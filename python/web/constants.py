# python/web/constants.py
"""プルダウン選択肢の単一の正 (PRIDEV-486)

これまで選択肢はテンプレート (`index.html`) の 2 箇所へ別々にハードコードされて
いた。本モジュールをバックエンド側の単一の正とし、UI は `/api/choices` 経由で
取得する。選択肢を増減させるときは本モジュールだけを変更すればよい。

**選択肢の実値はまだ確定していない。** 調査で判明した実データとの差分は
PENDING_CHOICE_DECISIONS へ記録するにとどめ、ユーザー確認前に反映しない
(PRIDEV-486「ユーザー確認前に新しい選択肢仕様を発明して追加しない」)。
"""

from __future__ import annotations

from typing import Dict, Tuple

__all__ = [
    "DEFAULT_STATUS_BADGE_CLASS",
    "PENDING_CHOICE_DECISIONS",
    "STATUS_CHOICES",
    "as_client_payload",
    "status_display_order",
]


# --- 銘柄ステータス -----------------------------------------------------------
# 現行 UI (index.html) の選択肢をそのまま移設したもの。value は永続化される値で、
# data/my_stock*.csv の status 列および python/web/api/signals.py の判定と一致する。
# 並び順はダッシュボードの表示順にそのまま使う。
# badge_class は現行 UI の getStatusClass から移設したもの (新規の意匠は追加していない)。
STATUS_CHOICES: Tuple[Dict[str, str], ...] = (
    {"key": "HOLDING", "value": "保有中", "badge_class": "bg-blue-100 text-blue-800"},
    {"key": "NEXT_BUY", "value": "次回のスイングで購入", "badge_class": "bg-purple-100 text-purple-800"},
    {"key": "WATCHING", "value": "監視中", "badge_class": "bg-yellow-100 text-yellow-800"},
    {"key": "SOLD_PROFIT", "value": "売却（利益確定）", "badge_class": "bg-green-100 text-green-800"},
    {"key": "SOLD_LOSS", "value": "売却（損切り）", "badge_class": "bg-red-100 text-red-800"},
)

# 未知の status に対するフォールバック表示
DEFAULT_STATUS_BADGE_CLASS = "bg-gray-100 text-gray-800"


# --- ユーザー確認待ちの差分 ---------------------------------------------------
# 調査で判明した現行 UI と永続データの食い違い。仕様確定はユーザー判断のため、
# ここでは記録のみ行い UI へは反映しない。確定後に STATUS_CHOICES 等を更新すれば
# 画面・API の両方へ 1 箇所で反映される。
# tests/test_choices.py が、この記録が実データの状況と一致していることを検証する。
PENDING_CHOICE_DECISIONS: Dict[str, Dict[str, object]] = {
    "status_missing_from_ui": {
        "description": "data/my_stock*.csv の status 列に存在するが UI から選べない値",
        "values": ("除外",),
    },
    "purpose_dropdown_shows_status": {
        "description": (
            "「目的別」select が purpose ではなく status の選択肢を表示している。"
            "永続データ (my_stock*.csv の purpose 列) の実値は下記のとおり"
        ),
        "values": ("long", "middle", "present", "swing"),
    },
}


def status_display_order() -> Dict[str, int]:
    """ダッシュボードの並び順 (status 値 → 表示順)。"""
    return {choice["value"]: index for index, choice in enumerate(STATUS_CHOICES)}


def as_client_payload() -> Dict[str, object]:
    """UI へ渡す選択肢一覧。"""
    return {
        "status": [dict(choice) for choice in STATUS_CHOICES],
        "default_status_badge_class": DEFAULT_STATUS_BADGE_CLASS,
    }
