"""System Monitor の認証・異常系 E2E テスト (PRIDEV-494)

実際に uvicorn を起動し、HTTP クライアントから **本物のソケット経由**で
ログイン → Cookie 保持 → 保護画面 → API という経路をなぞる。
middleware・認証ガード・テンプレート描画・API を通しで検証する。

ブラウザ (Playwright 等) は使わない:
    * CI にブラウザが無く、テンプレートは Tailwind / Vue を CDN から読み込むため
      オフライン環境では DOM を評価できない
    * そのため「サーバが返す HTML / JSON」に対して検証する
      (DOM 描画後の見た目の検証は本テストの対象外)

GCP との境界だけをスタブに差し替え、それ以外は本番と同じ経路を通す。
"""

import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.observability import errors, settings as observability_settings  # noqa: E402
from python.observability.health import HealthStatus, MaskedLogEntry, SystemHealth  # noqa: E402
from python.observability.models import LogEntry, MetricSample  # noqa: E402
from python.web import auth  # noqa: E402
from python.web.api import system_monitor as monitor_api  # noqa: E402
from python.web.routes import system_monitor as monitor_ui  # noqa: E402

E2E_PASSWORD = "e2e-monitor-password"

# テストで意図的に流し込む秘密値。UI / API のどこにも現れてはいけない。
TEST_SECRETS = {
    "api_key": "sk-live-E2ESECRETKEYVALUE",
    "bearer": "eyJhbGciOiJIUzI1NiJ9.E2EPAYLOAD.E2ESIGNATURE",
    "password": "e2e-db-password-value",
}
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


class StubHealthService:
    """GCP との境界だけを差し替えるスタブ。"""

    def __init__(self):
        self.health = SystemHealth(checked_at=NOW, status=HealthStatus.OK)
        self.error = None

    def collect(self, **kwargs):
        if self.error:
            raise self.error
        return self.health


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def stub_service():
    return StubHealthService()


@pytest.fixture(scope="module")
def base_url(stub_service):
    """本物の uvicorn を立ち上げて base URL を返す。"""
    import os

    import uvicorn

    os.environ["APP_PASSWORD_HASH"] = auth.hash_password(E2E_PASSWORD)
    os.environ["AUTH_SECRET_KEY"] = "e2e-signing-key"
    os.environ["AUTH_COOKIE_SECURE"] = "false"
    auth.reset_auth_settings_cache()
    observability_settings.reset_observability_settings_cache()
    monitor_ui.reset_ui_settings_cache()

    from python.web.app import app

    app.dependency_overrides[monitor_api.get_health_service] = lambda: stub_service

    port = _free_port()
    # lifespan="off": DB 初期化は本テストの対象外のため起動処理を走らせない
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 15
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "テスト用サーバーが起動しませんでした"

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=10)
    app.dependency_overrides.clear()
    for name in ("APP_PASSWORD_HASH", "AUTH_SECRET_KEY", "AUTH_COOKIE_SECURE"):
        os.environ.pop(name, None)
    auth.reset_auth_settings_cache()


@pytest.fixture
def client(base_url):
    """Cookie を保持する HTTP クライアント (ブラウザのセッション相当)。"""
    with httpx.Client(base_url=base_url, follow_redirects=False, timeout=10) as http_client:
        yield http_client


@pytest.fixture(autouse=True)
def reset_stub(stub_service):
    stub_service.health = SystemHealth(checked_at=NOW, status=HealthStatus.OK)
    stub_service.error = None
    yield


def _login(client, password=E2E_PASSWORD):
    return client.post("/auth/login", data={"password": password})


# --- 未認証経路 ---------------------------------------------------------------
def test_unauthenticated_page_is_redirected_to_login(client):
    response = client.get("/system-monitor")

    assert response.status_code == 303
    assert response.headers["location"].startswith(auth.LOGIN_PATH)


def test_unauthenticated_api_is_rejected(client):
    response = client.get("/api/system-monitor")

    assert response.status_code == 401


