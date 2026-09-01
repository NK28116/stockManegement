# python/web/auth.py
"""単一管理者向けパスワード認証 (PRIDEV-481)

管理画面 / 管理API を未認証アクセスから保護するための最小構成の認証基盤。

設計方針:
  * パスワードはコードへ直書きせず、環境変数 (または Secret Manager) から取得する。
  * 保存するのは平文ではなく PBKDF2-HMAC-SHA256 ハッシュ。平文は受け付けない (PRIDEV-523)。
  * セッションは HMAC 署名付き Cookie で表現し、サーバ側ストアを持たない。
  * 本番環境では設定不足を起動時に失敗させる (フェイルクローズ, PRIDEV-521)。
  * 保護対象は「公開パス以外すべて」とし、列挙漏れで穴が開かないようにする (PRIDEV-518)。
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
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from python.utils.logger import get_logger

logger = get_logger("web", "auth")

__all__ = [
    "AUTH_COOKIE_NAME",
    "AuthConfigurationError",
    "AuthSettings",
    "get_auth_settings",
    "hash_password",
    "is_authenticated",
    "is_protected_path",
    "is_public_path",
    "require_auth",
    "reset_auth_settings_cache",
    "router",
    "verify_password",
]

AUTH_COOKIE_NAME = "sm_session"
LOGIN_PATH = "/auth/login"


class AuthConfigurationError(RuntimeError):
    """本番環境で認証設定が不足・不正な場合に送出する (起動を失敗させる)。"""


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
    ユーザー確認済みの確定値 (Docs/AUTH_SETUP.md 参照)。
    変更する場合は環境変数、または本モジュールの既定値定数を変更する。
    """

    password_hash: str
    secret_key: str
    session_max_age_seconds: int
    max_login_attempts: int
    lockout_seconds: int
    public_prefixes: Tuple[str, ...]
    cookie_secure: bool
    is_production: bool
    trusted_proxy_count: int

    @property
    def enabled(self) -> bool:
        """パスワードハッシュが設定されている場合のみ認証を有効とする。

        本番環境では未設定だと `get_auth_settings()` が例外を送出するため、
        `enabled == False` になり得るのは開発環境だけ (PRIDEV-521)。
        """
        return bool(self.password_hash)


# 以下 3 つはユーザー確認済みの確定値 (PRIDEV-481)
DEFAULT_SESSION_MAX_AGE_SECONDS = 12 * 60 * 60  # 12 時間
DEFAULT_MAX_LOGIN_ATTEMPTS = 5  # 5 回失敗で
DEFAULT_LOCKOUT_SECONDS = 15 * 60  # 15 分ロック

# 認証を無効にできる (= 開発とみなす) APP_ENV の値。
# APP_ENV 未設定は「本番」として扱い、設定漏れが認証無効へ倒れないようにする。
DEVELOPMENT_APP_ENVS = ("local", "development", "dev", "test", "ci")

# 本番で要求する AUTH_SECRET_KEY の最小長 (token_urlsafe(32) は 43 文字)。
MIN_SECRET_KEY_LENGTH = 32

# 認証なしで到達できるパス (PRIDEV-518)。
# これ以外はすべて保護対象とし、ルート追加時の列挙漏れで穴が開かないようにする。
#   /auth/login       : ログインフォームそのもの
#   /auth/logout      : 未認証でも安全 (Cookie 破棄のみ)
#   /api/auth/status  : 画面が認証状態を判定するための最小情報のみ返す
#   /health           : 外形監視 / PaaS のヘルスチェック (認証を要求すると死活監視が破綻する)
#   /static           : 認証前のログイン画面が参照する静的アセット
DEFAULT_PUBLIC_PREFIXES = "/auth/login,/auth/logout,/api/auth/status,/health,/static"

# ログインフォームへ到達できないと復旧不能になるため、常に公開扱いとするパス。
MANDATORY_PUBLIC_PREFIXES = (LOGIN_PATH,)

_settings_cache: Optional[AuthSettings] = None


def is_production_environment() -> bool:
    """APP_ENV が既知の開発値でない場合は本番として扱う (フェイルクローズ)。"""
    return os.getenv("APP_ENV", "").strip().lower() not in DEVELOPMENT_APP_ENVS


def _has_valid_hash_format(encoded_hash: str) -> bool:
    """パスワードを伴わずに APP_PASSWORD_HASH の形式だけを検証する。"""
    try:
        scheme, iterations_raw, salt_b64, digest_b64 = encoded_hash.split("$")
        if scheme != _HASH_SCHEME or int(iterations_raw) <= 0:
            return False
        return bool(base64.b64decode(salt_b64)) and bool(base64.b64decode(digest_b64))
    except (ValueError, TypeError, base64.binascii.Error):
        return False


