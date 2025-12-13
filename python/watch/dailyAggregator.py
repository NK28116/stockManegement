from datetime import datetime, timedelta  # timedelta を追加

import pandas as pd
from psycopg2 import Error as PgError

from python.db.database import get_db_connection
from python.utils.logger import get_logger

logger = get_logger("dailyAggregator", category="watch")

__all__ = ["save_daily_data_to_db", "aggregate_intraday_to_daily"]


def save_daily_data_to_db(
    code: str,
    date: str,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int,
):
    """日足データをDBに保存する"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_data (
                code TEXT,
                date DATE,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume INTEGER,
                PRIMARY KEY (code, date)
            )
        """
        )
        cur.execute(
            """
            INSERT INTO stock_data (code, date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code, date) DO UPDATE
            SET open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, volume = EXCLUDED.volume
            """,
            (code, date, open_price, high_price, low_price, close_price, volume),
        )
        conn.commit()
    except PgError as e:
        logger.error(f"日足データのDB保存に失敗しました: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def aggregate_intraday_to_daily(target_date: str, is_test_mode: bool = False):
    """
    指定された日付の分足データから日足データを集計し、DBに保存する

    Args:
        target_date (str): 集計対象の日付 (YYYY-MM-DD形式)
    """
    logger.info(f"{target_date} の日足データを集計開始")
    conn = None
    try:
        conn = get_db_connection()
        # その日の全銘柄の分足データを取得
        query = (
            "SELECT code, timestamp, price, volume FROM intraday "
            "WHERE timestamp::date = %s ORDER BY timestamp ASC"
        )
        df = pd.read_sql_query(query, conn, params=(target_date,))

        if df.empty:
            logger.warning(f"{target_date} の分足データが見つかりませんでした。")
            return

        # timestampをdatetimeオブジェクトに変換
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # 銘柄ごとに日足データを集計
        for code in df["code"].unique():
            stock_df = df[df["code"] == code].set_index("timestamp")
            if stock_df.empty:
                continue

            # 日足のOHLCVを計算
            open_price = float(stock_df["price"].iloc[0])
            high_price = float(stock_df["price"].max())
            low_price = float(stock_df["price"].min())
            close_price = float(stock_df["price"].iloc[-1])
            total_volume = int(stock_df["volume"].sum())  # numpy.int64をintに変換

            if not is_test_mode:
                save_daily_data_to_db(
                    code,
                    target_date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    total_volume,
                )
                logger.info(f"銘柄 {code} の {target_date} 日足データを保存しました。")
            else:
                logger.info(
                    f"テストモードのため、銘柄 {code} の {target_date} 日足データの保存はスキップします。"
                )

    except PgError as e:
        logger.error(f"日足データ集計中にエラーが発生しました: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # 例: 前日の日足データを集計
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    aggregate_intraday_to_daily(yesterday)
