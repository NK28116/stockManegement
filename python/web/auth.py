# python/web/auth.py
"""単一管理者向けパスワード認証 (PRIDEV-481)

管理画面 / 管理API を未認証アクセスから保護するための最小構成の認証基盤。

設計方針:
  * パスワードはコードへ直書きせず、環境変数 (または Secret Manager) から取得する。
  * 保存するのは平文ではなく PBKDF2-HMAC-SHA256 ハッシュ。
  * セッションは HMAC 署名付き Cookie で表現し、サーバ側ストアを持たない。
  * パスワード・Cookie 値・ハッシュはログへ出力しない。

外部化された設定値の一覧と設定手順は Docs/AUTH_SETUP.md を参照。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from python.utils.logger import get_logger

logger = get_logger("web", "auth")

__all__ = [
    "AUTH_COOKIE_NAME",
    "AuthSettings",
    "get_auth_settings",
    "hash_password",
    "is_authenticated",
    "require_auth",
    "reset_auth_settings_cache",
    "router",
    "verify_password",
]

AUTH_COOKIE_NAME = "sm_session"
LOGIN_PATH = "/auth/login"

_HASH_SCHEME = "pbkdf2_sha256"
_HASH_ITERATIONS = 390_000
_SALT_BYTES = 16


# --- パスワードハッシュ -------------------------------------------------------
def hash_password(password: str, *, iterations: int = _HASH_ITERATIONS) -> str:
    """パスワードを `pbkdf2_sha256$<iterations>$<salt>$<hash>` 形式へ変換する。"""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{_HASH_SCHEME}${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """パスワードとハッシュを定数時間で比較する。形式不正時は False。"""
    try:
        scheme, iterations_raw, salt_b64, digest_b64 = encoded_hash.split("$")
        if scheme != _HASH_SCHEME:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        iterations = int(iterations_raw)
    except (ValueError, TypeError, base64.binascii.Error):
        # ハッシュ値そのものはログへ出さない
        logger.warning("APP_PASSWORD_HASH の形式が不正です")
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


# --- 設定 ---------------------------------------------------------------------
def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning(f"{name} の値が整数として解釈できないため既定値 {default} を使用します")
        return default


@dataclass(frozen=True)
class AuthSettings:
    """認証まわりの外部化された設定値。

    session_max_age_seconds / max_login_attempts / lockout_seconds は
    ユーザー確認待ちの暫定値 (Docs/AUTH_SETUP.md の確認事項 16, 17)。
    確定後は環境変数、または本 dataclass の既定値 1 箇所の変更で反映できる。
    """

    password_hash: str
    secret_key: str
    session_max_age_seconds: int
    max_login_attempts: int
    lockout_seconds: int
    protected_prefixes: Tuple[str, ...]
    cookie_secure: bool

    @property
    def enabled(self) -> bool:
        """パスワードが設定されている場合のみ認証を有効とする。"""
        return bool(self.password_hash)


# TODO(PRIDEV-481): 以下 3 つはユーザー確認待ちの暫定値。確定後はここを変更する。
DEFAULT_SESSION_MAX_AGE_SECONDS = 12 * 60 * 60  # 暫定 12 時間
DEFAULT_MAX_LOGIN_ATTEMPTS = 5  # 暫定 5 回
DEFAULT_LOCKOUT_SECONDS = 15 * 60  # 暫定 15 分

# 認証を必須とするパスの既定値。System Monitor (PRIDEV-492/493) を保護対象とする。
DEFAULT_PROTECTED_PREFIXES = "/system-monitor,/api/system-monitor"

_settings_cache: Optional[AuthSettings] = None


def _load_password_hash() -> str:
    """設定済みのパスワードハッシュを返す。未設定なら空文字。"""
    encoded = os.getenv("APP_PASSWORD_HASH", "").strip()
    if encoded:
        return encoded

    # 開発用フォールバック。平文をそのまま保持せず、起動時にハッシュ化する。
    plain = os.getenv("APP_PASSWORD", "").strip()
    if plain:
        logger.warning(
            "APP_PASSWORD (平文) が使用されています。本番環境では APP_PASSWORD_HASH を設定してください"
        )
        return hash_password(plain)
    return ""


def get_auth_settings() -> AuthSettings:
    """環境変数から AuthSettings を構築する (プロセス内でキャッシュ)。"""
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache

    password_hash = _load_password_hash()
    secret_key = os.getenv("AUTH_SECRET_KEY", "").strip()
    if not secret_key:
        # 未設定でも動作はするが、再起動でセッションが無効化される点を明示する。
        secret_key = secrets.token_urlsafe(32)
        if password_hash:
            logger.warning(
                "AUTH_SECRET_KEY が未設定のため一時キーを生成しました。"
                "再起動でログイン状態が失われます"
            )

    prefixes = tuple(
        prefix.strip()
        for prefix in os.getenv(
            "AUTH_PROTECTED_PATH_PREFIXES", DEFAULT_PROTECTED_PREFIXES
        ).split(",")
        if prefix.strip()
    )
    # ローカル開発 (http) では Secure Cookie がブラウザに保存されないため既定を落とす。
    cookie_secure = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower() not in ("0", "false", "no")
    if os.getenv("AUTH_COOKIE_SECURE", "").strip() == "":
        cookie_secure = os.getenv("APP_ENV", "local").lower() != "local"

    _settings_cache = AuthSettings(
        password_hash=password_hash,
        secret_key=secret_key,
        session_max_age_seconds=_env_int(
            "AUTH_SESSION_MAX_AGE_SECONDS", DEFAULT_SESSION_MAX_AGE_SECONDS
        ),
        max_login_attempts=_env_int("AUTH_MAX_LOGIN_ATTEMPTS", DEFAULT_MAX_LOGIN_ATTEMPTS),
        lockout_seconds=_env_int("AUTH_LOCKOUT_SECONDS", DEFAULT_LOCKOUT_SECONDS),
        protected_prefixes=prefixes,
        cookie_secure=cookie_secure,
    )
    if not password_hash:
        logger.warning(
            "APP_PASSWORD_HASH / APP_PASSWORD が未設定のため認証は無効です。"
            "公開環境では必ず設定してください"
        )
    return _settings_cache


def reset_auth_settings_cache() -> None:
    """環境変数を差し替えたテスト等からキャッシュを破棄する。"""
    global _settings_cache
    _settings_cache = None
    _login_attempts.clear()


# --- セッショントークン -------------------------------------------------------
def _sign(payload: str, secret_key: str) -> str:
    digest = hmac.new(secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def issue_session_token(settings: AuthSettings, *, now: Optional[float] = None) -> str:
    """`<expires_at>.<signature>` 形式の署名付きトークンを発行する。"""
    issued_at = int(now if now is not None else time.time())
    expires_at = issued_at + settings.session_max_age_seconds
    payload = str(expires_at)
    return f"{payload}.{_sign(payload, settings.secret_key)}"


def verify_session_token(token: str, settings: AuthSettings, *, now: Optional[float] = None) -> bool:
    """トークンの署名と有効期限を検証する。"""
    if not token:
        return False
    payload, _, signature = token.partition(".")
    if not signature:
        return False
    if not hmac.compare_digest(_sign(payload, settings.secret_key), signature):
        return False
    try:
        expires_at = int(payload)
    except ValueError:
        return False
    return expires_at > (now if now is not None else time.time())


# --- ログイン試行のレート制限 -------------------------------------------------
_login_attempts: Dict[str, Tuple[int, float]] = {}


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _is_locked_out(key: str, settings: AuthSettings, now: float) -> bool:
    failures, last_failure_at = _login_attempts.get(key, (0, 0.0))
    if failures < settings.max_login_attempts:
        return False
    if now - last_failure_at >= settings.lockout_seconds:
        _login_attempts.pop(key, None)
        return False
    return True


def _record_failure(key: str, now: float) -> None:
    failures, _ = _login_attempts.get(key, (0, 0.0))
    _login_attempts[key] = (failures + 1, now)


# --- 認証判定 -----------------------------------------------------------------
def is_authenticated(request: Request, settings: Optional[AuthSettings] = None) -> bool:
    """リクエストが認証済みかどうかを返す。認証無効時は常に True。"""
    settings = settings or get_auth_settings()
    if not settings.enabled:
        return True
    return verify_session_token(request.cookies.get(AUTH_COOKIE_NAME, ""), settings)


async def require_auth(request: Request) -> None:
    """認証必須ルート用の共通ガード (FastAPI 依存関数)。"""
    if is_authenticated(request):
        return
    logger.info(f"未認証アクセスを拒否しました: {request.url.path}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証が必要です",
        headers={"WWW-Authenticate": "Cookie"},
    )


def is_protected_path(path: str, settings: Optional[AuthSettings] = None) -> bool:
    settings = settings or get_auth_settings()
    return any(path.startswith(prefix) for prefix in settings.protected_prefixes)


# --- ルーティング -------------------------------------------------------------
router = APIRouter(tags=["auth"])

_LOGIN_PAGE = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ログイン | Stock Management</title>
  <style>
    body {{ font-family: system-ui, sans-serif; display: flex; align-items: center;
           justify-content: center; min-height: 100vh; margin: 0; background: #f3f4f6; }}
    form {{ background: #fff; padding: 2rem; border-radius: 8px; min-width: 18rem;
            box-shadow: 0 1px 3px rgba(0,0,0,.2); }}
    h1 {{ font-size: 1.1rem; margin: 0 0 1rem; }}
    input {{ width: 100%; box-sizing: border-box; padding: .5rem; margin-bottom: 1rem;
             border: 1px solid #d1d5db; border-radius: 4px; }}
    button {{ width: 100%; padding: .5rem; border: 0; border-radius: 4px;
              background: #2563eb; color: #fff; cursor: pointer; }}
    .error {{ color: #b91c1c; font-size: .85rem; margin-bottom: .75rem; }}
  </style>
</head>
<body>
  <form method="post" action="{login_path}">
    <h1>Stock Management</h1>
    {error_block}
    <input type="hidden" name="next" value="{next_path}">
    <label for="password">パスワード</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">ログイン</button>
  </form>
</body>
</html>
"""