def _configured_worker_count() -> int:
    """起動予定のワーカー数を環境変数から推定する (不明なら 1)。"""
    for name in ("WEB_CONCURRENCY", "UVICORN_WORKERS", "GUNICORN_WORKERS"):
        raw = os.getenv(name, "").strip()
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                logger.warning(f"{name} を整数として解釈できないため 1 ワーカーとみなします")
    return 1


def _load_public_prefixes() -> Tuple[str, ...]:
    configured = os.getenv("AUTH_PUBLIC_PATH_PREFIXES", DEFAULT_PUBLIC_PREFIXES)
    prefixes = [prefix.strip() for prefix in configured.split(",") if prefix.strip()]
    for mandatory in MANDATORY_PUBLIC_PREFIXES:
        if mandatory not in prefixes:
            prefixes.append(mandatory)
    return tuple(prefixes)


def _resolve_cookie_secure(is_production: bool) -> bool:
    """本番では常に Secure。開発のみ環境変数で無効化できる (PRIDEV-521)。"""
    raw = os.getenv("AUTH_COOKIE_SECURE", "").strip().lower()
    if is_production:
        if raw in ("0", "false", "no"):
            logger.warning(
                "本番環境では AUTH_COOKIE_SECURE=false を無視し、Secure Cookie を強制します"
            )
        return True
    # ローカル開発 (http) では Secure Cookie がブラウザへ保存されないため既定を落とす。
    return raw in ("1", "true", "yes")


def _validate_production_settings(password_hash: str, secret_key: str) -> None:
    """本番で設定が不足・不正なら起動を失敗させる (PRIDEV-521 / PRIDEV-522)。"""
    if not password_hash:
        raise AuthConfigurationError(
            "APP_PASSWORD_HASH が未設定です。本番環境では必須です "
            "(生成手順: python scripts/hash_password.py / Docs/AUTH_SETUP.md)"
        )
    if not _has_valid_hash_format(password_hash):
        # ハッシュ値そのものはメッセージへ含めない
        raise AuthConfigurationError(
            "APP_PASSWORD_HASH の形式が不正です (期待形式: pbkdf2_sha256$<iterations>$<salt>$<hash>)"
        )
    if not secret_key:
        raise AuthConfigurationError(
            "AUTH_SECRET_KEY が未設定です。本番環境では必須です "
            '(生成手順: python -c "import secrets; print(secrets.token_urlsafe(32))")'
        )
    if len(secret_key) < MIN_SECRET_KEY_LENGTH:
        raise AuthConfigurationError(
            f"AUTH_SECRET_KEY が短すぎます ({MIN_SECRET_KEY_LENGTH} 文字以上が必要です)"
        )
    workers = _configured_worker_count()
    if workers > 1:
        # ログイン試行制限をプロセス内で保持しているため複数ワーカーでは上限を迂回できる。
        raise AuthConfigurationError(
            f"ワーカー数 {workers} は未対応です。ログイン試行制限がプロセス内保持のため "
            "単一ワーカーで運用してください (Docs/AUTH_SETUP.md)"
        )


