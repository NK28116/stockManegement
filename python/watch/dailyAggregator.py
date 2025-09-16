import sqlite3
from datetime import datetime, timedelta  # timedelta を追加

import pandas as pd

from python.config import config
from python.utils.logger import get_logger

logger = get_logger("dailyAggregator", category="watch")

DB_PATH = config.db_path

__all__ = ["save_daily_data_to_db", "aggregate_intraday_to_daily"]


def save_daily_data_to_db(code, date, open_price, high_price, low_price, close_price, volume):
    """日足データをDBに保存する"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS daily (
                code TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (code, date)
            )
        """
        )
        c.execute(
            "INSERT OR REPLACE INTO daily VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, date, open_price, high_price, low_price, close_price, volume),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"日足データのDB保存に失敗しました: {e}")
    finally:
        conn.close()


def aggregate_intraday_to_daily(target_date: str):
    """
    指定された日付の分足データから日足データを集計し、DBに保存する

    Args:
        target_date (str): 集計対象の日付 (YYYY-MM-DD形式)
    """
    logger.info(f"{target_date} の日足データを集計開始")
    conn = sqlite3.connect(DB_PATH)
    try:
        # その日の全銘柄の分足データを取得
        query = (
            f"SELECT code, timestamp, price, volume FROM intraday "
            f"WHERE DATE(timestamp) = '{target_date}' ORDER BY timestamp ASC"
        )
        df = pd.read_sql_query(query, conn)

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
            open_price = stock_df["price"].iloc[0]
            high_price = stock_df["price"].max()
            low_price = stock_df["price"].min()
            close_price = stock_df["price"].iloc[-1]
            total_volume = stock_df["volume"].sum()

            save_daily_data_to_db(code, target_date, open_price, high_price, low_price, close_price, total_volume)
            logger.info(f"銘柄 {code} の {target_date} 日足データを保存しました。")

    except Exception as e:
        logger.error(f"日足データ集計中にエラーが発生しました: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    # 例: 前日の日足データを集計
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    aggregate_intraday_to_daily(yesterday)
