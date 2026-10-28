"""ドロップダウン配置と小画面 overflow の回帰テスト (PRIDEV-484)

CI にブラウザが無く、テンプレートが Tailwind / Vue を CDN から読み込む構成のため、
実ブラウザでの実測は行わず、レイアウト崩れを引き起こす「クラス構成の退行」を
静的に検出する。代表的な viewport 幅ごとに、その幅で必要になる指定が
テンプレートへ残っていることを固定する。

実ブラウザでの検証は System Monitor の E2E 基盤 (PRIDEV-494) で扱う。
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "python" / "web" / "templates" / "index.html"

# 代表的な viewport 幅と、その幅で効くべき Tailwind ブレークポイント
# (Tailwind 既定: sm=640px, lg=1024px)
VIEWPORTS = {
    "mobile-small": 320,
    "mobile": 375,
    "tablet": 768,
    "laptop": 1024,
    "desktop": 1440,
}

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "param", "source", "track", "wbr",
}


@pytest.fixture(scope="module")
def template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


# --- 構造の健全性 -------------------------------------------------------------
class _TagBalanceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID_ELEMENTS:
            return
        if not self.stack:
            self.errors.append(f"対応する開始タグの無い </{tag}> at {self.getpos()}")
            return
        opened, position = self.stack.pop()
        if opened != tag:
            self.errors.append(f"<{opened}> ({position}) が </{tag}> ({self.getpos()}) で閉じられている")


def test_template_tags_are_balanced(template):
    """レイアウト修正でタグの入れ子が壊れていないこと。"""
    parser = _TagBalanceParser()
    parser.feed(template)

    assert parser.errors == [], parser.errors
    assert [tag for tag, _ in parser.stack] == [], "閉じられていないタグがある"


# --- 通常幅で不要な横スクロールを起こさない ------------------------------------
def test_page_body_does_not_scroll_horizontally(template):
    """ページ本体は横スクロールさせない (必要箇所だけ .table-scroll で許可する)。"""
    assert re.search(r"html,\s*body\s*\{[^}]*overflow-x:\s*hidden", template), (
        "body の横スクロール抑止が失われている"
    )
    assert re.search(r"html,\s*body\s*\{[^}]*max-width:\s*100%", template)


def test_horizontal_scroll_is_allowed_only_in_designated_containers(template):
    """横スクロールは .table-scroll でのみ許可する。"""
    assert re.search(r"\.table-scroll\s*\{[^}]*overflow-x:\s*auto", template)

    # パネル全体に overflow-x-auto を付けると、フォームまで横スクロールしてしまう
    assert "rounded-lg shadow overflow-x-auto" not in template, (
        "パネル全体ではなくテーブルだけを横スクロール対象にすること"
    )


def test_every_table_is_inside_a_scroll_container(template):
    """列数の多い表が画面をはみ出さないよう、すべての table をスクロール枠で包む。"""
    tables = [match.start() for match in re.finditer(r"<table[\s>]", template)]
    assert tables, "テンプレートから table が消えている"

    for position in tables:
        preceding = template[:position]
        wrapper = preceding.rfind("table-scroll")
        opening_div = preceding.rfind("<div")
        assert wrapper != -1 and wrapper > opening_div, (
            f"{template[position:position + 60]!r} が .table-scroll で包まれていない"
        )


# --- 小画面で主要コンテンツが切れない ------------------------------------------
@pytest.mark.parametrize("name,width", sorted(VIEWPORTS.items(), key=lambda item: item[1]))
def test_header_navigation_wraps_on_narrow_viewports(template, name, width):
    """ヘッダーのタブ/操作ボタン群が折り返す (横一列固定だと狭い幅ではみ出す)。"""
    header = re.search(r"<header[^>]*>.*?</header>", template, re.DOTALL)
    assert header, "header が見つからない"
    header_html = header.group(0)

    assert "flex-wrap" in header_html, f"{name}({width}px) でヘッダーが折り返せない"
    assert "space-x-4" not in header_html, (
        "space-x-* は折り返し時に余白が崩れるため gap-* を使うこと"
    )
    if width < 1024:
        # lg 未満では縦積みになる
        assert "flex-col" in header_html


def test_purchase_form_wraps_and_aligns_controls(template):
    """購入フォームが折り返し、入力と select の基準位置が揃っていること。"""
    form = re.search(r"株式の購入.*?</div>\s*</div>", template, re.DOTALL)
    assert form, "購入フォームが見つからない"
    form_html = form.group(0)

    assert "flex flex-wrap items-end" in form_html, "小画面で折り返せない"
    # input / select / button すべてが共通クラスで同じ高さ・幅になる
    assert form_html.count("form-control") == 5, "入力部品の基準位置が揃っていない"
    assert form_html.count("form-field") == 4
    assert "w-full sm:w-auto" in form_html, "狭い幅では 1 列、通常幅では横並びにすること"


def test_form_control_has_shared_metrics(template):
    """.form-control が高さ・幅の基準を一元管理していること (select だけずれる問題の再発防止)。"""
    rule = re.search(r"\.form-control\s*\{([^}]*)\}", template)
    assert rule, ".form-control が定義されていない"
    body = rule.group(1)

    for prop in ("box-sizing", "height", "max-width", "width"):
        assert prop in body, f".form-control に {prop} が無い"


def test_flex_children_can_shrink(template):
    """flex 子要素の min-width 既定値による横はみ出しを防いでいること。"""
    assert re.search(r"\.form-field\s*\{[^}]*min-width:\s*0", template)


def test_modal_keeps_margin_and_scrolls_inside_on_small_screens(template):
    """モーダルが小画面で画面端に張り付かず、内部でスクロールすること。"""
    modal = re.search(r'v-if="showDiffModal".*?<h3', template, re.DOTALL)
    assert modal, "差分モーダルが見つからない"
    modal_html = modal.group(0)

    assert "p-4" in modal_html, "画面端との余白が無い"
    assert "max-h-[90vh]" in modal_html and "overflow-y-auto" in modal_html


def test_fixed_width_panels_do_not_exceed_small_viewports(template):
    """固定幅指定が狭い viewport を超えないこと。"""
    fixed_widths = re.findall(r"\bw-\[(\d+)px\]", template)
    smallest_viewport = min(VIEWPORTS.values())

    too_wide = [value for value in fixed_widths if int(value) > smallest_viewport]
    assert too_wide == [], f"{smallest_viewport}px を超える固定幅がある: {too_wide}"


def test_max_width_panels_are_allowed_to_shrink(template):
    """max-w-* パネルが狭い幅でも縮めること。"""
    for panel in ("simulation", "settings"):
        match = re.search(rf"currentTab === '{panel}'\" class=\"([^\"]*)\"", template)
        assert match, f"{panel} タブのパネルが見つからない"
        assert "w-full" in match.group(1), f"{panel} パネルが縮まない"
