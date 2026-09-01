"""単一パスワード認証のテスト (PRIDEV-481 とレビュー指摘 PRIDEV-518〜523)"""

import sys
import time
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.web import auth  # noqa: E402

TEST_PASSWORD = "correct-horse-battery-staple"


TEST_SECRET_KEY = "test-secret-key-for-signing-at-least-32-chars"


@pytest.fixture
def auth_env(monkeypatch):
    """認証を有効化した状態の設定を用意する (開発環境扱い)。"""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("AUTH_PUBLIC_PATH_PREFIXES", raising=False)
    monkeypatch.delenv("AUTH_TRUSTED_PROXY_COUNT", raising=False)
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


# --- next の検証とエスケープ (PRIDEV-519 / PRIDEV-520) -----------------------
@pytest.mark.parametrize(
    "candidate",
    [
        "//evil.example.com/steal",
        "https://evil.example.com/steal",
        "http://evil.example.com",
        "\\\\evil.example.com/steal",
        "/\\evil.example.com",
        "javascript:alert(1)",
        "relative/path",
        "/path\r\nSet-Cookie: x=1",
        "",
    ],
)
def test_safe_next_path_rejects_offsite_and_injection(candidate):
    assert auth._safe_next_path(candidate) == "/"


@pytest.mark.parametrize(
    "candidate,expected",
    [
        ("/system-monitor", "/system-monitor"),
        ("/system-monitor?date=2026-01-01&filter=all", "/system-monitor?date=2026-01-01&filter=all"),
        ("/api/charts/list?q=%E6%97%A5%E6%9C%AC%E8%AA%9E", "/api/charts/list?q=%E6%97%A5%E6%9C%AC%E8%AA%9E"),
        ("/path?a=1#fragment", "/path?a=1"),
    ],
)
def test_safe_next_path_keeps_same_origin_path_and_query(candidate, expected):
    assert auth._safe_next_path(candidate) == expected


def _hidden_next_attributes(body: str) -> dict:
    """ログイン画面をパースし、hidden input `next` の属性を返す。"""
    from html.parser import HTMLParser

    found: dict = {}

    class _Parser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "input" and attributes.get("name") == "next":
                found.update(attributes)

    _Parser().feed(body)
    return found


@pytest.mark.parametrize(
    "payload",
    [
        '/" autofocus onfocus=alert(1) x="',
        "/</textarea><script>alert(1)</script>",
        "/'onmouseover='alert(1)",
        "/path?q=<img src=x onerror=alert(1)>",
    ],
)
def test_login_page_escapes_next_value(client, payload):
    """`next` に引用符・山括弧・イベント属性を混ぜても HTML 構造が変わらないこと。"""
    body = client.get("/auth/login", params={"next": payload}).text

    attributes = _hidden_next_attributes(body)

    # 属性は type/name/value の 3 つだけ。属性を閉じて任意属性を注入できない。
    assert set(attributes) == {"type", "name", "value"}, attributes
    assert "<script" not in body.lower()
    assert "onerror" not in body or "&lt;img" in body


def test_login_page_escapes_error_message(client):
    """エラーメッセージ経路の動的値もエスケープされること。"""
    body = auth._render_login_page("/", '<img src=x onerror=alert(1)>')

    assert "<img src=x" not in body
    assert "&lt;img src=x onerror=alert(1)&gt;" in body


