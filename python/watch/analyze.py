# python/watch/analyze.py

import logging

import pandas as pd

from python.config import config
from python.db.database import get_db_connection
from python.utils.alert import send_alert
from python.utils.indicators import (
    calculate_bollinger_bands,
    calculate_macd,
)
from python.utils.rules_loader import get_active_rules

logger = logging.getLogger("analyze")


def get_daily_price_data(code: str, limit: int = 100) -> pd.DataFrame:
    """
    指定された銘柄の日足データを取得する
    Args:
        code: 銘柄コード
        limit: 取得件数
    Returns:
        DataFrame: 日足データ (index=date, columns=[open, high, low, close, volume])
    """
    query = f"""
        SELECT date, open, high, low, close, volume
        FROM daily_data
        WHERE code = '{code}'
        ORDER BY date ASC
    """
    if limit:
        # 直近のデータを取得するためにサブクエリを使うか、Python側でスライスするか
        # ここでは全件取得してPython側で処理（データ量次第だがシンプルに）
        # もしくは ORDER BY date DESC LIMIT limit して sort_index する
        query = f"""
            SELECT * FROM (
                SELECT date, open, high, low, close, volume
                FROM daily_data
                WHERE code = '{code}'
                ORDER BY date DESC
                LIMIT {limit}
            ) as sub
            ORDER BY date ASC
        """

    try:
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn, index_col="date", parse_dates=["date"])
        conn.close()
        return df
    except Exception as e:
        logger.error(f"日足データ取得エラー ({code}): {e}")
        return pd.DataFrame()


def analyze_daily_data(code: str, name: str):
    """
    日足データを分析し、シグナルが出ていれば通知する
    """
    logger.info(f"Analyzing daily data for {code} ({name})...")
    
    # データ取得 (分析に必要な期間分)
    # MACDなど長期の指標計算のためにある程度過去分も必要
    df = get_daily_price_data(code, limit=100)
    if df.empty or len(df) < 2:
        logger.warning(f"データ不足のため分析スキップ: {code}")
        return

    # ルール取得
    rules = get_active_rules()

    # 1. 急落検知 (単純な価格変動チェック)
    # config から閾値を取得 (-10.0 など)
    crash_threshold = config.crash_threshold
    
    current_price = df.iloc[-1]["close"]
    prev_price = df.iloc[-2]["close"]
    
    change_rate = (current_price - prev_price) / prev_price * 100
    
    if change_rate <= crash_threshold:
        msg = f"⚠️ 【急落注意】{name} ({code}) が前日比 {change_rate:.2f}% 下落しました (現在値: {current_price})"
        send_alert(msg, level="WARNING")
        logger.warning(msg)

    # 2. テクニカル分析 (MACD)
    macd_df = calculate_macd(
        df["close"],
        short_period=rules.indicators.macd.fast_period,
        long_period=rules.indicators.macd.slow_period,
        signal_period=rules.indicators.macd.signal_period
    )
    
    # 直近のクロス判定
    if len(macd_df) >= 2:
        curr_macd = macd_df.iloc[-1]["MACD"]
        curr_signal = macd_df.iloc[-1]["Signal"]
        prev_macd = macd_df.iloc[-2]["MACD"]
        prev_signal = macd_df.iloc[-2]["Signal"]

        # ゴールデンクロス (MACDがSignalを下から上に抜ける)
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            logger.info(f"MACDゴールデンクロス検知: {name} ({code})")
            # 必要ならアラート送信
            # send_alert(f"📈 {name} ({code}) MACD Golden Cross!", level="INFO")

    # 3. テクニカル分析 (Bollinger Bands)
    bb_df = calculate_bollinger_bands(
        df["close"],
        period=rules.indicators.bollinger.period,
        num_std=rules.indicators.bollinger.std
    )
    
    if len(bb_df) >= 1:
        curr_close = df.iloc[-1]["close"]
        upper = bb_df.iloc[-1]["Upper"]
        lower = bb_df.iloc[-1]["Lower"]
        
        if curr_close > upper:
            logger.info(f"ボリンジャーバンド アッパーバンド突破: {name} ({code})")
        elif curr_close < lower:
            logger.info(f"ボリンジャーバンド ローワーバンド下抜け: {name} ({code})")


def main():
    """
    分析ロジックのエントリーポイント
    現在はプレースホルダーとしての実装
    """
    logger.info("Starting analysis (placeholder)...")
    logger.info("Analysis completed.")
