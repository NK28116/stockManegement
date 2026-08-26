# python/observability/settings.py
"""Cloud Logging / Monitoring 取得条件の設定 (PRIDEV-490)

取得期間・件数・監視指標は運用コストと画面要件に関わるユーザー判断事項のため、
ロジックへ埋め込まず本モジュールへ外部化する。確定後は既定値定数
(または同名の環境変数) の 1 箇所を変更すれば全体へ反映される。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

from python.utils.logger import get_logger

logger = get_logger("observability", "settings")

__all__ = [
    "MONITORED_METRIC_CANDIDATES",
    "ObservabilitySettings",
    "get_observability_settings",
    "reset_observability_settings_cache",
]


# 以下はユーザー確認済みの確定値 (PRIDEV-490)。変更する場合はここを変更する。
DEFAULT_LOG_LOOKBACK_HOURS = 24  # 過去 24 時間
MAX_LOG_LOOKBACK_DAYS = 7  # 最大 7 日間
DEFAULT_LOG_LIMIT = 100  # 100 件
MAX_LOG_LIMIT = 500  # 500 件

# 監視対象指標もユーザー確認済み (6 種)。
# 「ユーザーが指定していない監視指標を仕様として追加しない」ため、
# 本一覧の範囲外は環境変数で指定されても無視する。
MONITORED_METRIC_CANDIDATES: Tuple[str, ...] = (
    "service_up",  # サービス/プロセスの稼働状態
    "cpu_utilization",  # CPU 使用率
    "memory_utilization",  # メモリ使用率
    "error_count",  # 5xx またはエラー数
    "response_latency",  # レスポンスタイム
    "last_success_at",  # 最終正常実行時刻
)

# 指標名 → Cloud Monitoring のメトリック type。
# GCE / Cloud Run のどちらで動いていても同じ指標名で引けるようにする。
METRIC_TYPES = {
    "service_up": {
        "cloud_run": "run.googleapis.com/container/instance_count",
        "gce": "compute.googleapis.com/instance/uptime",
    },
    "cpu_utilization": {
        "cloud_run": "run.googleapis.com/container/cpu/utilizations",
        "gce": "compute.googleapis.com/instance/cpu/utilization",
    },
    "memory_utilization": {
        "cloud_run": "run.googleapis.com/container/memory/utilizations",
        "gce": "agent.googleapis.com/memory/percent_used",
    },
    "error_count": {
        "cloud_run": "run.googleapis.com/request_count",
        "gce": "logging.googleapis.com/log_entry_count",
    },
    "response_latency": {
        "cloud_run": "run.googleapis.com/request_latencies",
        "gce": "loadbalancing.googleapis.com/https/backend_latencies",
    },
    # last_success_at は Monitoring ではなく Logging 側から求めるため type を持たない
    "last_success_at": {},
}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(f"{name} を整数として解釈できないため既定値 {default} を使用します")
        return default
    if value <= 0:
        logger.warning(f"{name} が 0 以下のため既定値 {default} を使用します")
        return default
    return value


@dataclass(frozen=True)
class ObservabilitySettings:
    """取得条件 (ユーザー確認済み)。すべて上限付きで、上位層からの指定は clamp される。"""

    project_id: str
    default_lookback_hours: int
    max_lookback_days: int
    default_limit: int
    max_limit: int
    monitored_metrics: Tuple[str, ...]

    @property
    def max_lookback_hours(self) -> int:
        return self.max_lookback_days * 24

    def clamp_lookback_hours(self, requested: Optional[int]) -> int:
        """要求された取得期間を既定値・上限へ収める。"""
        if requested is None or requested <= 0:
            return self.default_lookback_hours
        return min(requested, self.max_lookback_hours)

    def clamp_limit(self, requested: Optional[int]) -> int:
        """要求された取得件数を既定値・上限へ収める。"""
        if requested is None or requested <= 0:
            return self.default_limit
        return min(requested, self.max_limit)


_settings_cache: Optional[ObservabilitySettings] = None


def _resolve_project_id() -> str:
    for name in ("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT", "PROJECT_ID"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _resolve_metrics() -> Tuple[str, ...]:
    raw = os.getenv("OBSERVABILITY_MONITORED_METRICS", "").strip()
    if not raw:
        return MONITORED_METRIC_CANDIDATES

    requested = tuple(item.strip() for item in raw.split(",") if item.strip())
    unknown = [name for name in requested if name not in MONITORED_METRIC_CANDIDATES]
    if unknown:
        logger.warning(f"未知の監視指標を無視します: {unknown}")
    return tuple(name for name in requested if name in MONITORED_METRIC_CANDIDATES)


def get_observability_settings() -> ObservabilitySettings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = ObservabilitySettings(
            project_id=_resolve_project_id(),
            default_lookback_hours=_env_int(
                "OBSERVABILITY_LOG_DEFAULT_LOOKBACK_HOURS", DEFAULT_LOG_LOOKBACK_HOURS
            ),
            max_lookback_days=_env_int(
                "OBSERVABILITY_LOG_MAX_LOOKBACK_DAYS", MAX_LOG_LOOKBACK_DAYS
            ),
            default_limit=_env_int("OBSERVABILITY_LOG_DEFAULT_LIMIT", DEFAULT_LOG_LIMIT),
            max_limit=_env_int("OBSERVABILITY_LOG_MAX_LIMIT", MAX_LOG_LIMIT),
            monitored_metrics=_resolve_metrics(),
        )
    return _settings_cache


def reset_observability_settings_cache() -> None:
    global _settings_cache
    _settings_cache = None
