"""System Monitor 画面のテスト (PRIDEV-493)"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.web import auth  # noqa: E402
from python.web.routes import system_monitor as ui  # noqa: E402

TEMPLATE_PATH = ROOT / "python" / "web" / "templates" / "system_monitor.html"
TEST_PASSWORD = "monitor-ui-password"
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def reset_caches():
    auth.reset_auth_settings_cache()
    ui.reset_ui_settings_cache()
    yield
    auth.reset_auth_settings_cache()
    ui.reset_ui_settings_cache()


@pytest.fixture(scope="module")
def template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    monkeypatch.setenv("AUTH_SECRET_KEY", "system-monitor-ui-key")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    auth.reset_auth_settings_cache()
    ui.reset_ui_settings_cache()

    from python.web.app import app as real_app

    yield real_app
    real_app.dependency_overrides.clear()


def _login(client):
    assert client.post(
        "/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False
    ).status_code == 303
    return client


# --- 表示件数の設定 -----------------------------------------------------------
def test_defaults_are_the_documented_provisional_values():
    settings = ui.get_ui_settings()

    assert settings.initial_error_count == ui.DEFAULT_INITIAL_ERROR_COUNT
    assert settings.enable_load_more == ui.DEFAULT_ENABLE_LOAD_MORE
    assert settings.load_more_count == ui.DEFAULT_LOAD_MORE_COUNT
    assert settings.max_error_count == ui.DEFAULT_MAX_ERROR_COUNT


def test_settings_come_from_environment(monkeypatch):
    monkeypatch.setenv("SYSTEM_MONITOR_INITIAL_ERROR_COUNT", "5")
    monkeypatch.setenv("SYSTEM_MONITOR_ENABLE_LOAD_MORE", "false")
    monkeypatch.setenv("SYSTEM_MONITOR_LOAD_MORE_COUNT", "7")
    monkeypatch.setenv("SYSTEM_MONITOR_MAX_ERROR_COUNT", "40")
    ui.reset_ui_settings_cache()

    settings = ui.get_ui_settings()

    assert settings.to_client_config() == {
        "initialErrorCount": 5,
        "enableLoadMore": False,
        "loadMoreCount": 7,
        "maxErrorCount": 40,
    }


def test_initial_count_never_exceeds_the_display_cap(monkeypatch):
    monkeypatch.setenv("SYSTEM_MONITOR_INITIAL_ERROR_COUNT", "500")
    monkeypatch.setenv("SYSTEM_MONITOR_MAX_ERROR_COUNT", "50")
    ui.reset_ui_settings_cache()

    assert ui.get_ui_settings().to_client_config()["initialErrorCount"] == 50


@pytest.mark.parametrize("bad", ["", "abc", "0", "-5"])
def test_invalid_settings_fall_back_to_defaults(monkeypatch, bad):
    monkeypatch.setenv("SYSTEM_MONITOR_LOAD_MORE_COUNT", bad)
    ui.reset_ui_settings_cache()

    assert ui.get_ui_settings().load_more_count == ui.DEFAULT_LOAD_MORE_COUNT


# --- 認証 ---------------------------------------------------------------------
def test_unauthenticated_page_redirects_to_login(app):
    response = TestClient(app).get("/system-monitor", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith(auth.LOGIN_PATH)


def test_authenticated_page_is_served(app):
    response = _login(TestClient(app)).get("/system-monitor")

    assert response.status_code == 200
    assert "System Monitor" in response.text


def test_page_receives_server_side_counts(app, monkeypatch):
    monkeypatch.setenv("SYSTEM_MONITOR_INITIAL_ERROR_COUNT", "8")
    ui.reset_ui_settings_cache()

    body = _login(TestClient(app)).get("/system-monitor").text
    injected = re.search(r"window\.__MONITOR_CONFIG__ = (\{.*?\});", body)

    assert injected, "表示件数の設定がテンプレートへ注入されていない"
    assert '"initialErrorCount": 8' in injected.group(1)


def test_page_does_not_leak_credentials(app):
    body = _login(TestClient(app)).get("/system-monitor").text

    assert TEST_PASSWORD not in body
    assert "APP_PASSWORD" not in body
    assert "AUTH_SECRET_KEY" not in body


# --- 画面の状態 (静的検証) ----------------------------------------------------
def test_counts_are_not_hardcoded_in_the_template(template):
    """表示件数がテンプレートへ直書きされていないこと。"""
    assert "window.__MONITOR_CONFIG__" in template
    for key in ("initialErrorCount", "loadMoreCount", "maxErrorCount", "enableLoadMore"):
        assert f"this.config.{key}" in template, f"{key} がサーバ設定から使われていない"


@pytest.mark.parametrize("state", ["loading", "error", "empty", "degraded"])
def test_every_display_state_is_distinguishable(template, state):
    """loading / empty / error / degraded が区別できること。"""
    assert f'data-state="{state}"' in template


def test_load_more_is_gated_by_configuration(template):
    """追加読み込みが設定で無効化できること。"""
    assert "this.config.enableLoadMore && this.visibleErrors.length < this.totalErrorCount" in template
    assert 'data-role="load-more"' in template


def test_display_is_capped_at_the_maximum(template):
    """保持・表示件数が上限を超えないこと。"""
    assert "Math.min(this.health.recent_errors.length, this.config.maxErrorCount)" in template
    assert "Math.min(this.visibleCount, this.config.maxErrorCount)" in template
    assert "Math.min(\n                        this.visibleCount + this.config.loadMoreCount," in template


def test_status_and_last_update_are_shown(template):
    assert 'data-role="status-badge"' in template
    assert "checkedAtText" in template
    assert "last_success_at" in template


def test_internal_errors_are_not_rendered(template):
    """Cloud API 障害時に内部例外をそのまま表示しないこと。"""
    assert "監視情報を取得できませんでした" in template
    assert "内部の詳細情報は表示されません" in template
    # 例外オブジェクトを直接描画していないこと
    assert "{{ e }}" not in template
    assert "e.message" not in template


def test_permission_error_has_its_own_message(template):
    assert "res.status === 403" in template
    assert "権限がありません" in template
