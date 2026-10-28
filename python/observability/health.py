# python/observability/health.py
"""System Health 集約サービス (PRIDEV-491)

Cloud Logging / Monitoring から得た情報を、上位層 (System Monitor API / 画面) が
参照する **単一の SystemHealth モデル** へ集約する。

方針:
    * Cloud API の失敗で例外を投げない。degraded 状態として返す
    * 画面へ出る文字列は必ずマスク処理を通す
    * GCP SDK の型・例外を上位層へ渡さない
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from python.observability.errors import ObservabilityError, ObservabilityPermissionError
from python.observability.logging_adapter import CloudLoggingReader
from python.observability.masking import mask_mapping, mask_text
from python.observability.models import LogEntry, MetricSample
from python.observability.monitoring_adapter import CloudMonitoringReader
from python.observability.settings import ObservabilitySettings, get_observability_settings
from python.utils.logger import get_logger

logger = get_logger("observability", "health")

__all__ = [
    "HealthStatus",
    "SystemHealth",
    "SystemHealthService",
    "MaskedLogEntry",
]

# エラーとみなす severity
ERROR_SEVERITIES = frozenset({"ERROR", "CRITICAL", "ALERT", "EMERGENCY"})
WARNING_SEVERITIES = frozenset({"WARNING"})


class HealthStatus:
    """稼働状態。文字列定数として扱う (API レスポンスへそのまま出る)。"""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class MaskedLogEntry:
    """画面へ出しても安全な形へ加工済みのログ。"""

    timestamp: Optional[str]
    severity: str
    message: str
    resource_type: str
    labels: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_entry(cls, entry: LogEntry) -> "MaskedLogEntry":
        return cls(
            timestamp=entry.timestamp.isoformat() if entry.timestamp else None,
            severity=entry.severity,
            message=mask_text(entry.message),
            resource_type=entry.resource_type,
            labels=mask_mapping(entry.labels),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "message": self.message,
            "resource_type": self.resource_type,
            "labels": dict(self.labels),
        }


@dataclass
class SystemHealth:
    """上位層が参照する唯一の集約モデル。"""

    status: str = HealthStatus.OK
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_count: int = 0
    warning_count: int = 0
    recent_errors: List[MaskedLogEntry] = field(default_factory=list)
    metrics: Dict[str, MetricSample] = field(default_factory=dict)
    last_success_at: Optional[str] = None
    degraded_reasons: List[str] = field(default_factory=list)

    @property
    def degraded(self) -> bool:
        return bool(self.degraded_reasons)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at.isoformat(),
            "degraded": self.degraded,
            "degraded_reasons": list(self.degraded_reasons),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "last_success_at": self.last_success_at,
            "recent_errors": [entry.to_dict() for entry in self.recent_errors],
            "metrics": {name: sample.to_dict() for name, sample in self.metrics.items()},
        }


class SystemHealthService:
    """Logging / Monitoring を集約して SystemHealth を返す。"""

    def __init__(
        self,
        logging_reader: Optional[CloudLoggingReader] = None,
        monitoring_reader: Optional[CloudMonitoringReader] = None,
        settings: Optional[ObservabilitySettings] = None,
    ) -> None:
        self._settings = settings or get_observability_settings()
        self._logging_reader = logging_reader or CloudLoggingReader(settings=self._settings)
        self._monitoring_reader = monitoring_reader or CloudMonitoringReader(settings=self._settings)

    def collect(
        self,
        *,
        lookback_hours: Optional[int] = None,
        limit: Optional[int] = None,
        now: Optional[datetime] = None,
    ) -> SystemHealth:
        """System Health を集約する。Cloud API が落ちていても例外を投げない。"""
        health = SystemHealth(checked_at=now or datetime.now(timezone.utc))

        entries = self._collect_logs(health, lookback_hours=lookback_hours, limit=limit)
        self._classify(health, entries)
        self._collect_metrics(health)
        self._decide_status(health)
        return health

    def _collect_logs(
        self,
        health: SystemHealth,
        *,
        lookback_hours: Optional[int],
        limit: Optional[int],
    ) -> List[LogEntry]:
        try:
            return self._logging_reader.fetch_recent(lookback_hours=lookback_hours, limit=limit)
        except ObservabilityPermissionError as exc:
            health.degraded_reasons.append(f"ログの取得権限がありません: {exc}")
        except ObservabilityError as exc:
            health.degraded_reasons.append(f"ログを取得できませんでした: {exc}")
        except Exception as exc:  # noqa: BLE001 - 想定外でも degraded で返す
            logger.warning(f"ログ取得で想定外の例外: {type(exc).__name__}")
            health.degraded_reasons.append("ログを取得できませんでした")
        return []

    @staticmethod
    def _classify(health: SystemHealth, entries: List[LogEntry]) -> None:
        """severity で分類し、エラーのみを画面向けに整形する。"""
        errors = [entry for entry in entries if entry.severity.upper() in ERROR_SEVERITIES]
        warnings = [entry for entry in entries if entry.severity.upper() in WARNING_SEVERITIES]

        health.error_count = len(errors)
        health.warning_count = len(warnings)
        health.recent_errors = [MaskedLogEntry.from_entry(entry) for entry in errors]

    def _collect_metrics(self, health: SystemHealth) -> None:
        try:
            health.metrics = self._monitoring_reader.fetch_metrics()
        except Exception as exc:  # noqa: BLE001 - アダプタ側で握るが二重に防ぐ
            logger.warning(f"指標取得で想定外の例外: {type(exc).__name__}")
            health.metrics = {}
            health.degraded_reasons.append("稼働指標を取得できませんでした")
            return

        unavailable = [name for name, sample in health.metrics.items() if not sample.available]
        if unavailable and len(unavailable) == len(health.metrics):
            health.degraded_reasons.append("稼働指標を取得できませんでした")

        last_success = health.metrics.get("last_success_at")
        if last_success is not None and last_success.available and last_success.value is not None:
            health.last_success_at = datetime.fromtimestamp(
                last_success.value, tz=timezone.utc
            ).isoformat()

    @staticmethod
    def _decide_status(health: SystemHealth) -> None:
        if health.degraded_reasons:
            health.status = HealthStatus.DEGRADED
        elif health.error_count:
            health.status = HealthStatus.ERROR
        elif health.warning_count:
            health.status = HealthStatus.WARNING
        else:
            health.status = HealthStatus.OK
