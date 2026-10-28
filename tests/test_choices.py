"""プルダウン選択肢の回帰テスト (PRIDEV-486)

選択肢の欠落を検知することが目的。UI へのハードコードを禁止し、
ステータスは `python/trading/stock_status.py`、目的は
`python/web/constants.py` を単一の正として固定する。
"""

import csv
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.trading import stock_status  # noqa: E402
from python.web import constants  # noqa: E402

TEMPLATE_PATH = ROOT / "python" / "web" / "templates" / "index.html"
CSV_PATHS = (ROOT / "data" / "my_stock.csv", ROOT / "data" / "my_stock_local.csv")

# ユーザー確認済みの purpose (シート No.4 の回答)
CONFIRMED_PURPOSES = {
    "long": "長期（バリュー投資）",
    "middle": "中期",
    "present": "優待目的",
    "swing": "スイングトレード",
}


@pytest.fixture(scope="module")
def client():
    # lifespan (DB 初期化) は不要なため TestClient をそのまま使う
    from python.web.app import app

    return TestClient(app)


@pytest.fixture(scope="module")
def template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _persisted_values(column: str):
    values = set()
    for path in CSV_PATHS:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                value = (row.get(column) or "").strip()
                if value:
                    values.add(value)
    return values


# --- API が単一の正を配信していること -----------------------------------------
def test_status_choices_come_from_the_single_source(client):
    payload = client.get("/api/choices").json()

    assert [choice["key"] for choice in payload["status"]] == stock_status.status_keys()
    assert [choice["label"] for choice in payload["status"]] == [
        choice.label for choice in stock_status.STATUS_CHOICES
    ]


def test_purpose_choices_match_the_confirmed_specification(client):
    payload = client.get("/api/choices").json()

    assert {choice["key"]: choice["label"] for choice in payload["purpose"]} == CONFIRMED_PURPOSES


def test_status_payload_carries_the_held_flag(client):
    payload = client.get("/api/choices").json()

    held = {choice["key"] for choice in payload["status"] if choice["held"]}
    assert held == set(stock_status.held_status_values())


def test_no_duplicate_or_empty_choices():
    for choices in (constants.PURPOSE_CHOICES,):
        keys = [choice["key"] for choice in choices]
        assert len(keys) == len(set(keys)), "選択肢のキーが重複している"
        for choice in choices:
            assert choice["key"].strip() and choice["label"].strip()


# --- 永続データを網羅していること ---------------------------------------------
def test_every_persisted_status_is_selectable():
    """永続データに存在する status がすべて選択肢に含まれること (欠落の検知)。"""
    selectable = set(stock_status.status_keys())

    missing = {
        value for value in _persisted_values("status") if stock_status.normalize(value) is None
    } | (_persisted_values("status") - selectable - {"売却（利益確定）", "売却（損切り）"})

    assert missing == set(), f"UI から選べない status が永続データに存在する: {sorted(missing)}"


def test_every_persisted_purpose_is_selectable():
    missing = _persisted_values("purpose") - set(constants.purpose_keys())

    assert missing == set(), f"UI から選べない purpose が永続データに存在する: {sorted(missing)}"


def test_excluded_status_is_now_selectable():
    """調査で判明していた「除外」が選択肢へ入っていること。"""
    assert stock_status.StockStatus.EXCLUDED in stock_status.status_keys()
    assert stock_status.status_label(stock_status.StockStatus.EXCLUDED) == "除外"


# --- UI がハードコードしていないこと ------------------------------------------
def test_template_does_not_enumerate_choices(template):
    """選択肢の列挙 (狭い範囲に 3 つ以上) がテンプレートへ残っていないこと。"""
    values = [choice.label for choice in stock_status.STATUS_CHOICES]
    positions = sorted(
        (match.start(), value)
        for value in values
        for match in re.finditer(re.escape(value), template)
    )

    window = 400
    for index, (start, _) in enumerate(positions):
        nearby = {value for position, value in positions[index:] if position - start < window}
        assert len(nearby) < 3, (
            f"選択肢が {template[start:start + 120]!r} 付近へ列挙されている。"
            "選択肢は /api/choices から取得すること"
        )

    for key in stock_status.status_keys():
        assert key not in template, f"選択肢キー {key} がテンプレートへハードコードされている"
    assert "/api/choices" in template


def test_purpose_dropdown_uses_purpose_choices(template):
    """「目的別」select が status ではなく purpose の選択肢を使っていること。"""
    option = re.search(r'<option v-for="choice in purposeChoices"[^>]*>', template)

    assert option, "purpose の選択肢が API 由来になっていない"
    assert ':value="choice.key"' in option.group(0)
    assert 'v-model="purpose"' in template


def test_labels_and_badges_are_data_driven(template):
    """表示名・表示クラスの分岐が選択肢の二重管理になっていないこと。"""
    for function in ("getStatusClass(status)", "getPurposeClass(purpose)"):
        body = re.search(
            re.escape(function) + r" \{(.*?)\n                \},", template, re.DOTALL
        )
        assert body, f"{function} が見つからない"
        assert "matched" in body.group(1)
        for choice in stock_status.STATUS_CHOICES:
            assert choice.label not in body.group(1)
            assert choice.badge_class not in body.group(1)


def test_held_judgement_is_not_reimplemented_in_the_template(template):
    """保有判定がテンプレート側で作り直されていないこと。"""
    assert "isHeld(item.status)" in template
    assert "item.status !== '保有中'" not in template


def test_sort_order_is_derived_from_choices(template):
    assert "const statusOrder = this.statusOrder" in template
    assert template.count("statusOrder[a.status]") == 1


# --- バックエンドが単一の正を使っていること -----------------------------------
def test_signals_query_uses_the_single_source():
    source = (ROOT / "python" / "web" / "api" / "signals.py").read_text(encoding="utf-8")

    assert "stock_status.held_status_values()" in source
    assert "'SOLD_PROFIT', 'SOLD_LOSS'" not in source, "保有判定が SQL へ直書きされている"


def test_trading_module_writes_canonical_values():
    source = (ROOT / "python" / "trading" / "buy_and_sell_stock.py").read_text(encoding="utf-8")

    assert 'df.at[i, "status"] = "保有中"' not in source
    assert '"売却（利益確定）"' not in source.split("valid_statuses")[0]
    assert "StockStatus.HOLDING" in source
