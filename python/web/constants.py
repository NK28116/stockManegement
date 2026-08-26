# python/web/constants.py
"""UI が参照するプルダウン選択肢 (PRIDEV-486)

* 銘柄ステータス: 単一の定義元は `python/trading/stock_status.py`。
  本モジュールは UI 向けの整形のみを行い、値を再定義しない。
* 保有目的 (purpose): 本モジュールが単一の正。

選択肢を増減させるときは、ステータスなら `python/trading/stock_status.py`、
目的なら本モジュールの `PURPOSE_CHOICES` だけを変更すればよい。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from python.trading import stock_status

__all__ = [
    "DEFAULT_PURPOSE_BADGE_CLASS",
    "DEFAULT_STATUS_BADGE_CLASS",
    "PURPOSE_CHOICES",
    "as_client_payload",
    "purpose_keys",
    "purpose_label",
]


# --- 保有目的 -----------------------------------------------------------------
# 保存値は英字キー (data/my_stock*.csv の purpose 列)、表示は日本語。
PURPOSE_CHOICES: Tuple[Dict[str, str], ...] = (
    {"key": "long", "label": "長期（バリュー投資）", "badge_class": "bg-green-100 text-green-800"},
    {"key": "middle", "label": "中期", "badge_class": "bg-blue-100 text-blue-800"},
    {"key": "present", "label": "優待目的", "badge_class": "bg-pink-100 text-pink-800"},
    {"key": "swing", "label": "スイングトレード", "badge_class": "bg-orange-100 text-orange-800"},
)

DEFAULT_PURPOSE_BADGE_CLASS = "bg-gray-100 text-gray-800"
DEFAULT_STATUS_BADGE_CLASS = stock_status.DEFAULT_BADGE_CLASS

_PURPOSE_BY_KEY = {choice["key"]: choice for choice in PURPOSE_CHOICES}


def purpose_keys() -> List[str]:
    return [choice["key"] for choice in PURPOSE_CHOICES]


def purpose_label(key: str) -> str:
    choice = _PURPOSE_BY_KEY.get(key)
    return choice["label"] if choice else key


def as_client_payload() -> Dict[str, object]:
    """UI へ渡す選択肢一覧。"""
    return {
        "status": [choice.to_dict() for choice in stock_status.STATUS_CHOICES],
        "purpose": [dict(choice) for choice in PURPOSE_CHOICES],
        "default_status_badge_class": DEFAULT_STATUS_BADGE_CLASS,
        "default_purpose_badge_class": DEFAULT_PURPOSE_BADGE_CLASS,
    }
