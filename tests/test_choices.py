"""プルダウン選択肢の回帰テスト (PRIDEV-486)

選択肢の欠落を検知することが目的。UI へのハードコードを禁止し、
バックエンドの constants を単一の正として固定する。

選択肢の**実値**の確定はユーザー判断のため本テストでは変更せず、
調査で判明した実データとの差分が PENDING_CHOICE_DECISIONS へ
正しく記録されていることを検証する。
"""

import csv
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.web import constants  # noqa: E402

TEMPLATE_PATH = ROOT / "python" / "web" / "templates" / "index.html"
CSV_PATHS = (ROOT / "data" / "my_stock.csv", ROOT / "data" / "my_stock_local.csv")


@pytest.fixture(scope="module")
def client():
    # lifespan (DB 初期化) は不要なため TestClient をそのまま使う
    from python.web.app import app

    return TestClient(app)


@pytest.fixture(scope="module")
def template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _persisted_values(column: str):
    """永続データ (CSV) に実在する値を集める。"""
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


# --- 単一の正であること -------------------------------------------------------
def test_choices_api_returns_all_status_choices(client):
    payload = client.get("/api/choices").json()

    assert [choice["value"] for choice in payload["status"]] == [
        choice["value"] for choice in constants.STATUS_CHOICES
    ]


def test_no_duplicate_choices():
    values = [choice["value"] for choice in constants.STATUS_CHOICES]
    keys = [choice["key"] for choice in constants.STATUS_CHOICES]

    assert len(values) == len(set(values)), "選択肢の値が重複している"
    assert len(keys) == len(set(keys)), "選択肢のキーが重複している"


def test_no_empty_choices():
    for choice in constants.STATUS_CHOICES:
        assert choice["key"].strip(), "空のキーがある"
        assert choice["value"].strip(), "空の表示値がある"


def test_display_order_follows_definition_order():
    assert constants.status_display_order() == {
        choice["value"]: index for index, choice in enumerate(constants.STATUS_CHOICES)
    }


# --- 欠落の検知 ---------------------------------------------------------------
def test_template_does_not_enumerate_choices(template):
    """UI が選択肢一覧を持たないこと (2 箇所のハードコードが欠落の原因だった)。

    個々の値が文言として出てくること自体は許容し、
    「選択肢の列挙」(狭い範囲に 3 つ以上まとまって現れる) だけを禁止する。
    """
    values = [choice["value"] for choice in constants.STATUS_CHOICES]
    positions = sorted(
        (match.start(), value)
        for value in values
        for match in re.finditer(re.escape(value), template)
    )

    window = 400
    for index, (start, _) in enumerate(positions):
        nearby = {value for position, value in positions[index:] if position - start < window}
        assert len(nearby) < 3, (
            f"選択肢が {template[start:start + window][:120]!r} 付近へ列挙されている。"
            "選択肢は /api/choices から取得すること"
        )

    assert "SOLD_PROFIT" not in template, "選択肢キーがテンプレートへハードコードされている"
    assert "/api/choices" in template, "UI がバックエンドの選択肢を取得していない"


def test_status_badge_class_is_data_driven(template):
    """表示クラスの分岐が選択肢の二重管理になっていないこと。"""
    body = re.search(r"getStatusClass\(status\) \{(.*?)\n                \},", template, re.DOTALL)
    assert body, "getStatusClass が見つからない"
    source = body.group(1)

    assert "matched.badge_class" in source, "表示クラスを選択肢定義から引いていない"
    for choice in constants.STATUS_CHOICES:
        assert choice["value"] not in source, f"{choice['value']} が分岐へ直書きされている"
        assert choice["badge_class"] not in source, (
            f"{choice['value']} の表示クラスが分岐へ直書きされている"
        )


def test_template_renders_every_choice_from_the_api(template):
    """v-for が API の配列全体を描画していること (件数の取りこぼしが起きない)。"""
    option = re.search(r'<option v-for="choice in statusChoices"[^>]*>', template)

    assert option, "選択肢の描画が API 由来になっていない"
    assert ':value="choice.key"' in option.group(0)
    assert "slice(" not in option.group(0), "選択肢を途中で切り詰めないこと"


def test_sort_order_is_derived_from_choices(template):
    """並び順の定義が選択肢と二重管理になっていないこと。"""
    assert "const statusOrder = this.statusOrder" in template
    assert template.count("statusOrder[a.status]") == 1


def test_selected_value_is_the_persisted_key_format(client):
    """選択後に送信される値が期待する形式であること。"""
    payload = client.get("/api/choices").json()

    for choice in payload["status"]:
        assert re.fullmatch(r"[A-Z_]+", choice["key"]), f"想定外のキー形式: {choice['key']}"


# --- ユーザー確認待ちの差分が正しく記録されていること --------------------------
def test_pending_status_gap_matches_actual_data():
    """永続データにあって UI に無い status が、記録どおりであること。"""
    ui_values = {choice["value"] for choice in constants.STATUS_CHOICES}
    recorded = set(constants.PENDING_CHOICE_DECISIONS["status_missing_from_ui"]["values"])

    actual_gap = _persisted_values("status") - ui_values

    assert actual_gap == recorded, (
        "実データと UI の差分が記録と一致しない。"
        f"実際={sorted(actual_gap)} 記録={sorted(recorded)}。"
        "PENDING_CHOICE_DECISIONS を更新するか、選択肢の確定内容を反映すること"
    )


def test_pending_purpose_values_match_actual_data():
    """purpose 列の実値が記録どおりであること。"""
    recorded = set(constants.PENDING_CHOICE_DECISIONS["purpose_dropdown_shows_status"]["values"])

    assert _persisted_values("purpose") == recorded


def test_purpose_dropdown_still_bound_to_status_choices(template):
    """purpose select の選択肢仕様はユーザー確認待ちのため、現状を維持していること。

    確定後にこのテストが落ちることで、仕様変更が意図的であることを明示する。
    """
    assert 'v-model="purpose"' in template
    assert 'v-for="choice in statusChoices"' in template, (
        "purpose 用の選択肢へ切り替えるのはユーザー確認後 (PRIDEV-486)"
    )
