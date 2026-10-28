"""銘柄ステータスの単一定義元のテスト (PRIDEV-486)

保存値・表示名・保有判定がユーザー確認済みの仕様どおりであることを固定する。
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python.trading import stock_status  # noqa: E402
from python.trading.stock_status import StockStatus  # noqa: E402

# ユーザー確認済みの 8 種 (シート No.5 の回答順)
CONFIRMED_KEYS = [
    "HOLDING",
    "NEXT_BUY",
    "SELL_PLANNED_PROFIT",
    "SELL_PLANNED_LOSS",
    "SOLD_PROFIT",
    "SOLD_LOSS",
    "WATCHING",
    "EXCLUDED",
]


# --- 選択肢 -------------------------------------------------------------------
def test_status_keys_match_the_confirmed_specification():
    assert stock_status.status_keys() == CONFIRMED_KEYS


def test_every_status_has_a_japanese_label():
    for choice in stock_status.STATUS_CHOICES:
        assert choice.label, f"{choice.key} に表示名が無い"
        assert choice.label != choice.key, f"{choice.key} の表示名が保存値のまま"


def test_no_duplicate_keys_or_labels():
    keys = [choice.key for choice in stock_status.STATUS_CHOICES]
    labels = [choice.label for choice in stock_status.STATUS_CHOICES]

    assert len(keys) == len(set(keys))
    assert len(labels) == len(set(labels))


def test_sell_planned_and_sold_are_separate_values():
    """売却予定と売却済みが保存値として分離されていること。"""
    assert StockStatus.SELL_PLANNED_PROFIT != StockStatus.SOLD_PROFIT
    assert StockStatus.SELL_PLANNED_LOSS != StockStatus.SOLD_LOSS


def test_display_order_follows_definition_order():
    assert stock_status.status_display_order() == {
        key: index for index, key in enumerate(CONFIRMED_KEYS)
    }


# --- 保有判定 -----------------------------------------------------------------
@pytest.mark.parametrize(
    "status,expected",
    [
        (StockStatus.HOLDING, True),
        (StockStatus.SELL_PLANNED_PROFIT, True),  # 売却予定は保有
        (StockStatus.SELL_PLANNED_LOSS, True),
        (StockStatus.SOLD_PROFIT, False),  # 売却済みは未保有
        (StockStatus.SOLD_LOSS, False),
        (StockStatus.NEXT_BUY, False),
        (StockStatus.WATCHING, False),
        (StockStatus.EXCLUDED, False),
    ],
)
def test_is_held_matches_the_confirmed_rule(status, expected):
    assert stock_status.is_held(status) is expected


def test_held_status_values_is_the_single_source_for_queries():
    assert stock_status.held_status_values() == [
        StockStatus.HOLDING,
        StockStatus.SELL_PLANNED_PROFIT,
        StockStatus.SELL_PLANNED_LOSS,
    ]


def test_unknown_status_is_not_held():
    assert stock_status.is_held("SOMETHING_ELSE") is False
    assert stock_status.is_held(None) is False
    assert stock_status.is_held("") is False


# --- 旧データの正規化 ---------------------------------------------------------
@pytest.mark.parametrize(
    "legacy,expected",
    [
        ("保有中", StockStatus.HOLDING),
        ("次回のスイングで購入", StockStatus.NEXT_BUY),
        ("監視中", StockStatus.WATCHING),
        ("除外", StockStatus.EXCLUDED),
    ],
)
def test_legacy_labels_are_normalized(legacy, expected):
    assert stock_status.normalize(legacy) == expected


@pytest.mark.parametrize(
    "legacy,quantity,expected",
    [
        # 数量が残っている = 売却予定として運用されていた行
        ("売却（利益確定）", 1, StockStatus.SELL_PLANNED_PROFIT),
        ("売却（損切り）", 3, StockStatus.SELL_PLANNED_LOSS),
        # 数量 0 = 実際に売却済み (sell_stock() は売却時に数量を 0 にする)
        ("売却（利益確定）", 0, StockStatus.SOLD_PROFIT),
        ("売却（損切り）", 0, StockStatus.SOLD_LOSS),
    ],
)
def test_legacy_sell_labels_resolve_by_quantity(legacy, quantity, expected):
    assert stock_status.normalize(legacy, quantity) == expected


def test_normalize_is_idempotent_for_new_keys():
    for key in CONFIRMED_KEYS:
        assert stock_status.normalize(key) == key


def test_normalize_returns_none_for_unknown_values():
    assert stock_status.normalize("売却") is None, "利確/損切りが判別できない値は手動確認へ回す"
    assert stock_status.normalize("なにか") is None
    assert stock_status.normalize(None) is None


def test_normalize_tolerates_broken_quantity():
    assert stock_status.normalize("売却（利益確定）", "not-a-number") == StockStatus.SOLD_PROFIT
