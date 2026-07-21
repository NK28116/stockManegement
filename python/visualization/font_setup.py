"""
matplotlib 日本語フォント共通設定

チャート生成モジュールは図を描画する前に setup_japanese_font() を呼び出すこと
（フォント設定は描画時に参照されるため、pyplot import との順序は問わない）。
本番コンテナ (python:3.12-slim) には OS レベルの日本語フォントが存在しないため、
japanize_matplotlib が wheel に同梱する IPAexGothic を登録して日本語描画に対応
する。japanize_matplotlib が未インストールの場合は警告を出して OS 標準フォント
にフォールバックするベストエフォート動作となる。
"""

import logging
import platform

import matplotlib
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

__all__ = ["setup_japanese_font"]


def setup_japanese_font() -> None:
    """日本語フォントを OS 非依存で設定する。

    IPAexGothic (japanize_matplotlib 同梱) をベースラインとし、
    macOS / Windows ではよりネイティブなフォントがあれば優先する。
    """
    try:
        import japanize_matplotlib  # noqa: F401  (import 時に IPAexGothic を登録)
    except ImportError:
        logger.warning(
            "japanize_matplotlib が見つかりません。"
            "Linux 環境では日本語が文字化けする可能性があります。"
        )

    system = platform.system()
    if system == "Darwin":
        installed = {f.name for f in fm.fontManager.ttflist}
        for candidate in ("Hiragino Sans", "Hiragino Kaku Gothic ProN"):
            if candidate in installed:
                matplotlib.rcParams["font.family"] = candidate
                break
    elif system == "Windows":
        matplotlib.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "MS Gothic"]

    # マイナス記号の文字化け対策
    matplotlib.rcParams["axes.unicode_minus"] = False