def test_login_preserves_query_after_authentication(client):
    """クエリ付きの next でログインすると path と query の両方へ戻る (PRIDEV-520)。"""
    target = "/system-monitor?date=2026-01-01&filter=all"
    response = client.post(
        "/auth/login",
        data={"password": TEST_PASSWORD, "next": target},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == target


# --- 認証無効時 / 平文パスワード (PRIDEV-523) --------------------------------
def test_auth_disabled_when_password_not_configured(monkeypatch):
    """開発環境でのみ、ハッシュ未設定なら認証は無効になる。"""
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    auth.reset_auth_settings_cache()
    try:
        settings = auth.get_auth_settings()
        assert settings.enabled is False
    finally:
        auth.reset_auth_settings_cache()


def test_plaintext_app_password_is_ignored(monkeypatch):
    """APP_PASSWORD (平文) を設定しても認証は有効にならない (PRIDEV-523)。"""
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("APP_PASSWORD", TEST_PASSWORD)
    auth.reset_auth_settings_cache()
    try:
        settings = auth.get_auth_settings()
        assert settings.enabled is False
        assert settings.password_hash == ""
    finally:
        auth.reset_auth_settings_cache()


def test_app_password_is_not_referenced_by_implementation():
    """実装が APP_PASSWORD を参照しないこと (Docs と挙動の一致)。"""
    source = (Path(__file__).resolve().parent.parent / "python" / "web" / "auth.py").read_text(
        encoding="utf-8"
    )

    assert 'getenv("APP_PASSWORD")' not in source
    assert 'getenv("APP_PASSWORD",' not in source


def test_docs_do_not_document_plaintext_password_env():
    """平文パスワードを環境変数へ保存する手順が Docs に存在しないこと。"""
    docs = (Path(__file__).resolve().parent.parent / "Docs" / "AUTH_SETUP.md").read_text(
        encoding="utf-8"
    )
    env_example = (Path(__file__).resolve().parent.parent / ".env.example").read_text(
        encoding="utf-8"
    )

    # 設定表の行 / 代入形式のどちらでも APP_PASSWORD を案内していないこと
    assert "| `APP_PASSWORD` |" not in docs
    assert "APP_PASSWORD=" not in docs
    assert "APP_PASSWORD=" not in env_example.replace("APP_PASSWORD_HASH=", "")


# --- 本番のフェイルクローズ (PRIDEV-521) --------------------------------------
@pytest.fixture
def production_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("AUTH_SECRET_KEY", raising=False)
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("WEB_CONCURRENCY", raising=False)
    auth.reset_auth_settings_cache()
    yield monkeypatch
    auth.reset_auth_settings_cache()


def test_production_requires_password_hash(production_env):
    production_env.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)

    with pytest.raises(auth.AuthConfigurationError, match="APP_PASSWORD_HASH"):
        auth.get_auth_settings()


def test_production_rejects_malformed_password_hash(production_env):
    production_env.setenv("APP_PASSWORD_HASH", "not-a-valid-hash")
    production_env.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)

    with pytest.raises(auth.AuthConfigurationError, match="APP_PASSWORD_HASH"):
        auth.get_auth_settings()


def test_production_requires_secret_key(production_env):
    production_env.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))

    with pytest.raises(auth.AuthConfigurationError, match="AUTH_SECRET_KEY"):
        auth.get_auth_settings()


def test_production_rejects_short_secret_key(production_env):
    production_env.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    production_env.setenv("AUTH_SECRET_KEY", "too-short")

    with pytest.raises(auth.AuthConfigurationError, match="AUTH_SECRET_KEY"):
        auth.get_auth_settings()


def test_production_rejects_multiple_workers(production_env):
    """ログイン試行制限がプロセス内保持のため複数ワーカーを拒否する (PRIDEV-522)。"""
    production_env.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    production_env.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)
    production_env.setenv("WEB_CONCURRENCY", "4")

    with pytest.raises(auth.AuthConfigurationError, match="ワーカー"):
        auth.get_auth_settings()


def test_production_forces_secure_cookie(production_env):
    production_env.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    production_env.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)
    production_env.setenv("AUTH_COOKIE_SECURE", "false")

    settings = auth.get_auth_settings()

    assert settings.is_production is True
    assert settings.cookie_secure is True


def test_unset_app_env_is_treated_as_production(production_env):
    """APP_ENV の設定漏れは本番扱い (フェイルオープンさせない)。"""
    production_env.delenv("APP_ENV", raising=False)

    assert auth.is_production_environment() is True
    with pytest.raises(auth.AuthConfigurationError):
        auth.get_auth_settings()


@pytest.mark.parametrize("app_env", ["local", "development", "dev", "test", "ci"])
def test_known_development_app_envs_allow_disabled_auth(production_env, app_env):
    production_env.setenv("APP_ENV", app_env)

    settings = auth.get_auth_settings()

    assert settings.is_production is False
    assert settings.enabled is False


def test_production_secure_cookie_is_issued(production_env):
    """本番設定で発行される Cookie に Secure が付く。"""
    production_env.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    production_env.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)

    app = FastAPI()
    app.include_router(auth.router)
    with TestClient(app, base_url="https://testserver") as production_client:
        response = production_client.post(
            "/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False
        )

    assert "Secure" in response.headers["set-cookie"]


# --- レート制限の実行環境要件 (PRIDEV-522) ------------------------------------
def test_client_key_ignores_forwarded_header_when_no_trusted_proxy(auth_env):
    request = _fake_request({"x-forwarded-for": "1.2.3.4"}, client_host="10.0.0.1")

    assert auth._client_key(request, auth_env) == "10.0.0.1"