def get_auth_settings() -> AuthSettings:
    """環境変数から AuthSettings を構築する (プロセス内でキャッシュ)。

    本番環境 (APP_ENV が DEVELOPMENT_APP_ENVS 以外) で設定が不足・不正な場合は
    AuthConfigurationError を送出し、認証なしで起動しないようにする。
    """
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache

    is_production = is_production_environment()
    # 平文 APP_PASSWORD は受け付けない (PRIDEV-523)。
    password_hash = os.getenv("APP_PASSWORD_HASH", "").strip()
    secret_key = os.getenv("AUTH_SECRET_KEY", "").strip()

    if is_production:
        _validate_production_settings(password_hash, secret_key)
    else:
        if not password_hash:
            logger.warning(
                f"APP_ENV={os.getenv('APP_ENV', '')!r} かつ APP_PASSWORD_HASH 未設定のため "
                "認証は無効です。開発環境でのみ許可されます"
            )
        elif not secret_key:
            # 開発環境のみ。再起動でセッションが無効化される点を明示する。
            secret_key = secrets.token_urlsafe(32)
            logger.warning(
                "AUTH_SECRET_KEY が未設定のため一時キーを生成しました。"
                "再起動でログイン状態が失われます"
            )
    if not secret_key:
        secret_key = secrets.token_urlsafe(32)

    _settings_cache = AuthSettings(
        password_hash=password_hash,
        secret_key=secret_key,
        session_max_age_seconds=_env_int(
            "AUTH_SESSION_MAX_AGE_SECONDS", DEFAULT_SESSION_MAX_AGE_SECONDS
        ),
        max_login_attempts=_env_int("AUTH_MAX_LOGIN_ATTEMPTS", DEFAULT_MAX_LOGIN_ATTEMPTS),
        lockout_seconds=_env_int("AUTH_LOCKOUT_SECONDS", DEFAULT_LOCKOUT_SECONDS),
        public_prefixes=_load_public_prefixes(),
        cookie_secure=_resolve_cookie_secure(is_production),
        is_production=is_production,
        trusted_proxy_count=max(0, _env_int("AUTH_TRUSTED_PROXY_COUNT", 0)),
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
# 対応するデプロイ構成: 単一ワーカー / 単一インスタンス (PRIDEV-522)。
# 失敗回数はプロセス内で保持するため、複数ワーカーでは上限を迂回できる。
# そのため本番では _validate_production_settings() がワーカー数 > 1 を拒否する。
# 分散構成へ移行する場合は Redis 等の共有ストアへ差し替えること。
_login_attempts: Dict[str, Tuple[int, float]] = {}

# 無制限に増加させないための追跡クライアント数の上限。
MAX_TRACKED_CLIENTS = 1024


def _client_key(request: Request, settings: AuthSettings) -> str:
    """レート制限のキーとなるクライアント識別子を返す。

    転送ヘッダーは無条件に信用しない。AUTH_TRUSTED_PROXY_COUNT=N (N>=1) のときだけ
    X-Forwarded-For を解釈し、右から N 番目 (= 最も内側の信頼済みプロキシが実際に
    記録した接続元) を採用する。末尾 N-1 個は信頼済みプロキシ自身のアドレス、
    それより左はクライアントが自称した値なので信用しない。
    """
    if settings.trusted_proxy_count > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            index = max(0, len(hops) - settings.trusted_proxy_count)
            return hops[index]
    return request.client.host if request.client else "unknown"


def _purge_expired_attempts(settings: AuthSettings, now: float) -> None:
    """ロックアウト期間を過ぎたエントリを全体清掃し、上限を超えたら古い順に捨てる。"""
    for key, (_, last_failure_at) in list(_login_attempts.items()):
        if now - last_failure_at >= settings.lockout_seconds:
            _login_attempts.pop(key, None)
    overflow = len(_login_attempts) - MAX_TRACKED_CLIENTS
    if overflow > 0:
        for key, _ in sorted(_login_attempts.items(), key=lambda item: item[1][1])[:overflow]:
            _login_attempts.pop(key, None)


def _is_locked_out(key: str, settings: AuthSettings, now: float) -> bool:
    _purge_expired_attempts(settings, now)
    failures, _ = _login_attempts.get(key, (0, 0.0))
    return failures >= settings.max_login_attempts


def _record_failure(key: str, settings: AuthSettings, now: float) -> None:
    failures, _ = _login_attempts.get(key, (0, 0.0))
    _login_attempts[key] = (failures + 1, now)
    _purge_expired_attempts(settings, now)


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


def is_public_path(path: str, settings: Optional[AuthSettings] = None) -> bool:
    """公開パス (認証不要) かどうかを返す。前方一致はパス境界単位で判定する。"""
    settings = settings or get_auth_settings()
    for prefix in settings.public_prefixes:
        normalized = prefix.rstrip("/")
        if not normalized:
            # "/" だけの指定は全公開を意味してしまうため無視する。
            continue
        if path == normalized or path.startswith(normalized + "/"):
            return True
    return False


def is_protected_path(path: str, settings: Optional[AuthSettings] = None) -> bool:
    """公開パス以外はすべて保護対象とする (PRIDEV-518)。"""
    return not is_public_path(path, settings)


# --- ルーティング -------------------------------------------------------------
router = APIRouter(tags=["auth"])

# ログイン画面は Jinja2 テンプレート (自動エスケープ有効) で描画する。
# 文字列連結 / str.format による HTML 生成は反射型 XSS になるため禁止 (PRIDEV-519)。
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(("html", "xml")),
)


def _render_login_page(next_path: str = "/", error: str = "") -> str:
    return _jinja_env.get_template("login.html").render(
        login_path=LOGIN_PATH,
        next_path=next_path,
        error=error,
    )


def _safe_next_path(candidate: str) -> str:
    """ログイン後の遷移先として安全な同一オリジンの相対 URL のみ許可する。

    ここで行うのはリダイレクト先としての検証のみ。HTML 属性値としての
    エスケープはテンプレート側の自動エスケープが担当する (PRIDEV-519)。
    クエリは保持する (PRIDEV-520)。
    """
    if not candidate:
        return "/"
    # ヘッダーインジェクションと、ブラウザが scheme-relative と解釈する "\\" を弾く。
    if any(char in candidate for char in ("\r", "\n", "\\", "\x00")):
        return "/"
    parts = urlsplit(candidate)
    if parts.scheme or parts.netloc:
        return "/"
    if not parts.path.startswith("/") or parts.path.startswith("//"):
        return "/"
    # fragment はサーバーへ送られないため落とす。
    return urlunsplit(("", "", parts.path, parts.query, ""))


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
    key = _client_key(request, settings)

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
        _record_failure(key, settings, now)
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
