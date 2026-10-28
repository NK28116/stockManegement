"""管理者専用 System Monitor API のテスト (PRIDEV-492)"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.observability import errors, settings as observability_settings  # noqa: E402
from python.observability.health import HealthStatus, SystemHealth  # noqa: E402
from python.observability.models import MetricSample  # noqa: E402
from python.web import auth  # noqa: E402
from python.web.api import system_monitor  # noqa: E402

NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
TEST_PASSWORD = "monitor-test-password"
API_PATH = "/api/system-monitor"


class StubHealthService:
    def __init__(self, health=None, error=None):
        self._health = health if health is not None else SystemHealth(checked_at=NOW)
        self._error = error
        self.calls = []

    def collect(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._health


@pytest.fixture(autouse=True)
def reset_caches():
    auth.reset_auth_settings_cache()
    observability_settings.reset_observability_settings_cache()
    yield
    auth.reset_auth_settings_cache()
    observability_settings.reset_observability_settings_cache()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    monkeypatch.setenv("AUTH_SECRET_KEY", "system-monitor-test-key")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    auth.reset_auth_settings_cache()
    observability_settings.reset_observability_settings_cache()

    from python.web.app import app as real_app

    yield real_app
    real_app.dependency_overrides.clear()


def _use_service(app, service):
    app.dependency_overrides[system_monitor.get_health_service] = lambda: service


def _login(client):
    response = client.post(
        "/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False
    )
    assert response.status_code == 303
    return client


# --- 認証境界 -----------------------------------------------------------------
def test_unauthenticated_request_returns_401(app):
    _use_service(app, StubHealthService())

    response = TestClient(app).get(API_PATH)

    assert response.status_code == 401
    assert "detail" in response.json()


def test_authenticated_request_returns_health(app):
    health = SystemHealth(checked_at=NOW, status=HealthStatus.OK, error_count=0)
    _use_service(app, StubHealthService(health))

    client = _login(TestClient(app))
    response = client.get(API_PATH)

    assert response.status_code == 200
    assert response.json()["status"] == HealthStatus.OK
    assert response.json()["checked_at"] == NOW.isoformat()


def test_logout_revokes_api_access(app):
    _use_service(app, StubHealthService())
    client = _login(TestClient(app))
    assert client.get(API_PATH).status_code == 200

    client.post("/auth/logout", follow_redirects=False)

    assert client.get(API_PATH).status_code == 401


def test_permission_error_returns_403(app):
    _use_service(app, StubHealthService(error=errors.ObservabilityPermissionError("no role")))

    response = _login(TestClient(app)).get(API_PATH)

    assert response.status_code == 403
    assert "権限" in response.json()["detail"]


def test_unexpected_error_returns_503_without_internals(app):
    secret_detail = "psycopg2 connection string password=hunter2"
    _use_service(app, StubHealthService(error=RuntimeError(secret_detail)))

    response = _login(TestClient(app)).get(API_PATH)

    assert response.status_code == 503
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text


# --- degraded は 200 で返す ---------------------------------------------------
def test_degraded_is_returned_as_200_with_status(app):
    health = SystemHealth(checked_at=NOW)
    health.degraded_reasons.append("ログを取得できませんでした")
    health.status = HealthStatus.DEGRADED
    _use_service(app, StubHealthService(health))

    response = _login(TestClient(app)).get(API_PATH)

    assert response.status_code == 200
    assert response.json()["degraded"] is True
    assert response.json()["status"] == HealthStatus.DEGRADED


# --- 取得条件の上限 -----------------------------------------------------------
def test_query_parameters_are_passed_to_the_service(app):
    service = StubHealthService()
    _use_service(app, service)

    _login(TestClient(app)).get(API_PATH, params={"lookback_hours": 3, "limit": 10})

    assert service.calls[0] == {"lookback_hours": 3, "limit": 10}


def test_applied_limits_are_reported(app):
    _use_service(app, StubHealthService())

    response = _login(TestClient(app)).get(API_PATH, params={"limit": 100_000})

    query = response.json()["query"]
    settings = observability_settings.get_observability_settings()
    assert query["limit"] == settings.max_limit
    assert query["max_limit"] == settings.max_limit
    assert query["max_lookback_hours"] == settings.max_lookback_hours


@pytest.mark.parametrize("params", [{"limit": 0}, {"lookback_hours": 0}, {"limit": -1}])
def test_invalid_query_parameters_are_rejected(app, params):
    _use_service(app, StubHealthService())

    response = _login(TestClient(app)).get(API_PATH, params=params)

    assert response.status_code == 422


# --- 秘密値がレスポンスへ出ないこと -------------------------------------------
def test_response_does_not_leak_credentials(app):
    health = SystemHealth(
        checked_at=NOW,
        metrics={"cpu_utilization": MetricSample(metric="cpu_utilization", value=0.2)},
    )
    _use_service(app, StubHealthService(health))

    client = _login(TestClient(app))
    body = client.get(API_PATH).text

    assert TEST_PASSWORD not in body
    assert auth.AUTH_COOKIE_NAME not in body
    assert "APP_PASSWORD" not in body
