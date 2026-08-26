# python/trading/stock_status.py
"""銘柄ステータスの単一の定義元 (PRIDEV-486)

保存値・表示名・保有判定をすべて本モジュールで定義する。
UI は `/api/choices` 経由で本定義から選択肢を取得し、値を持たない。

保存値は英字キー (例: ``HOLDING``)。旧データは日本語の表示文字列を
保存値として持っているため、:func:`normalize` で英字キーへ正規化する。

保有判定 (:func:`is_held`):
    * 売却予定 (``SELL_PLANNED_*``) は **保有**
    * 売却済み (``SOLD_*``) は **未保有**
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

__all__ = [
    "LEGACY_STATUS_LABELS",
    "STATUS_CHOICES",
    "StockStatus",
    "held_status_values",
    "is_held",
    "normalize",
    "status_display_order",
    "status_keys",
    "status_label",
]


class StockStatus:
    """保存値 (英字キー)。"""

    HOLDING = "HOLDING"
    NEXT_BUY = "NEXT_BUY"
    SELL_PLANNED_PROFIT = "SELL_PLANNED_PROFIT"
    SELL_PLANNED_LOSS = "SELL_PLANNED_LOSS"
    SOLD_PROFIT = "SOLD_PROFIT"
    SOLD_LOSS = "SOLD_LOSS"
    WATCHING = "WATCHING"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True)
class StatusChoice:
    key: str
    label: str
    badge_class: str
    held: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "badge_class": self.badge_class,
            "held": self.held,
        }


# 定義順がそのまま画面の表示順・並び順になる。
STATUS_CHOICES: Tuple[StatusChoice, ...] = (
    StatusChoice(StockStatus.HOLDING, "保有中", "bg-blue-100 text-blue-800", held=True),
    StatusChoice(StockStatus.NEXT_BUY, "次回のスイングで購入", "bg-purple-100 text-purple-800", held=False),
    StatusChoice(
        StockStatus.SELL_PLANNED_PROFIT, "売却予定（利益確定）", "bg-teal-100 text-teal-800", held=True
    ),
    StatusChoice(
        StockStatus.SELL_PLANNED_LOSS, "売却予定（損切り）", "bg-orange-100 text-orange-800", held=True
    ),
    StatusChoice(StockStatus.SOLD_PROFIT, "売却済み（利益確定）", "bg-green-100 text-green-800", held=False),
    StatusChoice(StockStatus.SOLD_LOSS, "売却済み（損切り）", "bg-red-100 text-red-800", held=False),
    StatusChoice(StockStatus.WATCHING, "監視中", "bg-yellow-100 text-yellow-800", held=False),
    StatusChoice(StockStatus.EXCLUDED, "除外", "bg-gray-200 text-gray-700", held=False),
)

DEFAULT_BADGE_CLASS = "bg-gray-100 text-gray-800"

_BY_KEY: Dict[str, StatusChoice] = {choice.key: choice for choice in STATUS_CHOICES}

# 旧データ (保存値が日本語表示文字列) からの対応表。
# 「売却（…）」は数量が残っていれば売却予定、0 なら売却済みとして解決する。
LEGACY_STATUS_LABELS: Dict[str, str] = {
    "保有中": StockStatus.HOLDING,
    "次回のスイングで購入": StockStatus.NEXT_BUY,
    "監視中": StockStatus.WATCHING,
    "除外": StockStatus.EXCLUDED,
}

_LEGACY_SELL_LABELS: Dict[str, Tuple[str, str]] = {
    # 旧ラベル: (数量が残っている場合, 数量が 0 の場合)
    "売却（利益確定）": (StockStatus.SELL_PLANNED_PROFIT, StockStatus.SOLD_PROFIT),
    "売却（損切り）": (StockStatus.SELL_PLANNED_LOSS, StockStatus.SOLD_LOSS),
}


def status_keys() -> List[str]:
    return [choice.key for choice in STATUS_CHOICES]


def status_label(key: str) -> str:
    choice = _BY_KEY.get(key)
    return choice.label if choice else key


def status_display_order() -> Dict[str, int]:
    """保存値 → 表示順。"""
    return {choice.key: index for index, choice in enumerate(STATUS_CHOICES)}


def held_status_values() -> List[str]:
    """保有とみなす保存値の一覧 (SQL の IN 句などで使う)。"""
    return [choice.key for choice in STATUS_CHOICES if choice.held]


def is_held(status: Optional[str], quantity: Optional[float] = None) -> bool:
    """保有中かどうかを判定する。旧データの日本語ラベルも受け付ける。"""
    key = normalize(status, quantity)
    choice = _BY_KEY.get(key or "")
    return bool(choice and choice.held)


def normalize(status: Optional[str], quantity: Optional[float] = None) -> Optional[str]:
    """保存値を英字キーへ正規化する。判定できない場合は None。

    Args:
        status: 英字キー、または旧データの日本語ラベル。
        quantity: 旧ラベル「売却（…）」の解決に使う保有数量。
            数量が残っていれば売却予定、0 以下なら売却済みとみなす。
    """
    if status is None:
        return None
    raw = str(status).strip()
    if not raw:
        return None
    if raw in _BY_KEY:
        return raw
    if raw in LEGACY_STATUS_LABELS:
        return LEGACY_STATUS_LABELS[raw]
    if raw in _LEGACY_SELL_LABELS:
        planned, sold = _LEGACY_SELL_LABELS[raw]
        try:
            remaining = float(quantity) if quantity is not None else 0.0
        except (TypeError, ValueError):
            remaining = 0.0
        return planned if remaining > 0 else sold
    return None
