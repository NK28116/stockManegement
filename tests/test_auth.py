"""単一パスワード認証のテスト (PRIDEV-481)"""

import sys
import time
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.web import auth  # noqa: E402

TEST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def auth_env(monkeypatch):
    """認証を有効化した状態の設定を用意する。"""
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key-for-signing")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    auth.reset_auth_settings_cache()
    yield auth.get_auth_settings()
    auth.reset_auth_settings_cache()


@pytest.fixture
def client(auth_env):
    """auth ルーターと認証必須ルートだけを載せた最小アプリ。"""
    app = FastAPI()
    app.include_router(auth.router)

    @app.get("/protected", dependencies=[Depends(auth.require_auth)])
    async def protected():
        return {"ok": True}

    with TestClient(app) as test_client:
        yield test_client


# --- パスワードハッシュ -------------------------------------------------------
def test_hash_password_is_salted_and_verifiable():
    first = auth.hash_password(TEST_PASSWORD)
    second = auth.hash_password(TEST_PASSWORD)

    assert first != second, "salt によりハッシュは毎回変わること"
    assert TEST_PASSWORD not in first, "平文がハッシュへ含まれないこと"
    assert auth.verify_password(TEST_PASSWORD, first)
    assert auth.verify_password(TEST_PASSWORD, second)


def test_verify_password_rejects_wrong_password_and_broken_hash():
    encoded = auth.hash_password(TEST_PASSWORD)

    assert auth.verify_password("wrong-password", encoded) is False
    assert auth.verify_password(TEST_PASSWORD, "not-a-valid-hash") is False
    assert auth.verify_password(TEST_PASSWORD, "md5$1$aaaa$bbbb") is False


# --- セッショントークン -------------------------------------------------------
def test_session_token_roundtrip_and_expiry(auth_env):
    now = time.time()
    token = auth.issue_session_token(auth_env, now=now)

    assert auth.verify_session_token(token, auth_env, now=now) is True
    expired_at = now + auth_env.session_max_age_seconds + 1
    assert auth.verify_session_token(token, auth_env, now=expired_at) is False


def test_session_token_rejects_tampering(auth_env):
    token = auth.issue_session_token(auth_env)
    payload, _, signature = token.partition(".")
    forged = f"{int(payload) + 10_000}.{signature}"

    assert auth.verify_session_token(forged, auth_env) is False
    assert auth.verify_session_token("", auth_env) is False
    assert auth.verify_session_token("no-signature", auth_env) is False


# --- ログイン / ログアウト ----------------------------------------------------
def test_unauthenticated_access_is_rejected(client):
    assert client.get("/protected").status_code == 401


def test_login_with_correct_password_grants_access(client):
    response = client.post("/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False)

    assert response.status_code == 303
    assert auth.AUTH_COOKIE_NAME in response.cookies
    assert client.get("/protected").status_code == 200


def test_login_with_wrong_password_is_rejected(client):
    response = client.post("/auth/login", data={"password": "wrong-password"}, follow_redirects=False)

    assert response.status_code == 401
    assert auth.AUTH_COOKIE_NAME not in response.cookies
    assert client.get("/protected").status_code == 401


def test_logout_revokes_access(client):
    client.post("/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False)
    assert client.get("/protected").status_code == 200

    client.post("/auth/logout", follow_redirects=False)

    assert client.get("/protected").status_code == 401


def test_session_cookie_is_httponly_and_not_the_password(client):
    response = client.post("/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False)
    set_cookie = response.headers["set-cookie"]

    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie.replace("samesite", "SameSite")
    assert TEST_PASSWORD not in set_cookie


def test_auth_status_reports_state(client):
    assert client.get("/api/auth/status").json() == {"auth_enabled": True, "authenticated": False}

    client.post("/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False)

    assert client.get("/api/auth/status").json() == {"auth_enabled": True, "authenticated": True}


def test_login_page_does_not_leak_configured_password(client):
    body = client.get("/auth/login").text

    assert TEST_PASSWORD not in body
    assert "APP_PASSWORD" not in body


def test_login_next_path_cannot_redirect_offsite(client):
    response = client.post(
        "/auth/login",
        data={"password": TEST_PASSWORD, "next": "//evil.example.com/steal"},
        follow_redirects=False,
    )

    assert response.headers["location"] == "/"


# --- レート制限 ---------------------------------------------------------------
def test_repeated_failures_are_locked_out(client, monkeypatch):
    monkeypatch.setenv("AUTH_MAX_LOGIN_ATTEMPTS", "3")
    auth.reset_auth_settings_cache()

    for _ in range(3):
        assert client.post("/auth/login", data={"password": "wrong"}).status_code == 401

    locked = client.post("/auth/login", data={"password": TEST_PASSWORD})

    assert locked.status_code == 429
    assert client.get("/protected").status_code == 401


# --- ログ出力 -----------------------------------------------------------------
def test_login_does_not_log_password_or_cookie(client, caplog):
    with caplog.at_level("INFO", logger="auth.web"):
        client.post("/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False)
        client.post("/auth/login", data={"password": "wrong-password"}, follow_redirects=False)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert TEST_PASSWORD not in logged
    assert "wrong-password" not in logged
    assert auth.AUTH_COOKIE_NAME not in logged


# --- 認証無効時 ---------------------------------------------------------------
def test_auth_disabled_when_password_not_configured(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    auth.reset_auth_settings_cache()
    try:
        settings = auth.get_auth_settings()
        assert settings.enabled is False
    finally:
        auth.reset_auth_settings_cache()


def test_plaintext_app_password_is_hashed_at_load(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("APP_PASSWORD", TEST_PASSWORD)
    auth.reset_auth_settings_cache()
    try:
        settings = auth.get_auth_settings()
        assert settings.enabled is True
        assert settings.password_hash != TEST_PASSWORD
        assert auth.verify_password(TEST_PASSWORD, settings.password_hash)
    finally:
        auth.reset_auth_settings_cache()


# --- 保護対象パスの判定 -------------------------------------------------------
def test_protected_prefixes_are_configurable(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    monkeypatch.setenv("AUTH_PROTECTED_PATH_PREFIXES", "/admin,/api/admin")
    auth.reset_auth_settings_cache()
    try:
        settings = auth.get_auth_settings()
        assert auth.is_protected_path("/api/admin/things", settings) is True
        assert auth.is_protected_path("/admin", settings) is True
        assert auth.is_protected_path("/api/charts/list", settings) is False
    finally:
        auth.reset_auth_settings_cache()


def test_default_protected_prefixes_cover_system_monitor(auth_env):
    assert auth.is_protected_path("/system-monitor", auth_env) is True
    assert auth.is_protected_path("/api/system-monitor", auth_env) is True
    assert auth.is_protected_path("/", auth_env) is False


# --- アプリ全体の保護 (middleware) --------------------------------------------
def test_app_middleware_blocks_protected_paths(auth_env):
    """本体アプリの middleware が保護対象パスを遮断することを確認する。"""
    from python.web.app import app as real_app

    # lifespan (DB 同期) を起動せず middleware だけを検証する
    real_client = TestClient(real_app)

    api_response = real_client.get("/api/system-monitor", follow_redirects=False)
    page_response = real_client.get("/system-monitor", follow_redirects=False)

    # ルート自体は未実装 (PRIDEV-492/493) だが、認証ガードは経路解決より前段で働く
    assert api_response.status_code == 401
    assert page_response.status_code == 303
    assert page_response.headers["location"].startswith(auth.LOGIN_PATH)

    # 保護対象外の既存経路は認証なしで到達できる (既存導線を壊さない)
    assert real_client.get("/").status_code == 200
