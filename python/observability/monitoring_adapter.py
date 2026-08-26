# python/observability/monitoring_adapter.py
"""Cloud Monitoring 読み取りアダプタ (PRIDEV-490)

**読み取り専用**。指標の書き込み・アラート設定の変更は行わない。

GCE / Cloud Run で指標の type が異なるため、実行環境を判定して
同じ指標名 (cpu_utilization など) で引けるように吸収する。
取得できない指標は例外ではなく MetricSample.unavailable として返す。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from python.observability.errors import (
    ObservabilityError,
    ObservabilityUnavailableError,
    normalize_exception,
)
from python.observability.models import MetricSample
from python.observability.settings import (
    METRIC_TYPES,
    ObservabilitySettings,
    get_observability_settings,
)
from python.utils.logger import get_logger

logger = get_logger("observability", "monitoring")

__all__ = ["CloudMonitoringReader", "detect_platform"]

# 指標の集計に使う直近の窓 (取得期間そのものではなく「今の値」を得るための幅)
SAMPLE_WINDOW_MINUTES = 10


def detect_platform() -> str:
    """実行環境を判定する。Cloud Run なら K_SERVICE が設定される。"""
    return "cloud_run" if os.getenv("K_SERVICE") else "gce"


class CloudMonitoringReader:
    """Cloud Monitoring から稼働指標を読み取る。"""

    def __init__(
        self,
        client: Optional[Any] = None,
        settings: Optional[ObservabilitySettings] = None,
        platform: Optional[str] = None,
    ) -> None:
        self._client = client
        self._settings = settings or get_observability_settings()
        self._platform = platform or detect_platform()

    @property
    def settings(self) -> ObservabilitySettings:
        return self._settings

    @property
    def platform(self) -> str:
        return self._platform

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._settings.project_id:
            raise ObservabilityUnavailableError(
                "Cloud Monitoring: GCP プロジェクト ID が未設定です (GCP_PROJECT_ID)"
            )
        try:
            from google.cloud import monitoring_v3
        except ImportError as exc:  # pragma: no cover - 依存未導入時のみ
            raise ObservabilityUnavailableError(
                "Cloud Monitoring: google-cloud-monitoring が導入されていません"
            ) from exc
        try:
            self._client = monitoring_v3.MetricServiceClient()
        except Exception as exc:  # noqa: BLE001 - SDK 例外を正規化する
            raise normalize_exception(exc, "Cloud Monitoring クライアントの初期化") from exc
        return self._client

    def metric_type(self, metric: str) -> str:
        """指標名を実行環境に応じた Cloud Monitoring の type へ解決する。"""
        return METRIC_TYPES.get(metric, {}).get(self._platform, "")

    def fetch_metrics(
        self,
        metrics: Optional[List[str]] = None,
        *,
        now: Optional[datetime] = None,
    ) -> Dict[str, MetricSample]:
        """設定済みの監視指標をまとめて取得する。

        個々の指標が取れなくても例外にせず、unavailable として返す。
        クライアント初期化そのものが失敗した場合は全指標を unavailable にする。
        """
        target_metrics = list(metrics) if metrics is not None else list(self._settings.monitored_metrics)
        now = now or datetime.now(timezone.utc)

        try:
            client = self._get_client()
        except ObservabilityError as exc:
            logger.warning(f"Cloud Monitoring を利用できません: {exc}")
            return {name: MetricSample.unavailable(name, str(exc)) for name in target_metrics}

        results: Dict[str, MetricSample] = {}
        for name in target_metrics:
            results[name] = self._fetch_one(client, name, now)
        return results

    def _fetch_one(self, client: Any, metric: str, now: datetime) -> MetricSample:
        metric_type = self.metric_type(metric)
        if not metric_type:
            return MetricSample.unavailable(metric, "この実行環境では取得できない指標です")

        try:
            series = client.list_time_series(
                request=self._build_request(metric_type, now),
            )
            value = _latest_value(series)
        except Exception as exc:  # noqa: BLE001 - SDK 例外を正規化する
            normalized = normalize_exception(exc, f"Cloud Monitoring ({metric}) の取得")
            logger.warning(str(normalized))
            return MetricSample.unavailable(metric, str(normalized))

        if value is None:
            return MetricSample.unavailable(metric, "データ点がありません")
        return MetricSample(metric=metric, value=value, sampled_at=now)

    def _build_request(self, metric_type: str, now: datetime) -> Dict[str, Any]:
        """list_time_series へ渡すリクエストを組み立てる。

        SDK 型 (monitoring_v3.ListTimeSeriesRequest) ではなく dict で渡すことで、
        SDK 未導入環境でも本メソッドを検証できるようにしている。
        """
        start = now - timedelta(minutes=SAMPLE_WINDOW_MINUTES)
        return {
            "name": f"projects/{self._settings.project_id}",
            "filter": f'metric.type = "{metric_type}"',
            "interval": {
                "start_time": {"seconds": int(start.timestamp())},
                "end_time": {"seconds": int(now.timestamp())},
            },
            "view": "FULL",
        }


def _latest_value(series: Any) -> Optional[float]:
    """時系列から最新のデータ点を取り出す。"""
    for time_series in series or []:
        points = getattr(time_series, "points", None) or []
        for point in points:
            value = getattr(point, "value", None)
            if value is None:
                continue
            for attribute in ("double_value", "int64_value", "bool_value"):
                raw = getattr(value, attribute, None)
                if raw is not None:
                    return float(raw)
    return None
