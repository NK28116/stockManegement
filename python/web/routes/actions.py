# python/web/routes/actions.py

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from python.trading import buy_and_sell_stock

router = APIRouter(prefix="/api/actions", tags=["actions"])
logger = logging.getLogger(__name__)

# 市場データ更新ロジックのインポート
try:
    from python import watch
except ImportError:
    watch = None

try:
    from python.watch import analyze
except ImportError:
    analyze = None

# チャート一括再生成モジュール
try:
    from python.visualization import generate_all_charts
except ImportError:
    generate_all_charts = None


class SellRequest(BaseModel):
    sell_type: str  # 'profit' or 'loss'


class BuyRequest(BaseModel):
    quantity: int
    price: Optional[float] = None
    purpose: Optional[str] = None


@router.post("/buy/{code}")
async def buy_stock(code: str, buy_request: BuyRequest):
    """
    指定された銘柄コードの株を購入するAPIエンドポイント。
    """
    try:
        # 既存のCSVファイルを読み込む
        df = buy_and_sell_stock.load_codes(buy_and_sell_stock.config.codes_path)

        # buy関数を呼び出してデータフレームを更新
        updated_df = buy_and_sell_stock.buy(df, code, buy_request.quantity, buy_request.price)

        # purposeが指定されていれば更新
        if buy_request.purpose and code in updated_df["code"].values:
            updated_df.loc[updated_df["code"] == code, "purpose"] = buy_request.purpose

        # 更新されたデータフレームをCSVファイルに保存
        buy_and_sell_stock.save_codes(updated_df, buy_and_sell_stock.config.codes_path)

        return {
            "status": "success",
            "message": f"Successfully bought {buy_request.quantity} of {code}.",
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Portfolio file not found.")
    except Exception as e:
        logger.error(f"Error buying stock {code}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sell/{code}")
async def sell_stock(code: str, sell_request: SellRequest):
    try:
        # Pass the sell_type to the underlying sell function
        result = buy_and_sell_stock.sell_stock(code, sell_type=sell_request.sell_type)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {
            "status": "success",
            "message": result.get("message", f"Stock {code} sold."),
        }
    except Exception as e:
        logger.error(f"Error selling stock {code}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/stock/{code}")
async def delete_stock(code: str):
    """
    銘柄をダッシュボード（CSV）から完全に削除するエンドポイント。
    """
    try:
        result = buy_and_sell_stock.delete_stock(code)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return {
            "status": "success",
            "message": result.get("message", f"Stock {code} deleted."),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stock {code}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ActionState:
    last_update_time: Optional[datetime] = None
    is_updating: bool = False
    is_analyzing: bool = False


_state = ActionState()
_UPDATE_COOLDOWN = timedelta(hours=1)


async def _run_market_update():
    """
    バックグラウンドで実行される市場データ更新処理

    ダッシュボードの「Update Data」ボタンから呼ばれる。以下のステップを順に実行する。
      1) watch.main(): intraday 株価取得 + DB 保存 (従来通り)
      2) refresh_prices(): ポートフォリオCSVの current_price / profit_loss /
         profit_loss_percent / last_updated を最新の株価で書き換える
      3) generate_all_charts.main(): Plots (MACD/BB) と ChartImg (Signals) の
         PNG 画像を全銘柄ぶん再生成する → これをやらないと横軸の日付が古いまま
    """
    try:
        logger.info("Starting market data update task...")

        loop = asyncio.get_running_loop()

        # --- Step 1: intraday データ取得 (watch.main) ---
        if watch is None:
            logger.warning("python.watch module is not available; skipping intraday fetch.")
        else:
            try:
                await loop.run_in_executor(None, watch.main)
                logger.info("Step 1/3: watch.main() completed.")
            except Exception as watch_err:
                # watch.main() が失敗しても、後続のCSV/チャート更新は試す
                logger.error(
                    f"Step 1/3: watch.main() failed: {watch_err}", exc_info=True
                )

        # --- Step 2: ポートフォリオCSVの価格フィールドを最新値に更新 ---
        try:
            path = buy_and_sell_stock.config.codes_path
            df = buy_and_sell_stock.load_codes(path)

            # refresh_prices は code ごとに yfinance から現在値を取得し、
            # current_price / profit_loss / profit_loss_percent / last_updated を上書きする
            df = await loop.run_in_executor(
                None, buy_and_sell_stock.refresh_prices, df, None
            )

            # last_updated は refresh_prices 側では日付のみ ("%Y-%m-%d") が入るため、
            # 従来通り時刻付き表記に再設定して画面と整合させる
            update_time_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            if "last_updated" in df.columns:
                df["last_updated"] = update_time_str

            buy_and_sell_stock.save_codes(df, path)
            logger.info(
                f"Step 2/3: Successfully refreshed prices and last_updated in {path}"
            )
        except Exception as csv_err:
            logger.error(
                f"Step 2/3: Failed to refresh portfolio CSV: {csv_err}",
                exc_info=True,
            )

        # --- Step 3: チャート画像の一括再生成 ---
        # 案B: 重いチャート生成はGCE側のcronワーカーに集約する。
        # Render等のWeb環境では DISABLE_CHART_GENERATION=1 を設定してスキップし、
        # メモリ制約やGCS未連携による「ローカル生成→反映されない」問題を回避する。
        if os.getenv("DISABLE_CHART_GENERATION", "").lower() in ("1", "true", "yes"):
            logger.info(
                "Step 3/3: DISABLE_CHART_GENERATION が設定されているためチャート生成をスキップ "
                "(チャートはGCEワーカーの定期ジョブで生成・GCSへ反映されます)。"
            )
        elif generate_all_charts is None:
            logger.warning(
                "Step 3/3: python.visualization.generate_all_charts is not available; "
                "chart images will NOT be regenerated."
            )
        else:
            try:
                # 日次タスクと同じ 1mo 期間で再生成する
                await loop.run_in_executor(
                    None, lambda: generate_all_charts.main(period="1mo")
                )
                logger.info("Step 3/3: Chart images regenerated successfully.")
            except Exception as chart_err:
                logger.error(
                    f"Step 3/3: Failed to regenerate chart images: {chart_err}",
                    exc_info=True,
                )

        logger.info("Market data update task completed.")

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
                (_UPDATE_COOLDOWN - (datetime.now() - _state.last_update_time)).total_seconds(),
            )
            if _state.last_update_time
            else 0
        ),
    }
