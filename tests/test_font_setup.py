"""matplotlib 日本語フォント設定の回帰テスト (PRIDEV-482)

日本語チャートの文字化けは matplotlib が
「Glyph ... missing from font(s) ...」という UserWarning を出すことで検知できる。
本テストはその警告が出ないことを回帰テストとして固定する。
"""

import io
import sys
import warnings
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.visualization import font_setup  # noqa: E402

JAPANESE_TITLE = "日本語タイトル：売買タイミング分析"
JAPANESE_XLABEL = "日付"
JAPANESE_YLABEL = "価格 (円)"
JAPANESE_LEGEND = "移動平均線"


@pytest.fixture(autouse=True)
def reset_font_cache():
    """環境変数を差し替えるテストが互いに干渉しないようにする。"""
    original_family = matplotlib.rcParams["font.family"]
    font_setup._cached_result = None
    yield
    font_setup._cached_result = None
    matplotlib.rcParams["font.family"] = original_family


def _render_japanese_chart():
    """日本語を含む図を描画し、発生した警告メッセージを返す。"""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig, ax = plt.subplots()
        try:
            ax.plot([1, 2, 3], [-1.5, 0.5, 2.5], label=JAPANESE_LEGEND)
            ax.set_title(JAPANESE_TITLE)
            ax.set_xlabel(JAPANESE_XLABEL)
            ax.set_ylabel(JAPANESE_YLABEL)
            ax.legend()
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png")
        finally:
            plt.close(fig)
    return [str(item.message) for item in caught]


# --- 本題: 日本語が文字化けしないこと -----------------------------------------
def test_japanese_chart_has_no_missing_glyph_warning():
    result = font_setup.setup_japanese_font(force=True)
    assert result.japanese_supported, f"日本語フォントが見つかりません: {result.candidates}"

    missing = [message for message in _render_japanese_chart() if "missing from font" in message]

    assert missing == [], f"日本語が文字化けしています: {missing[:3]}"


def test_missing_glyph_detection_actually_works():
    """検知ロジック自体が機能していること (フォントを外すと警告が出る)。"""
    matplotlib.rcParams["font.family"] = "DejaVu Sans"

    missing = [message for message in _render_japanese_chart() if "missing from font" in message]

    assert missing, "日本語非対応フォントでも警告が出ないなら、この回帰テストは無意味"


def test_minus_sign_is_not_garbled():
    font_setup.setup_japanese_font(force=True)

    assert matplotlib.rcParams["axes.unicode_minus"] is False


# --- フォント解決 -------------------------------------------------------------
def test_bundled_font_is_used_by_default(monkeypatch):
    monkeypatch.delenv("MATPLOTLIB_FONT_FAMILY", raising=False)

    result = font_setup.setup_japanese_font(force=True)

    assert result.japanese_supported is True
    assert result.family in font_setup.japanese_font_candidates()


def test_font_family_env_takes_precedence(monkeypatch):
    monkeypatch.setenv("MATPLOTLIB_FONT_FAMILY", "My Custom Gothic")

    candidates = font_setup.japanese_font_candidates()

    assert candidates[0] == "My Custom Gothic"
    assert font_setup.BUNDLED_FONT in candidates, "指定フォントが無い場合の同梱フォントへのフォールバックを残すこと"


def test_resolve_returns_none_when_no_candidate_installed():
    assert font_setup.resolve_japanese_font(("No Such Font A", "No Such Font B")) is None


# --- フォント不足時の挙動 -----------------------------------------------------
def test_missing_font_is_reported_but_does_not_crash(monkeypatch, caplog):
    monkeypatch.setattr(font_setup, "resolve_japanese_font", lambda candidates=None: None)
    monkeypatch.delenv("MATPLOTLIB_FONT_STRICT", raising=False)

    with caplog.at_level("ERROR", logger=font_setup.logger.name):
        result = font_setup.setup_japanese_font(force=True)

    assert result.japanese_supported is False
    assert "文字化け" in caplog.text


def test_missing_font_raises_in_strict_mode(monkeypatch):
    monkeypatch.setattr(font_setup, "resolve_japanese_font", lambda candidates=None: None)
    monkeypatch.setenv("MATPLOTLIB_FONT_STRICT", "true")

    with pytest.raises(font_setup.JapaneseFontUnavailableError):
        font_setup.setup_japanese_font(force=True)


# --- 重複実装の防止 -----------------------------------------------------------
CHART_MODULES = (
    "python/visualization/stock_chart_visualizer.py",
    "python/visualization/plot_indicators.py",
)


@pytest.mark.parametrize("module_path", CHART_MODULES)
def test_chart_modules_delegate_font_setup(module_path):
    """各描画モジュールがフォント設定を自前で持たず共通関数へ委譲していること。"""
    source = (Path(__file__).resolve().parent.parent / module_path).read_text(encoding="utf-8")

    assert "setup_japanese_font()" in source, f"{module_path} が共通のフォント設定を呼んでいない"
    assert 'rcParams["font.family"]' not in source, f"{module_path} がフォント設定を重複実装している"
    assert "font.family" not in source.replace('rcParams["font.family"]', ""), (
        f"{module_path} がフォント設定を重複実装している"
    )
