"""
シグナル生成APIエンドポイント

銘柄コードを受け取り、最新の取引ルールに基づいて
売買シグナルを生成し、履歴として保存する。
"""

import asyncio
import json
from datetime import datetime
from typing import List, Optional

import yfinance as yf
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from python.db.database import get_db_session, engine
from python.db.models import Signal, SignalHistory
from python.trading.trading_rules import ImprovedTradingRules
from python.utils.logger import get_logger
from python.utils.rules_loader import get_active_rules
from python.web.schemas import SignalCheckRequest, SignalCheckResponse

logger = get_logger("web", "signals")

router = APIRouter(prefix="/api/signals", tags=["signals"])


# --- 週足スイング分析 State ---
class _AnalyzeState:
    is_analyzing: bool = False


_analyze_state = _AnalyzeState()


async def _run_swing_analysis() -> None:
    """バックグラウンドで週足スイング分析を実行する"""
    try:
        logger.info("週足スイング分析 バックグラウンドタスク 開始")
        from python.watch.analyze import main as analyze_main

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, analyze_main)
        logger.info("週足スイング分析 バックグラウンドタスク 完了")
    except Exception as e:
        logger.error(f"週足スイング分析エラー: {e}", exc_info=True)
    finally:
        _analyze_state.is_analyzing = False


@router.post("/analyze", status_code=202)
async def trigger_swing_analysis(background_tasks: BackgroundTasks):
    """
    保有・監視銘柄の週足スイングトレード分析をバックグラウンドで開始する
    既に実行中の場合は 409 を返す
    """
    if _analyze_state.is_analyzing:
        raise HTTPException(status_code=409, detail="Analysis already in progress")

    _analyze_state.is_analyzing = True
    background_tasks.add_task(_run_swing_analysis)

    return {
        "status": "accepted",
        "message": "週足スイング分析を開始しました。",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/status")
async def get_analysis_status():
    """分析実行状態を返す"""
    return {"is_analyzing": _analyze_state.is_analyzing}


class SignalResponse(BaseModel):
    id: int
    symbol: str
    analysis_date: str
    signal_type: str
    score: int
    detected_patterns: List[str]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    rationale: Optional[str]
    created_at: str
    is_held: bool

    class Config:
        from_attributes = True


@router.get("/latest", response_model=List[SignalResponse])
async def get_latest_signals():
    """
    signals テーブルから銘柄ごとの最新シグナルを返す。
    portfolio テーブルと結合して保有中かどうか (is_held) を付与する。
    """
    try:
        from sqlalchemy import text

        # GROUP BY + MAX(created_at) で銘柄ごとの最新レコードを取得し、
        # portfolio テーブルと LEFT JOIN して保有フラグを付与する
        # (DISTINCT ON は PostgreSQL 固有のため、SQLite でも動く標準 SQL に変更)
        query = text(
            """
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            """
        )

        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        results = []
        for row in rows:
            patterns_raw = row.detected_patterns or "[]"
            try:
                patterns = json.loads(patterns_raw)
            except (json.JSONDecodeError, TypeError):
                patterns = []

            results.append(
                SignalResponse(
                    id=row.id,
                    symbol=row.symbol,
                    analysis_date=str(row.analysis_date),
                    signal_type=row.signal_type,
                    score=row.score or 0,
                    detected_patterns=patterns,
                    stop_loss=row.stop_loss,
                    take_profit=row.take_profit,
                    rationale=row.rationale,
                    created_at=str(row.created_at),
                    is_held=bool(row.is_held),
                )
            )

        return results

    except Exception as e:
        logger.error(f"最新シグナル取得エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部エラー: {str(e)}")


@router.post("/check", response_model=SignalCheckResponse)
async def check_signal(request: SignalCheckRequest):
    """
    指定された銘柄の売買シグナルをチェックする

    Args:
        request: 銘柄コードを含むリクエスト

    Returns:
        SignalCheckResponse: 生成されたシグナル情報

    Raises:
        HTTPException: データ取得失敗やシグナル生成失敗時
    """
    stock_code = request.stock_code
    logger.info(f"シグナルチェック開始: {stock_code}")

    try:
        active_rules = get_active_rules()
        rule_version = str(active_rules.meta.version)
        logger.info(f"使用するルールバージョン: {rule_version}")

        ticker = yf.Ticker(stock_code)
        df = ticker.history(period="3mo")

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"銘柄コード {stock_code} のデータが取得できませんでした",
            )

        trading_rules = ImprovedTradingRules(rules=active_rules)
        trades = trading_rules.analyze_with_improved_rules(df)

        if not trades:
            raise HTTPException(
                status_code=500, detail="シグナル生成に失敗しました（取引履歴が空です）"
            )

        latest_trade = trades[-1]
        signal = latest_trade["action"]
        price = float(latest_trade["price"])
        reason = latest_trade["reason"]
        timestamp = datetime.utcnow()

        with get_db_session() as session:
            signal_record = SignalHistory(
                stock_code=stock_code,
                timestamp=timestamp,
                signal=signal,
                price=price,
                reason=reason,
                rule_version=rule_version,
            )
            session.add(signal_record)
            session.commit()
            logger.info(f"シグナル履歴を保存しました: {stock_code} - {signal}")

        return SignalCheckResponse(
            stock_code=stock_code,
            signal=signal,
            price=price,
            reason=reason,
            rule_version=rule_version,
            timestamp=timestamp,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"シグナルチェック中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部エラーが発生しました: {str(e)}")