def _render_login_page(next_path: str = "/", error: str = "") -> str:
    error_block = f'<p class="error">{error}</p>' if error else ""
    return _LOGIN_PAGE.format(login_path=LOGIN_PATH, next_path=next_path, error_block=error_block)


def _safe_next_path(candidate: str) -> str:
    """オープンリダイレクトを避けるため、同一オリジンの絶対パスのみ許可する。"""
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return "/"


@router.get(LOGIN_PATH, response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/") -> Response:
    if is_authenticated(request):
        return RedirectResponse(_safe_next_path(next), status_code=status.HTTP_303_SEE_OTHER)
    return HTMLResponse(_render_login_page(_safe_next_path(next)))


@router.post(LOGIN_PATH)
async def login(request: Request, password: str = Form(...), next: str = Form("/")) -> Response:
    settings = get_auth_settings()
    next_path = _safe_next_path(next)
    now = time.time()
    key = _client_key(request)

    if _is_locked_out(key, settings, now):
        logger.warning("ログイン試行がロックアウト中のため拒否しました")
        return _login_failure_response(
            request,
            next_path,
            "試行回数の上限に達しました。しばらく待って再試行してください",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if not settings.enabled:
        logger.warning("パスワード未設定のためログイン要求を拒否しました")
        return _login_failure_response(
            request, next_path, "サーバー側でパスワードが設定されていません", status.HTTP_503_SERVICE_UNAVAILABLE
        )

    if not verify_password(password, settings.password_hash):
        _record_failure(key, now)
        logger.info("ログインに失敗しました")  # パスワードは出力しない
        return _login_failure_response(request, next_path, "パスワードが正しくありません", status.HTTP_401_UNAUTHORIZED)

    _login_attempts.pop(key, None)
    logger.info("ログインに成功しました")
    response: Response
    if _wants_json(request):
        response = JSONResponse({"authenticated": True})
    else:
        response = RedirectResponse(next_path, status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, settings)
    return response


def _wants_json(request: Request) -> bool:
    return "application/json" in request.headers.get("accept", "")


def _login_failure_response(request: Request, next_path: str, message: str, status_code: int) -> Response:
    if _wants_json(request):
        return JSONResponse({"detail": message}, status_code=status_code)
    return HTMLResponse(_render_login_page(next_path, message), status_code=status_code)


def _set_session_cookie(response: Response, settings: AuthSettings) -> None:
    response.set_cookie(
        AUTH_COOKIE_NAME,
        issue_session_token(settings),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post("/auth/logout")
async def logout(request: Request) -> Response:
    logger.info("ログアウトしました")
    response: Response
    if _wants_json(request):
        response = JSONResponse({"authenticated": False})
    else:
        response = RedirectResponse(LOGIN_PATH, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@router.get("/api/auth/status")
async def auth_status(request: Request) -> Dict[str, bool]:
    settings = get_auth_settings()
    return {
        "auth_enabled": settings.enabled,
        "authenticated": is_authenticated(request, settings),
    }
