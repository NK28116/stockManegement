# python/observability/masking.py
"""ログ本文の秘匿処理 (PRIDEV-491)

System Monitor は直近のログを画面へ表示するため、ログ本文へ紛れ込んだ
秘密値をそのまま露出させない。クエリ文字列・Authorization ヘッダ・Cookie・
トークン・パスワード・API キーをマスクする。

方針:
    * 「マスクし損ねるより、マスクしすぎる」側へ倒す
    * 判定は値の形ではなくキー名で行い、未知の値でも取りこぼさない
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable

__all__ = ["MASK", "SENSITIVE_KEY_PATTERN", "mask_mapping", "mask_text"]

MASK = "***"

# 秘匿対象とみなすキー名 (大文字小文字を区別しない)
_SENSITIVE_KEY_WORDS = (
    "authorization",
    "api[_-]?key",
    "access[_-]?key",
    "secret",
    "password",
    "passwd",
    "pwd",
    "token",
    "credential",
    "cookie",
    "session",
    "signature",
    "private[_-]?key",
    "auth",
)
SENSITIVE_KEY_PATTERN = re.compile("|".join(_SENSITIVE_KEY_WORDS), re.IGNORECASE)

# key=value / key: value / "key": "value" 形式 (JSON のようにキーが引用符付きでもよい)
_KEY_VALUE_PATTERN = re.compile(
    r"(?P<kq>[\"']?)"
    r"(?P<key>[A-Za-z_][\w\-]*)"
    r"(?P=kq)"
    r"(?P<sep>\s*[=:]\s*)"
    r"(?P<quote>[\"']?)"
    r"(?P<value>[^\s\"',;&}]+)"
    r"(?P=quote)"
)

# HTTP ヘッダ形式 (Authorization: Bearer xxx / Cookie: a=b; c=d)
_HEADER_PATTERN = re.compile(
    r"(?P<name>Authorization|Cookie|Set-Cookie|Proxy-Authorization)\s*:\s*(?P<value>[^\r\n]+)",
    re.IGNORECASE,
)

# URL のクエリ文字列全体
_QUERY_STRING_PATTERN = re.compile(r"(?P<url>https?://[^\s?]+)\?(?P<query>[^\s\"']*)")


def _is_sensitive(key: str) -> bool:
    return bool(SENSITIVE_KEY_PATTERN.search(key))


def _mask_query(match: "re.Match[str]") -> str:
    """クエリ文字列は値を保持する必要が無いため丸ごとマスクする。"""
    return f"{match.group('url')}?{MASK}"


def _mask_header(match: "re.Match[str]") -> str:
    return f"{match.group('name')}: {MASK}"


def _mask_key_value(match: "re.Match[str]") -> str:
    if not _is_sensitive(match.group("key")):
        return match.group(0)
    quote = match.group("quote")
    key_quote = match.group("kq")
    return (
        f"{key_quote}{match.group('key')}{key_quote}"
        f"{match.group('sep')}{quote}{MASK}{quote}"
    )


def mask_text(text: Any) -> str:
    """ログ本文から秘密値を取り除いた文字列を返す。"""
    if text is None:
        return ""
    masked = str(text)
    masked = _QUERY_STRING_PATTERN.sub(_mask_query, masked)
    masked = _HEADER_PATTERN.sub(_mask_header, masked)
    masked = _KEY_VALUE_PATTERN.sub(_mask_key_value, masked)
    return masked


def mask_mapping(mapping: Dict[str, Any], *, extra_keys: Iterable[str] = ()) -> Dict[str, str]:
    """ラベル等のマッピングから秘密値を取り除く。"""
    extra = {key.lower() for key in extra_keys}
    masked: Dict[str, str] = {}
    for key, value in (mapping or {}).items():
        if _is_sensitive(str(key)) or str(key).lower() in extra:
            masked[str(key)] = MASK
        else:
            masked[str(key)] = mask_text(value)
    return masked
