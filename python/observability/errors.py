# python/observability/errors.py
"""GCP SDK の例外を上位層へ漏らさないための内部エラー型 (PRIDEV-490)"""

from __future__ import annotations

__all__ = [
    "ObservabilityError",
    "ObservabilityPermissionError",
    "ObservabilityUnavailableError",
    "normalize_exception",
]


class ObservabilityError(Exception):
    """Logging / Monitoring 読み取りの失敗を表す基底エラー。"""


class ObservabilityPermissionError(ObservabilityError):
    """権限不足 (IAM ロール不足など)。"""


class ObservabilityUnavailableError(ObservabilityError):
    """API 到達不能・一時障害・設定不足。"""


# google.api_core の例外名。SDK 未導入環境でも import できるよう名前で判定する。
_PERMISSION_EXCEPTION_NAMES = frozenset(
    {"PermissionDenied", "Forbidden", "Unauthenticated", "Unauthorized"}
)


def normalize_exception(exc: Exception, context: str) -> ObservabilityError:
    """GCP SDK 例外を内部エラー型へ正規化する。

    元例外のメッセージには対象リソース名などが含まれうるため、
    上位層へは種別と context のみを伝え、詳細は原因例外として保持する。
    """
    name = type(exc).__name__
    if name in _PERMISSION_EXCEPTION_NAMES or getattr(exc, "code", None) in (401, 403):
        error: ObservabilityError = ObservabilityPermissionError(f"{context}: 権限が不足しています")
    else:
        error = ObservabilityUnavailableError(f"{context}: 取得できませんでした ({name})")
    error.__cause__ = exc
    return error