@pytest.mark.parametrize(
    "proxy_count,forwarded,expected",
    [
        # プロキシ 1 段: 末尾はプロキシが記録した実際の接続元。左側はクライアントの自称値。
        ("1", "203.0.113.9", "203.0.113.9"),
        ("1", "1.2.3.4-spoofed, 203.0.113.9", "203.0.113.9"),
        # プロキシ 2 段: 末尾 1 個は内側プロキシ自身。その左が実クライアント。
        ("2", "203.0.113.9, 70.0.0.1", "203.0.113.9"),
        ("2", "1.2.3.4-spoofed, 203.0.113.9, 70.0.0.1", "203.0.113.9"),
        # 段数より短い場合でも左端より外へは出ない
        ("3", "203.0.113.9", "203.0.113.9"),
    ],
)
def test_client_key_uses_forwarded_header_behind_trusted_proxy(
    monkeypatch, proxy_count, forwarded, expected
):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)
    monkeypatch.setenv("AUTH_TRUSTED_PROXY_COUNT", proxy_count)
    auth.reset_auth_settings_cache()
    try:
        settings = auth.get_auth_settings()
        request = _fake_request({"x-forwarded-for": forwarded}, client_host="10.0.0.1")

        assert auth._client_key(request, settings) == expected
    finally:
        auth.reset_auth_settings_cache()


def test_spoofed_forwarded_header_cannot_reset_lockout(client, monkeypatch):
    """プロキシを信用しない既定設定では X-Forwarded-For を変えても迂回できない。"""
    monkeypatch.setenv("AUTH_MAX_LOGIN_ATTEMPTS", "2")
    auth.reset_auth_settings_cache()

    for _ in range(2):
        client.post("/auth/login", data={"password": "wrong"})

    locked = client.post(
        "/auth/login",
        data={"password": TEST_PASSWORD},
        headers={"X-Forwarded-For": "198.51.100.7"},
    )

    assert locked.status_code == 429


def test_lockout_expires_and_allows_login_again(client, monkeypatch):
    monkeypatch.setenv("AUTH_MAX_LOGIN_ATTEMPTS", "2")
    monkeypatch.setenv("AUTH_LOCKOUT_SECONDS", "1")
    auth.reset_auth_settings_cache()

    for _ in range(2):
        assert client.post("/auth/login", data={"password": "wrong"}).status_code == 401
    assert client.post("/auth/login", data={"password": TEST_PASSWORD}).status_code == 429

    time.sleep(1.1)

    unlocked = client.post(
        "/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False
    )

    assert unlocked.status_code == 303
    assert client.get("/protected").status_code == 200


def test_login_attempts_do_not_grow_without_bound(auth_env):
    """期限切れエントリを全体清掃し、追跡数に上限を設ける (PRIDEV-522)。"""
    now = time.time()
    for index in range(auth.MAX_TRACKED_CLIENTS + 50):
        auth._record_failure(f"10.0.{index // 256}.{index % 256}", auth_env, now)

    assert len(auth._login_attempts) <= auth.MAX_TRACKED_CLIENTS

    # ロックアウト期間を過ぎたエントリは他のキーの操作時に清掃される
    auth._purge_expired_attempts(auth_env, now + auth_env.lockout_seconds + 1)

    assert auth._login_attempts == {}


def _fake_request(headers: dict, client_host: str):
    """Starlette Request を最小限のスコープから組み立てる。"""
    from starlette.requests import Request as StarletteRequest

    return StarletteRequest(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/login",
            "headers": [
                (key.encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()
            ],
            "client": (client_host, 12345),
            "query_string": b"",
        }
    )


# --- 公開パス / 保護対象パスの判定 (PRIDEV-518) -------------------------------
@pytest.mark.parametrize(
    "path",
    ["/auth/login", "/auth/logout", "/api/auth/status", "/health", "/static/app.css"],
)
def test_public_paths_are_not_protected(auth_env, path):
    assert auth.is_public_path(path, auth_env) is True
    assert auth.is_protected_path(path, auth_env) is False


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/system-monitor",
        "/api/system-monitor",
        "/api/rules/active",
        "/api/actions/status",
        "/api/signals/latest",
        "/api/watchlist",
        "/api/charts/list",
        "/api/analytics/summary",
        "/api/simulate/simulate",
        "/docs",
        "/openapi.json",
        "/api/newly-added-route",
        "/healthcheck-lookalike",
    ],
)
def test_everything_else_is_protected_by_default(auth_env, path):
    assert auth.is_protected_path(path, auth_env) is True


