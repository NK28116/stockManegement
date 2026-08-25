"""Cloud Logging / Monitoring 読み取りアダプタのテスト (PRIDEV-490)

GCP API は呼ばず、注入したモッククライアントで検証する。
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.observability import errors, settings as settings_module  # noqa: E402
from python.observability.logging_adapter import CloudLoggingReader, build_filter  # noqa: E402
from python.observability.models import LogEntry, MetricSample  # noqa: E402
from python.observability.monitoring_adapter import CloudMonitoringReader  # noqa: E402

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def reset_settings():
    settings_module.reset_observability_settings_cache()
    yield
    settings_module.reset_observability_settings_cache()


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    settings_module.reset_observability_settings_cache()
    return settings_module.get_observability_settings()


class FakeLoggingClient:
    """list_entries だけを持つ最小のモック。"""

    def __init__(self, entries=None, error=None):
        self._entries = entries or []
        self._error = error
        self.calls = []

    def list_entries(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return iter(self._entries)


def _raw_entry(message="boom", severity="ERROR", offset_minutes=0):
    return SimpleNamespace(
        payload=message,
        severity=severity,
        timestamp=NOW - timedelta(minutes=offset_minutes),
        resource=SimpleNamespace(type="cloud_run_revision"),
        labels={"service": "stock-web-ui"},
    )


class PermissionDenied(Exception):
    """google.api_core.exceptions.PermissionDenied を模した例外。"""


# --- 設定値の外部化 -----------------------------------------------------------
def test_defaults_are_the_documented_provisional_values(configured):
    assert configured.default_lookback_hours == settings_module.DEFAULT_LOG_LOOKBACK_HOURS
    assert configured.max_lookback_days == settings_module.MAX_LOG_LOOKBACK_DAYS
    assert configured.default_limit == settings_module.DEFAULT_LOG_LIMIT
    assert configured.max_limit == settings_module.MAX_LOG_LIMIT


def test_settings_come_from_environment(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "p")
    monkeypatch.setenv("OBSERVABILITY_LOG_DEFAULT_LIMIT", "5")
    monkeypatch.setenv("OBSERVABILITY_LOG_MAX_LIMIT", "50")
    settings_module.reset_observability_settings_cache()

    current = settings_module.get_observability_settings()

    assert (current.default_limit, current.max_limit) == (5, 50)


@pytest.mark.parametrize("bad", ["", "abc", "0", "-3"])
def test_invalid_settings_fall_back_to_defaults(monkeypatch, bad):
    monkeypatch.setenv("OBSERVABILITY_LOG_MAX_LIMIT", bad)
    settings_module.reset_observability_settings_cache()

    assert settings_module.get_observability_settings().max_limit == settings_module.MAX_LOG_LIMIT


def test_unapproved_metrics_are_ignored(monkeypatch):
    monkeypatch.setenv("OBSERVABILITY_MONITORED_METRICS", "cpu_utilization,disk_iops_invented")
    settings_module.reset_observability_settings_cache()

    assert settings_module.get_observability_settings().monitored_metrics == ("cpu_utilization",)


# --- 期間・件数の上限 ---------------------------------------------------------
def test_limit_is_clamped_to_maximum(configured):
    assert configured.clamp_limit(10_000) == configured.max_limit
    assert configured.clamp_limit(None) == configured.default_limit
    assert configured.clamp_limit(0) == configured.default_limit
    assert configured.clamp_limit(7) == 7


def test_lookback_is_clamped_to_maximum(configured):
    assert configured.clamp_lookback_hours(10_000) == configured.max_lookback_hours
    assert configured.clamp_lookback_hours(None) == configured.default_lookback_hours
    assert configured.clamp_lookback_hours(3) == 3


def test_fetch_applies_limits_to_the_request(configured):
    client = FakeLoggingClient([_raw_entry() for _ in range(10)])
    reader = CloudLoggingReader(client=client, settings=configured)

    reader.fetch_recent(lookback_hours=10_000, limit=10_000)

    request = client.calls[0]
    assert request["max_results"] == configured.max_limit
    since = request["filter_"].split('"')[1]
    assert datetime.fromisoformat(since) >= datetime.now(timezone.utc) - timedelta(
        hours=configured.max_lookback_hours + 1
    )


def test_fetch_truncates_results_at_the_limit(configured):
    client = FakeLoggingClient([_raw_entry() for _ in range(50)])
    reader = CloudLoggingReader(client=client, settings=configured)

    entries = reader.fetch_recent(limit=5)

    assert len(entries) == 5, "SDK が上限より多く返しても打ち切ること"


def test_build_filter_uses_severity_and_window():
    generated = build_filter(lookback_hours=6, min_severity="ERROR", now=NOW)

    assert "severity >= ERROR" in generated
    assert (NOW - timedelta(hours=6)).isoformat() in generated


# --- 変換 ---------------------------------------------------------------------
def test_entries_are_converted_to_internal_model(configured):
    client = FakeLoggingClient([_raw_entry(message="DB error", severity="ERROR")])
    reader = CloudLoggingReader(client=client, settings=configured)

    entries = reader.fetch_recent()

    assert isinstance(entries[0], LogEntry)
    assert entries[0].message == "DB error"
    assert entries[0].severity == "ERROR"
    assert entries[0].resource_type == "cloud_run_revision"
    assert entries[0].labels == {"service": "stock-web-ui"}


def test_dict_payload_is_flattened(configured):
    raw = _raw_entry()
    raw.payload = {"message": "structured message", "extra": 1}
    reader = CloudLoggingReader(client=FakeLoggingClient([raw]), settings=configured)

    assert reader.fetch_recent()[0].message == "structured message"


# --- エラーの正規化 -----------------------------------------------------------
def test_permission_error_is_normalized(configured):
    client = FakeLoggingClient(error=PermissionDenied("caller lacks roles/logging.viewer"))
    reader = CloudLoggingReader(client=client, settings=configured)

    with pytest.raises(errors.ObservabilityPermissionError):
        reader.fetch_recent()


def test_other_sdk_errors_are_normalized(configured):
    client = FakeLoggingClient(error=RuntimeError("connection reset"))
    reader = CloudLoggingReader(client=client, settings=configured)

    with pytest.raises(errors.ObservabilityUnavailableError) as raised:
        reader.fetch_recent()

    assert isinstance(raised.value.__cause__, RuntimeError)


def test_sdk_exception_details_are_not_leaked(configured):
    secret = "projects/secret-project/logs/private"
    client = FakeLoggingClient(error=RuntimeError(secret))
    reader = CloudLoggingReader(client=client, settings=configured)

    with pytest.raises(errors.ObservabilityError) as raised:
        reader.fetch_recent()

    assert secret not in str(raised.value)


def test_missing_project_id_is_reported_as_unavailable(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("PROJECT_ID", raising=False)
    settings_module.reset_observability_settings_cache()

    with pytest.raises(errors.ObservabilityUnavailableError):
        CloudLoggingReader().fetch_recent()


# --- Monitoring ---------------------------------------------------------------
class FakeMonitoringClient:
    def __init__(self, value=None, error=None):
        self._value = value
        self._error = error
        self.requests = []

    def list_time_series(self, request):
        self.requests.append(request)
        if self._error:
            raise self._error
        if self._value is None:
            return []
        point = SimpleNamespace(value=SimpleNamespace(double_value=self._value))
        return [SimpleNamespace(points=[point])]


def test_metrics_are_fetched_for_configured_names(configured):
    client = FakeMonitoringClient(value=0.42)
    reader = CloudMonitoringReader(client=client, settings=configured, platform="cloud_run")

    samples = reader.fetch_metrics(["cpu_utilization"], now=NOW)

    assert samples["cpu_utilization"].value == pytest.approx(0.42)
    assert samples["cpu_utilization"].available is True
    assert "run.googleapis.com/container/cpu/utilizations" in client.requests[0]["filter"]


def test_platform_difference_is_absorbed(configured):
    gce = CloudMonitoringReader(client=FakeMonitoringClient(1.0), settings=configured, platform="gce")

    assert gce.metric_type("cpu_utilization") == "compute.googleapis.com/instance/cpu/utilization"


def test_unfetchable_metric_is_represented_not_raised(configured):
    reader = CloudMonitoringReader(
        client=FakeMonitoringClient(error=PermissionDenied("nope")),
        settings=configured,
        platform="cloud_run",
    )

    samples = reader.fetch_metrics(["cpu_utilization"], now=NOW)

    assert samples["cpu_utilization"].available is False
    assert samples["cpu_utilization"].value is None


def test_metric_without_a_type_for_this_platform_is_unavailable(configured):
    reader = CloudMonitoringReader(
        client=FakeMonitoringClient(1.0), settings=configured, platform="cloud_run"
    )

    samples = reader.fetch_metrics(["last_success_at"], now=NOW)

    assert samples["last_success_at"].available is False


def test_empty_time_series_is_unavailable(configured):
    reader = CloudMonitoringReader(
        client=FakeMonitoringClient(value=None), settings=configured, platform="cloud_run"
    )

    assert reader.fetch_metrics(["cpu_utilization"], now=NOW)["cpu_utilization"].available is False


def test_client_failure_marks_every_metric_unavailable(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("PROJECT_ID", raising=False)
    settings_module.reset_observability_settings_cache()

    samples = CloudMonitoringReader().fetch_metrics(["cpu_utilization", "error_count"], now=NOW)

    assert [sample.available for sample in samples.values()] == [False, False]


def test_metric_sample_serialization():
    sample = MetricSample(metric="cpu_utilization", value=0.5, unit="1", sampled_at=NOW)

    assert sample.to_dict()["metric"] == "cpu_utilization"
    assert sample.to_dict()["sampled_at"] == NOW.isoformat()


# --- 読み取り専用であること ---------------------------------------------------
@pytest.mark.parametrize("module_path", [
    "python/observability/logging_adapter.py",
    "python/observability/monitoring_adapter.py",
])
def test_adapters_do_not_use_write_apis(module_path):
    source = (ROOT / module_path).read_text(encoding="utf-8")

    for forbidden in ("log_text", "log_struct", "create_time_series", "delete_", "write_"):
        assert forbidden not in source, f"{module_path} が書き込み API を参照している"
