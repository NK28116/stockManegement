"""matplotlib 日本語フォント共通設定 (PRIDEV-482)

チャート生成モジュールは図を描画する前に :func:`setup_japanese_font` を呼び出すこと
（フォント設定は描画時に参照されるため、pyplot import との順序は問わない）。

フォントの決定順序:
    1. 環境変数 ``MATPLOTLIB_FONT_FAMILY`` で明示指定されたフォント
    2. ``japanize_matplotlib`` が同梱する ``IPAexGothic``
    3. OS 標準の日本語フォント (macOS: Hiragino / Windows: Meiryo / Linux: Noto, IPA 等)

いずれも見つからない場合の挙動:
    * 既定 (``MATPLOTLIB_FONT_STRICT`` 未設定): matplotlib の既定フォントのまま続行し、
      ``japanese_supported=False`` を返して ERROR ログを出す（描画は文字化けする）。
    * ``MATPLOTLIB_FONT_STRICT=true``: :class:`JapaneseFontUnavailableError` を送出する。
      文字化けした画像を配信したくない本番環境向け。
"""

from __future__ import annotations

import logging
import os
import platform
from dataclasses import dataclass
from typing import Optional, Tuple

import matplotlib
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

__all__ = [
    "FontSetupResult",
    "JapaneseFontUnavailableError",
    "japanese_font_candidates",
    "resolve_japanese_font",
    "setup_japanese_font",
]


class JapaneseFontUnavailableError(RuntimeError):
    """日本語フォントが 1 つも利用できない場合に送出される (strict モード時のみ)。"""


@dataclass(frozen=True)
class FontSetupResult:
    """フォント設定の結果。呼び出し側が文字化けの有無を判定できるようにする。"""

    family: str
    japanese_supported: bool
    candidates: Tuple[str, ...]


# japanize_matplotlib 同梱フォント。OS 非依存のベースラインとして最優先で使う。
BUNDLED_FONT = "IPAexGothic"

# OS 標準の日本語フォント候補 (存在すればより自然な字形になる)
_OS_FONT_CANDIDATES = {
    "Darwin": ("Hiragino Sans", "Hiragino Kaku Gothic ProN", "Hiragino Maru Gothic Pro"),
    "Windows": ("Meiryo", "Yu Gothic", "MS Gothic"),
    "Linux": ("Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "IPAGothic", "TakaoGothic", "VL Gothic"),
}

_cached_result: Optional[FontSetupResult] = None


def _import_bundled_font() -> None:
    """japanize_matplotlib を import して IPAexGothic を font_manager へ登録する。"""
    try:
        import japanize_matplotlib  # noqa: F401
    except ImportError:
        logger.warning(
            "japanize_matplotlib が見つかりません。"
            "OS 標準の日本語フォントが無い環境では文字化けします "
            "(pip install japanize-matplotlib)"
        )


def japanese_font_candidates() -> Tuple[str, ...]:
    """優先順位順の日本語フォント候補を返す。"""
    candidates = []
    preferred = os.getenv("MATPLOTLIB_FONT_FAMILY", "").strip()
    if preferred:
        candidates.append(preferred)
    candidates.append(BUNDLED_FONT)
    candidates.extend(_OS_FONT_CANDIDATES.get(platform.system(), ()))
    # 重複を除きつつ順序を保つ
    return tuple(dict.fromkeys(candidates))


def resolve_japanese_font(candidates: Optional[Tuple[str, ...]] = None) -> Optional[str]:
    """インストール済みフォントから最初に利用できる候補を返す。無ければ None。"""
    candidates = candidates if candidates is not None else japanese_font_candidates()
    installed = {font.name for font in fm.fontManager.ttflist}
    for candidate in candidates:
        if candidate in installed:
            return candidate
    return None


def _strict_mode() -> bool:
    return os.getenv("MATPLOTLIB_FONT_STRICT", "").strip().lower() in ("1", "true", "yes")


def setup_japanese_font(*, force: bool = False) -> FontSetupResult:
    """日本語フォントを OS 非依存で設定する。

    Args:
        force: 既に設定済みでも再解決する (環境変数を差し替えるテスト用)。

    Returns:
        FontSetupResult: 選択されたフォントと、日本語が描画可能かどうか。

    Raises:
        JapaneseFontUnavailableError: strict モードで日本語フォントが見つからない場合。
    """
    global _cached_result
    if _cached_result is not None and not force:
        return _cached_result

    _import_bundled_font()
    candidates = japanese_font_candidates()
    resolved = resolve_japanese_font(candidates)

    if resolved is None:
        message = (
            "日本語フォントが見つかりませんでした。チャートの日本語は文字化けします。"
            f"候補={candidates}. japanize-matplotlib の導入、または "
            "MATPLOTLIB_FONT_FAMILY で利用可能なフォント名を指定してください"
        )
        logger.error(message)
        if _strict_mode():
            raise JapaneseFontUnavailableError(message)
        result = FontSetupResult(
            family=str(matplotlib.rcParams["font.family"]),
            japanese_supported=False,
            candidates=candidates,
        )
    else:
        matplotlib.rcParams["font.family"] = resolved
        logger.info(f"matplotlib の日本語フォントを設定しました: {resolved}")
        result = FontSetupResult(family=resolved, japanese_supported=True, candidates=candidates)

    # マイナス記号の文字化け対策 (フォント有無に関わらず適用)
    matplotlib.rcParams["axes.unicode_minus"] = False

    _cached_result = result
    return result
