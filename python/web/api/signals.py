"""
シグナル生成APIエンドポイント

銘柄コードを受け取り、最新の取引ルールに基づいて
売買シグナルを生成し、履歴として保存する。
"""

from datetime import datetime

import yfinance as yf
from fastapi import APIRouter, HTTPException

from python.db.database import get_db_session
from python.db.models import SignalHistory
from python.trading.trading_rules import ImprovedTradingRules
from python.utils.logger import get_logger
from python.utils.rules_loader import get_active_rules
from python.web.schemas import SignalCheckRequest, SignalCheckResponse

logger = get_logger("web", "signals")

router = APIRouter(prefix="/api/signals", tags=["signals"])


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
        # 1. 最新のルールを取得
        active_rules = get_active_rules()
        rule_version = str(active_rules.meta.version)
        logger.info(f"使用するルールバージョン: {rule_version}")

        # 2. yfinance APIで最新の株価データを取得
        ticker = yf.Ticker(stock_code)
        df = ticker.history(period="3mo")  # 3ヶ月分のデータを取得

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"銘柄コード {stock_code} のデータが取得できませんでした",
            )

        # 3. ImprovedTradingRulesクラスでシグナル分析
        trading_rules = ImprovedTradingRules(rules=active_rules)
        trades = trading_rules.analyze_with_improved_rules(df)

        if not trades:
            raise HTTPException(
                status_code=500, detail="シグナル生成に失敗しました（取引履歴が空です）"
            )

        # 4. 最新のシグナルを取得
        latest_trade = trades[-1]
        signal = latest_trade["action"]  # 'BUY', 'SELL', 'HOLD'
        price = float(latest_trade["price"])
        reason = latest_trade["reason"]
        timestamp = datetime.utcnow()

        # 5. SignalHistoryテーブルに保存
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

        # 6. レスポンスを返却
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
