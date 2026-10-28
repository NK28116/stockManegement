# python/web/api/choices.py
"""プルダウン選択肢の配信 API (PRIDEV-486)

UI が選択肢をハードコードせず、バックエンドの constants を単一の正として
参照できるようにする。
"""

from typing import Dict

from fastapi import APIRouter

from python.web import constants

router = APIRouter(prefix="/api/choices", tags=["choices"])


@router.get("")
async def list_choices() -> Dict[str, object]:
    """銘柄ステータスの選択肢を表示順で返す。"""
    return constants.as_client_payload()
