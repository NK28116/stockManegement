"""System Health 集約サービスと秘匿処理のテスト (PRIDEV-491)"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.observability import errors, masking  # noqa: E402
from python.observability.health import (  # noqa: E402
    HealthStatus,
    SystemHealth,
    SystemHealthService,
)
from python.observability.models import LogEntry, MetricSample  # noqa: E402

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

SECRETS = (
    "sk-live-51H9xSECRETVALUE",
    "eyJhbGciOiJIUzI1NiJ9.payloadpart.signaturepart",
    "hunter2",
    "deadbeefsessionvalue",
)


class FakeLoggingReader:
    def __init__(self, entries=None, error=None):
        self._entries = entries or []
        self._error = error
        self.calls = []

    def fetch_recent(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return list(self._entries)


class FakeMonitoringReader:
    def __init__(self, samples=None, error=None):
        self._samples = samples if samples is not None else {}
        self._error = error

    def fetch_metrics(self, *args, **kwargs):
        if self._error:
            raise self._error
        return dict(self._samples)


def _entry(severity="ERROR", message="something failed"):
    return LogEntry(timestamp=NOW, severity=severity, message=message, resource_type="cloud_run_revision")


def _service(logging_reader=None, monitoring_reader=None):
    return SystemHealthService(
        logging_reader=logging_reader or FakeLoggingReader(),
        monitoring_reader=monitoring_reader or FakeMonitoringReader(),
    )


# --- 単一の集約モデル ---------------------------------------------------------
def test_upper_layer_sees_a_single_health_model():
    health = _service().collect(now=NOW)

    assert isinstance(health, SystemHealth)
    payload = health.to_dict()
    for key in ("status", "checked_at", "degraded", "error_count", "recent_errors", "metrics"):
        assert key in payload


def test_errors_and_warnings_are_classified():
    reader = FakeLoggingReader(
        [_entry("ERROR"), _entry("CRITICAL"), _entry("WARNING"), _entry("INFO")]
    )

    health = _service(reader).collect(now=NOW)

    assert health.error_count == 2
    assert health.warning_count == 1
    assert len(health.recent_errors) == 2, "recent_errors はエラーのみ"


@pytest.mark.parametrize(
    "entries,expected",
    [
        ([], HealthStatus.OK),
        ([_entry("WARNING")], HealthStatus.WARNING),
        ([_entry("ERROR")], HealthStatus.ERROR),
    ],
)
def test_status_reflects_log_severity(entries, expected):
    health = _service(FakeLoggingReader(entries)).collect(now=NOW)

    assert health.status == expected


def test_last_success_at_comes_from_metrics():
    samples = {"last_success_at": MetricSample(metric="last_success_at", value=NOW.timestamp())}

    health = _service(monitoring_reader=FakeMonitoringReader(samples)).collect(now=NOW)

    assert health.last_success_at == NOW.isoformat()


def test_lookback_and_limit_are_passed_through():
    reader = FakeLoggingReader()

    _service(reader).collect(lookback_hours=3, limit=7, now=NOW)

    assert reader.calls[0] == {"lookback_hours": 3, "limit": 7}


# --- degraded ---------------------------------------------------------------
def test_logging_failure_returns_degraded_not_exception():
    reader = FakeLoggingReader(error=errors.ObservabilityUnavailableError("Cloud Logging: 到達不能"))

    health = _service(reader).collect(now=NOW)

    assert health.status == HealthStatus.DEGRADED
    assert health.degraded is True
    assert any("ログを取得できませんでした" in reason for reason in health.degraded_reasons)


def test_permission_error_is_reported_as_degraded():
    reader = FakeLoggingReader(error=errors.ObservabilityPermissionError("権限が不足しています"))

    health = _service(reader).collect(now=NOW)

    assert health.status == HealthStatus.DEGRADED
    assert any("権限" in reason for reason in health.degraded_reasons)


def test_unexpected_exception_is_contained():
    reader = FakeLoggingReader(error=RuntimeError("unexpected"))

    health = _service(reader).collect(now=NOW)

    assert health.status == HealthStatus.DEGRADED


def test_all_metrics_unavailable_is_degraded():
    samples = {
        "cpu_utilization": MetricSample.unavailable("cpu_utilization", "権限不足"),
        "error_count": MetricSample.unavailable("error_count", "権限不足"),
    }

    health = _service(monitoring_reader=FakeMonitoringReader(samples)).collect(now=NOW)

    assert health.status == HealthStatus.DEGRADED


def test_partially_available_metrics_are_not_degraded():
    samples = {
        "cpu_utilization": MetricSample(metric="cpu_utilization", value=0.3),
        "error_count": MetricSample.unavailable("error_count", "データ点なし"),
    }

    health = _service(monitoring_reader=FakeMonitoringReader(samples)).collect(now=NOW)

    assert health.degraded is False
    assert health.status == HealthStatus.OK


def test_monitoring_exception_is_contained():
    health = _service(monitoring_reader=FakeMonitoringReader(error=RuntimeError("boom"))).collect(now=NOW)

    assert health.status == HealthStatus.DEGRADED
    assert health.metrics == {}


# --- 秘匿処理 -----------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "GET https://api.example.com/v1/orders?api_key=sk-live-51H9xSECRETVALUE&code=7203",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payloadpart.signaturepart",
        "Cookie: sm_session=deadbeefsessionvalue; theme=dark",
        "psql connect password=hunter2 host=db",
        '{"access_token": "eyJhbGciOiJIUzI1NiJ9.payloadpart.signaturepart"}',
    ],
)
def test_secrets_never_reach_the_output_model(text):
    health = _service(FakeLoggingReader([_entry("ERROR", text)])).collect(now=NOW)

    serialized = str(health.to_dict())
    for secret in SECRETS:
        assert secret not in serialized, f"秘密値が露出している: {text}"
    assert masking.MASK in health.recent_errors[0].message


def test_labels_are_masked():
    entry = LogEntry(
        timestamp=NOW,
        severity="ERROR",
        message="failed",
        labels={"service": "stock-web-ui", "x-api-key": "sk-live-51H9xSECRETVALUE"},
    )

    health = _service(FakeLoggingReader([entry])).collect(now=NOW)

    labels = health.recent_errors[0].labels
    assert labels["service"] == "stock-web-ui", "秘密でない値は保持すること"
    assert labels["x-api-key"] == masking.MASK


def test_query_string_is_masked_entirely():
    masked = masking.mask_text("https://example.com/callback?code=abc&state=xyz")

    assert masked == f"https://example.com/callback?{masking.MASK}"


def test_non_sensitive_text_is_preserved():
    message = "銘柄 7203.T の分析が完了しました (score=5)"

    assert masking.mask_text(message) == message


def test_masking_handles_empty_values():
    assert masking.mask_text(None) == ""
    assert masking.mask_mapping({}) == {}