def test_public_prefixes_are_configurable_but_login_stays_public(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_PASSWORD_HASH", auth.hash_password(TEST_PASSWORD))
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_SECRET_KEY)
    monkeypatch.setenv("AUTH_PUBLIC_PATH_PREFIXES", "/public")
    auth.reset_auth_settings_cache()
    try:
        settings = auth.get_auth_settings()
        assert auth.is_public_path("/public/thing", settings) is True
        # ログインへ到達できないと復旧不能になるため常に公開
        assert auth.is_public_path(auth.LOGIN_PATH, settings) is True
        assert auth.is_protected_path("/health", settings) is True
    finally:
        auth.reset_auth_settings_cache()


# --- アプリ全体の保護 (middleware + ルーター依存) ------------------------------
# 未認証時に拒否され、認証後に到達できることを確認する既存の管理画面 / 管理 API。
PROTECTED_ROUTES = [
    "/",
    "/api/rules/active",
    "/api/rules/default",
    "/api/rules/history",
    "/api/actions/status",
    "/api/signals/status",
    "/api/watchlist",
    "/api/charts/list",
    "/api/analytics/summary",
    "/system-monitor",
    "/api/system-monitor",
    "/docs",
    "/openapi.json",
]


@pytest.fixture
def real_client(auth_env):
    """本体アプリを lifespan なしで起動し、認証ガードだけを検証する。"""
    from python.web.app import app as real_app

    return TestClient(real_app)


@pytest.mark.parametrize("path", PROTECTED_ROUTES)
def test_real_app_rejects_unauthenticated_access(real_client, path):
    response = real_client.get(path, follow_redirects=False)

    if path.startswith("/api/"):
        assert response.status_code == 401, path
    else:
        assert response.status_code == 303, path
        assert response.headers["location"].startswith(auth.LOGIN_PATH), path


@pytest.mark.parametrize("path", ["/auth/login", "/api/auth/status", "/health"])
def test_real_app_keeps_public_routes_reachable(real_client, path):
    assert real_client.get(path, follow_redirects=False).status_code == 200, path


def test_real_app_redirect_preserves_original_query(real_client):
    response = real_client.get(
        "/system-monitor?date=2026-01-01&filter=all", follow_redirects=False
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert location == "/auth/login?next=%2Fsystem-monitor%3Fdate%3D2026-01-01%26filter%3Dall"


def test_real_app_allows_authenticated_access(real_client):
    """認証後は保護対象へ到達できる (404/500 でも 401/303 ではない)。"""
    login = real_client.post(
        "/auth/login", data={"password": TEST_PASSWORD}, follow_redirects=False
    )
    assert login.status_code == 303

    for path in ("/", "/api/rules/active", "/docs", "/openapi.json"):
        status_code = real_client.get(path, follow_redirects=False).status_code
        assert status_code not in (401, 303), f"{path} -> {status_code}"


def test_every_registered_route_is_protected_or_explicitly_public(auth_env):
    """アプリへ登録された全ルートが、保護対象か明示された公開ルートのどちらかであること。

    新しいルートを追加しても既定で保護されるため、このテストは
    「公開してよい理由を Docs へ書かずに公開ルートを増やした」場合にだけ失敗する。
    """
    from python.web.app import app as real_app

    # Docs/AUTH_SETUP.md 「3. 保護対象と公開ルート」の表と一致させること
    documented_public = {
        "/auth/login",
        "/auth/logout",
        "/api/auth/status",
        "/health",
    }

    unexpected_public = {
        route.path
        for route in real_app.routes
        if getattr(route, "path", None) and auth.is_public_path(route.path, auth_env)
    } - documented_public

    assert unexpected_public == set(), (
        f"公開ルートが増えています: {sorted(unexpected_public)}。"
        " 公開してよい理由を Docs/AUTH_SETUP.md へ記載し、本テストの表を更新してください"
    )


def test_real_app_is_open_when_auth_disabled_in_development(monkeypatch):
    """開発環境で認証無効なら既存導線を壊さない。"""
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    auth.reset_auth_settings_cache()
    try:
        from python.web.app import app as real_app

        assert TestClient(real_app).get("/", follow_redirects=False).status_code == 200
    finally:
        auth.reset_auth_settings_cache()