def test_wrong_password_does_not_grant_access(client):
    assert _login(client, "wrong-password").status_code == 401

    assert client.get("/api/system-monitor").status_code == 401
    assert client.get("/system-monitor").status_code == 303


def test_forged_session_cookie_is_rejected(client):
    client.cookies.set(auth.AUTH_COOKIE_NAME, "99999999999.forged-signature")

    assert client.get("/api/system-monitor").status_code == 401


# --- 認証済み経路 -------------------------------------------------------------
def test_authenticated_user_can_view_system_monitor(client):
    login = _login(client)

    assert login.status_code == 303
    assert auth.AUTH_COOKIE_NAME in login.cookies

    page = client.get("/system-monitor")
    api = client.get("/api/system-monitor")

    assert page.status_code == 200
    assert "System Monitor" in page.text
    assert api.status_code == 200
    assert api.json()["status"] == HealthStatus.OK


def test_logout_ends_the_session(client):
    _login(client)
    assert client.get("/api/system-monitor").status_code == 200

    client.post("/auth/logout")

    assert client.get("/api/system-monitor").status_code == 401
    assert client.get("/system-monitor").status_code == 303


# --- 異常系 -------------------------------------------------------------------
def test_permission_error_is_shown_safely(client, stub_service):
    _login(client)
    stub_service.error = errors.ObservabilityPermissionError("caller lacks roles/logging.viewer")

    response = client.get("/api/system-monitor")

    assert response.status_code == 403
    assert "roles/logging.viewer" not in response.text, "内部の権限詳細を返さないこと"
    assert "権限" in response.json()["detail"]


def test_cloud_api_failure_is_shown_as_degraded(client, stub_service):
    _login(client)
    stub_service.health = SystemHealth(checked_at=NOW)
    stub_service.health.degraded_reasons.append("ログを取得できませんでした")
    stub_service.health.status = HealthStatus.DEGRADED

    response = client.get("/api/system-monitor")

    assert response.status_code == 200, "障害時も画面が描けるよう 200 で返すこと"
    assert response.json()["degraded"] is True
    assert response.json()["status"] == HealthStatus.DEGRADED


def test_unexpected_failure_does_not_expose_internals(client, stub_service):
    _login(client)
    stub_service.error = RuntimeError(
        f"psycopg2 could not connect password={TEST_SECRETS['password']}"
    )

    response = client.get("/api/system-monitor")

    assert response.status_code == 503
    assert TEST_SECRETS["password"] not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text


# --- 秘密値の非露出 -----------------------------------------------------------
def test_secrets_do_not_reach_the_api_response(client, stub_service):
    _login(client)
    stub_service.health = SystemHealth(
        checked_at=NOW,
        status=HealthStatus.ERROR,
        error_count=1,
        recent_errors=[
            MaskedLogEntry.from_entry(
                LogEntry(
                    timestamp=NOW,
                    severity="ERROR",
                    message=(
                        f"GET https://api.example.com/v1?api_key={TEST_SECRETS['api_key']} failed; "
                        f"Authorization: Bearer {TEST_SECRETS['bearer']}"
                    ),
                    labels={"x-api-key": TEST_SECRETS["api_key"]},
                )
            )
        ],
        metrics={"cpu_utilization": MetricSample(metric="cpu_utilization", value=0.4)},
    )

    body = client.get("/api/system-monitor").text

    for secret in TEST_SECRETS.values():
        assert secret not in body, f"秘密値が API レスポンスへ露出している: {secret}"


def test_secrets_do_not_reach_the_page(client):
    _login(client)

    body = client.get("/system-monitor").text

    assert E2E_PASSWORD not in body
    assert "e2e-signing-key" not in body
    assert "APP_PASSWORD_HASH" not in body


def test_session_cookie_is_httponly_over_the_wire(client):
    response = _login(client)

    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert E2E_PASSWORD not in set_cookie
