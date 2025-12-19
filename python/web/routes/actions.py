# python/web/routes/actions.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

# 市場データ更新ロジックのインポート
try:
    from python import watch
except ImportError:
    watch = None

try:
    from python.watch import analyze
except ImportError:
    analyze = None


router = APIRouter(prefix="/api/actions", tags=["actions"])
logger = logging.getLogger(__name__)


class ActionState:
    last_update_time: Optional[datetime] = None
    is_updating: bool = False
    is_analyzing: bool = False


_state = ActionState()
_UPDATE_COOLDOWN = timedelta(hours=1)


async def _run_market_update():
    """
    バックグラウンドで実行される市場データ更新処理
    """
    try:
        logger.info("Starting market data update task...")

        if watch is None:
            raise ImportError("python.watch module could not be imported.")

        # 実際のデータ更新ロジック(watch.main)を別スレッドで実行
        loop = asyncio.get_running_loop()
        # watch.main() がエントリポイントであると仮定
        await loop.run_in_executor(None, watch.main)

        logger.info("Market data update task completed successfully.")

    except Exception as e:
        logger.error(f"Error during market data update: {e}", exc_info=True)
    finally:

        # 成功・失敗に関わらず、必ずフラグを下ろす
        _state.is_updating = False


async def _run_analysis():
    """
    バックグラウンドで実行される分析処理
    """
    try:
        logger.info("Starting analysis task...")

        if analyze is None:
            raise ImportError("python.watch.analyze module could not be imported.")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, analyze.main)

        logger.info("Analysis task completed successfully.")

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
    finally:
        _state.is_analyzing = False


@router.post("/update-market-data")
async def trigger_market_update(background_tasks: BackgroundTasks):
    """
    市場データ更新を手動トリガーするエンドポイント
    """
    now = datetime.now()

    # 実行中チェック
    if _state.is_updating:
        raise HTTPException(status_code=409, detail="Update already in progress")

    # クールダウンチェック
    if _state.last_update_time:
        elapsed = now - _state.last_update_time
        if elapsed < _UPDATE_COOLDOWN:
            remaining_minutes = int((_UPDATE_COOLDOWN - elapsed).total_seconds() / 60)
            raise HTTPException(
                status_code=429,
                detail=f"Update limit reached. Please wait {remaining_minutes} minutes.",
            )

    # 状態更新
    _state.is_updating = True
    _state.last_update_time = now

    # バックグラウンドタスクの登録
    background_tasks.add_task(_run_market_update)

    return {
        "status": "accepted",
        "message": "Market data update started in background.",
        "timestamp": now.isoformat(),
    }


@router.post("/analyze-signals")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """
    分析処理を手動トリガーするエンドポイント
    """
    if _state.is_analyzing:
        raise HTTPException(status_code=409, detail="Analysis already in progress")

    _state.is_analyzing = True
    background_tasks.add_task(_run_analysis)

    return {
        "status": "accepted",
        "message": "Analysis started in background.",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/status")
async def get_action_status():
    """
    現在のアクション実行状態を取得する
    """
    return {
        "is_updating": _state.is_updating,
        "is_analyzing": _state.is_analyzing,
        "last_update_time": _state.last_update_time,
        "cooldown_remaining_seconds": (
            max(
                0,
                (
                    _UPDATE_COOLDOWN - (datetime.now() - _state.last_update_time)
                ).total_seconds(),
            )
            if _state.last_update_time
            else 0
        ),
    }
