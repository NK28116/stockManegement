# python/observability/logging_adapter.py
"""Cloud Logging 読み取りアダプタ (PRIDEV-490)

**読み取り専用**。ログの書き込み・削除は一切行わない。
取得期間と件数は ObservabilitySettings の上限が必ず適用される。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Optional

from python.observability.errors import ObservabilityUnavailableError, normalize_exception
from python.observability.models import LogEntry
from python.observability.settings import ObservabilitySettings, get_observability_settings
from python.utils.logger import get_logger

logger = get_logger("observability", "logging")

__all__ = ["CloudLoggingReader", "build_filter"]

# 取得対象の重大度。エラー調査が目的のため WARNING 以上を既定とする。
DEFAULT_MIN_SEVERITY = "WARNING"


def build_filter(*, lookback_hours: int, min_severity: str, now: Optional[datetime] = None) -> str:
    """Cloud Logging のフィルタ式を組み立てる。"""
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(hours=lookback_hours)).isoformat()
    return f'timestamp >= "{since}" AND severity >= {min_severity}'


class CloudLoggingReader:
    """Cloud Logging から直近のログを読み取る。

    client を注入できるため、テストでは GCP SDK を使わずに検証できる。
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        settings: Optional[ObservabilitySettings] = None,
    ) -> None:
        self._client = client
        self._settings = settings or get_observability_settings()

    @property
    def settings(self) -> ObservabilitySettings:
        return self._settings

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._settings.project_id:
            raise ObservabilityUnavailableError(
                "Cloud Logging: GCP プロジェクト ID が未設定です (GCP_PROJECT_ID)"
            )
        try:
            import google.cloud.logging as cloud_logging
        except ImportError as exc:  # pragma: no cover - 依存未導入時のみ
            raise ObservabilityUnavailableError(
                "Cloud Logging: google-cloud-logging が導入されていません"
            ) from exc
        try:
            self._client = cloud_logging.Client(project=self._settings.project_id)
        except Exception as exc:  # noqa: BLE001 - SDK 例外を正規化する
            raise normalize_exception(exc, "Cloud Logging クライアントの初期化") from exc
        return self._client

    def fetch_recent(
        self,
        *,
        lookback_hours: Optional[int] = None,
        limit: Optional[int] = None,
        min_severity: str = DEFAULT_MIN_SEVERITY,
        now: Optional[datetime] = None,
    ) -> List[LogEntry]:
        """直近のログを新しい順に取得する。

        Args:
            lookback_hours: 取得期間。未指定/範囲外は既定値・上限へ丸められる。
            limit: 取得件数。未指定/範囲外は既定値・上限へ丸められる。

        Raises:
            ObservabilityPermissionError / ObservabilityUnavailableError:
                GCP SDK の例外は必ずこのいずれかへ正規化される。
        """
        effective_hours = self._settings.clamp_lookback_hours(lookback_hours)
        effective_limit = self._settings.clamp_limit(limit)
        log_filter = build_filter(
            lookback_hours=effective_hours, min_severity=min_severity, now=now
        )

        client = self._get_client()
        try:
            entries = client.list_entries(
                filter_=log_filter,
                order_by="timestamp desc",
                max_results=effective_limit,
            )
            collected = self._collect(entries, effective_limit)
        except Exception as exc:  # noqa: BLE001 - SDK 例外を正規化する
            if isinstance(exc, ObservabilityUnavailableError):
                raise
            raise normalize_exception(exc, "Cloud Logging の取得") from exc

        logger.info(
            f"Cloud Logging から {len(collected)} 件取得しました "
            f"(lookback={effective_hours}h limit={effective_limit})"
        )
        return collected

    @staticmethod
    def _collect(entries: Iterable[Any], limit: int) -> List[LogEntry]:
        """SDK のページングを消費しつつ、上限件数で必ず打ち切る。"""
        collected: List[LogEntry] = []
        for raw in entries:
            collected.append(_to_log_entry(raw))
            if len(collected) >= limit:
                break
        return collected


def _to_log_entry(raw: Any) -> LogEntry:
    """SDK のエントリを内部モデルへ変換する (SDK 型を上位層へ渡さない)。"""
    payload = getattr(raw, "payload", None)
    if isinstance(payload, dict):
        message = str(payload.get("message") or payload)
    elif payload is None:
        message = ""
    else:
        message = str(payload)

    resource = getattr(raw, "resource", None)
    resource_type = getattr(resource, "type", "") if resource is not None else ""

    return LogEntry(
        timestamp=getattr(raw, "timestamp", None),
        severity=str(getattr(raw, "severity", "") or ""),
        message=message,
        resource_type=str(resource_type or ""),
        labels=dict(getattr(raw, "labels", None) or {}),
    )
