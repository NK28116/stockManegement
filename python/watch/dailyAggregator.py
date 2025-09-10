# TODO: 分足から日足への自動集計機能が未実装です。日足データをDBに保存する関数はありますが、集計ロジックがありません。

import logging
import sqlite3

# ログ出力の設定
from python.utils.logger import get_logger

logger = get_logger("dailyAggregator", category="watch")

__all__ = ["save_data_to_db"]


def save_data_to_db(data):
    try:
        conn = sqlite3.connect("my_stock.db")
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS stock_data (date TEXT, open REAL, high REAL, low REAL, close REAL)")
        c.execute(
            "INSERT INTO stock_data VALUES (?, ?, ?, ?, ?)",
            (
                data.index[0],
                data["Open"][0],
                data["High"][0],
                data["Low"][0],
                data["Close"][0],
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"SQLite データベースへの接続とデータ保存に失敗しました: {e}")
