"""初回起動待ちの短縮と失敗時 UX の回帰テスト (PRIDEV-485)"""

import re
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.web import startup  # noqa: E402

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "python" / "web" / "templates" / "index.html"


@pytest.fixture(autouse=True)
def reset_startup_state():
    startup.reset_startup_settings_cache()
    startup.metrics.reset()
    yield
    startup.reset_startup_settings_cache()
    startup.metrics.reset()


# --- 設定値の外部化 -----------------------------------------------------------
def test_default_settings_are_the_documented_provisional_values():
    settings = startup.get_startup_settings()

    assert settings.target_seconds == startup.DEFAULT_TARGET_SECONDS
    assert settings.loading_delay_seconds == startup.DEFAULT_LOADING_DELAY_SECONDS
    assert settings.timeout_seconds == startup.DEFAULT_TIMEOUT_SECONDS


def test_settings_come_from_environment(monkeypatch):
    monkeypatch.setenv("STARTUP_TARGET_SECONDS", "5")
    monkeypatch.setenv("STARTUP_LOADING_DELAY_SECONDS", "0.25")
    monkeypatch.setenv("STARTUP_TIMEOUT_SECONDS", "12.5")
    startup.reset_startup_settings_cache()

    settings = startup.get_startup_settings()

    assert (settings.target_seconds, settings.loading_delay_seconds, settings.timeout_seconds) == (
        5.0,
        0.25,
        12.5,
    )


@pytest.mark.parametrize("bad_value", ["", "abc", "-1"])
def test_invalid_settings_fall_back_to_defaults(monkeypatch, bad_value):
    monkeypatch.setenv("STARTUP_TIMEOUT_SECONDS", bad_value)
    startup.reset_startup_settings_cache()

    assert startup.get_startup_settings().timeout_seconds == startup.DEFAULT_TIMEOUT_SECONDS


def test_client_config_is_exposed_in_milliseconds(monkeypatch):
    monkeypatch.setenv("STARTUP_LOADING_DELAY_SECONDS", "1.5")
    startup.reset_startup_settings_cache()

    assert startup.get_startup_settings().to_client_config() == {
        "targetMs": 10000,
        "loadingDelayMs": 1500,
        "timeoutMs": 30000,
    }


# --- 計測 ---------------------------------------------------------------------
def test_metrics_measure_elapsed_time():
    startup.run_warmup(lambda: time.sleep(0.05))

    status = startup.startup_status()

    assert status["ready"] is True
    assert status["degraded"] is False
    assert status["elapsed_seconds"] >= 0.05
    assert status["within_target"] is True


def test_metrics_flag_target_overrun(monkeypatch):
    monkeypatch.setenv("STARTUP_TARGET_SECONDS", "0.01")
    startup.reset_startup_settings_cache()

    startup.run_warmup(lambda: time.sleep(0.05))

    assert startup.startup_status()["within_target"] is False


def test_elapsed_is_frozen_after_ready():
    startup.run_warmup(lambda: None)
    first = startup.metrics.elapsed_seconds
    time.sleep(0.05)

    assert startup.metrics.elapsed_seconds == first, "完了後の所要時間が伸びてはいけない"


# --- 失敗時 -------------------------------------------------------------------
def test_warmup_failure_is_degraded_not_a_crash():
    def broken():
        raise RuntimeError("DB へ接続できません")

    result = startup.run_warmup(broken)

    assert result.ready is True, "失敗しても起動待ちのままにしない"
    assert result.failed is True
    status = startup.startup_status()
    assert status["degraded"] is True
    assert "RuntimeError" in status["detail"]


# --- アプリ全体 ---------------------------------------------------------------
@pytest.fixture
def slow_warmup_app(monkeypatch):
    """起動処理に時間がかかるアプリを組み立てる。"""
    monkeypatch.setenv("DB_TYPE", "sqlite")
    from python.web import app as app_module

    started = threading.Event()

    def slow():
        started.set()
        time.sleep(0.5)

    monkeypatch.setattr(app_module, "_warmup", slow)
    return app_module.app, started


def test_first_request_is_not_blocked_by_warmup(slow_warmup_app):
    """起動処理がリクエスト経路から分離されていること (AC: 無反応な画面にならない)。"""
    app, started = slow_warmup_app

    with TestClient(app) as client:
        began = time.monotonic()
        response = client.get("/api/startup/status")
        elapsed = time.monotonic() - began

        assert response.status_code == 200
        assert elapsed < 0.4, f"起動処理がリクエストをブロックしている ({elapsed:.2f}s)"
        assert started.wait(timeout=2), "warmup がバックグラウンドで開始されていない"
        assert response.json()["ready"] is False


def test_startup_status_becomes_ready(slow_warmup_app):
    app, _ = slow_warmup_app

    with TestClient(app) as client:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            payload = client.get("/api/startup/status").json()
            if payload["ready"]:
                break
            time.sleep(0.05)

        assert payload["ready"] is True
        assert payload["degraded"] is False
        assert payload["elapsed_seconds"] >= 0.5


def test_warmup_failure_does_not_break_the_app(monkeypatch):
    monkeypatch.setenv("DB_TYPE", "sqlite")
    from python.web import app as app_module

    monkeypatch.setattr(app_module, "_warmup", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    with TestClient(app_module.app) as client:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            payload = client.get("/api/startup/status").json()
            if payload["ready"]:
                break
            time.sleep(0.05)

        assert payload["degraded"] is True
        assert client.get("/").status_code == 200, "起動処理の失敗で画面が落ちてはいけない"


def test_client_receives_server_side_thresholds(monkeypatch):
    monkeypatch.setenv("DB_TYPE", "sqlite")
    monkeypatch.setenv("STARTUP_TIMEOUT_SECONDS", "7")
    startup.reset_startup_settings_cache()
    from python.web.app import app

    body = TestClient(app).get("/").text
    injected = re.search(r"window\.__STARTUP_CONFIG__ = (\{.*?\});", body)

    assert injected, "テンプレートへ起動待ち設定が注入されていない"
    assert '"timeoutMs": 7000' in injected.group(1)


# --- フロントエンド (静的検証) ------------------------------------------------
@pytest.fixture(scope="module")
def template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def test_frontend_uses_injected_thresholds_not_hardcoded(template):
    """しきい値がテンプレートへ直書きされていないこと。"""
    assert "window.__STARTUP_CONFIG__" in template
    assert "this.startupConfig.timeoutMs" in template
    assert "this.startupConfig.loadingDelayMs" in template


def test_frontend_has_retry_affordance(template):
    """timeout 時に再試行できること。"""
    assert 'v-if="startupTimedOut"' in template
    assert "retryStartup" in template
    assert "再試行" in template


def test_frontend_delays_loading_indicator(template):
    """遅延時間を超えるまで loading 表示を出さないこと (ちらつき防止)。"""
    match = re.search(r"noteStartupWait\(startedAt\) \{(.*?)\n                \}", template, re.DOTALL)
    assert match, "noteStartupWait が見つからない"

    assert "loadingDelayMs" in match.group(1)


def test_frontend_records_measurable_wait_time(template):
    """起動待ち時間を比較できる形で残していること。"""
    assert "recordStartupSuccess" in template
    assert "[startup] 起動待ち" in template
    assert "startupWaitMs" in template
