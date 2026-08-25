# python/observability/models.py
"""Logging / Monitoring から取得した値の内部表現 (PRIDEV-490)"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

__all__ = ["LogEntry", "MetricSample"]


@dataclass(frozen=True)
class LogEntry:
    """Cloud Logging の 1 エントリ。"""

    timestamp: Optional[datetime]
    severity: str
    message: str
    resource_type: str = ""
    labels: Dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.labels is None:
            object.__setattr__(self, "labels", {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity,
            "message": self.message,
            "resource_type": self.resource_type,
            "labels": dict(self.labels),
        }


@dataclass(frozen=True)
class MetricSample:
    """Cloud Monitoring の指標 1 件。

    取得できなかった指標は value=None / available=False で表現し、
    例外ではなく値として上位層へ渡す。
    """

    metric: str
    value: Optional[float]
    unit: str = ""
    sampled_at: Optional[datetime] = None
    available: bool = True
    detail: str = ""

    @classmethod
    def unavailable(cls, metric: str, detail: str) -> "MetricSample":
        return cls(metric=metric, value=None, available=False, detail=detail)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "sampled_at": self.sampled_at.isoformat() if self.sampled_at else None,
            "available": self.available,
            "detail": self.detail,
        }
