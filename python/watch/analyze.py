import pandas as pd
import psycopg2
from psycopg2 import Error as PgError

from python.utils.logger import get_logger
from python.db.database import get_db_connection

from python.config import config
from python.utils.indicators import (  # インジケーター計算関数をインポート
    calculate_bollinger_bands,
    calculate_macd,
)

logger = get_logger("analyze", category="watch")

__all__ = ["analyze_daily_data"]


def get_daily_price_data(code, limit=config.volatility_period + 20):  # MACD/BB計算用に多めに取得
    """DBから指定銘柄の日足データを取得する"""
    conn = None
    try:
        conn = get_db_connection()
        query = f"SELECT date, open, high, low, close, volume \
                FROM stock_data \
                WHERE code = %s \
                ORDER BY date ASC LIMIT %s"
        df = pd.read_sql_query(query, conn, params=(code, limit), index_col="date", parse_dates=["date"])
        return df
    except PgError as e:
        logger.error(f"DBから日足データ取得エラー: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def analyze_daily_data(code: str):
    """
    指定された銘柄の日足データを分析し、急落検知やテクニカル指標に基づく警告を行う

    Args:
        code (str): 分析対象の銘柄コード
    """
    logger.info(f"銘柄 {code} の日足データ分析を開始")
    df = get_daily_price_data(code)

    if df.empty:
        logger.warning(f"銘柄 {code} の日足データが見つかりませんでした。")
        return

    # --- 前日比急落検知 ---
    if len(df) >= 2:
        prev_close = df["close"].iloc[-2]
        current_close = df["close"].iloc[-1]
        drop_pct = (current_close - prev_close) / prev_close * 100
        if drop_pct <= config.crash_threshold:
            message = (
                f"銘柄 {code} 日足で {config.crash_threshold}%以上下落: "
                f"{prev_close:.1f} -> {current_close:.1f} ({drop_pct:.2f}%)"
            )
            logger.warning(message)
            from python.utils.alert import send_alert

            send_alert(message, level="WARNING")

    # --- MACD分析 ---
    if len(df) >= config.macd_long_period:  # MACD計算に必要な期間
        df = calculate_macd(df)
        # MACDゴールデンクロス/デッドクロスなどの分析ロジックをここに追加
        # 例: MACDがシグナルを上抜けた/下抜けた
        if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] <= df["macd_signal"].iloc[-2]:
            logger.info(f"銘柄 {code} MACDゴールデンクロス発生")
        elif df["macd"].iloc[-1] < df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] >= df["macd_signal"].iloc[-2]:
            logger.info(f"銘柄 {code} MACDデッドクロス発生")

    # --- ボリンジャーバンド分析 ---
    if len(df) >= config.bollinger_period:  # ボリンジャーバンド計算に必要な期間
        df = calculate_bollinger_bands(df)
        # ボリンジャーバンドのブレイクアウトなどの分析ロジックをここに追加
        # 例: 終値がアッパーバンドを上抜けた
        if df["close"].iloc[-1] > df["upper_band"].iloc[-1]:
            logger.info(f"銘柄 {code} ボリンジャーバンドのアッパーバンドを上抜け")
        elif df["close"].iloc[-1] < df["lower_band"].iloc[-1]:
            logger.info(f"銘柄 {code} ボリンジャーバンドのローワーバンドを下抜け")

    logger.info(f"銘柄 {code} の日足データ分析を完了")


if __name__ == "__main__":
    # 例: my_stock.csv に記載された全銘柄を分析
    stock_df = pd.read_csv(config.codes_path)
    codes = stock_df["code"].tolist()
    for code in codes:
        analyze_daily_data(code)
