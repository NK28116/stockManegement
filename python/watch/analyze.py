# TODO:現在、日足データに対する単純な急落検知（前日比-3%）のみで、リアルタイム監視の「数分で-3%」のような急落検知は `watch.py` の方が担当しています。
# `analyze.py` はリアルタイム監視の目標に対しては**未実装**です。

import logging
import sqlite3

from python.utils.logger import get_logger

logger = get_logger("analyze", category="watch")

__all__ = ["analyze_stock_data"]


def analyze_stock_data():
    try:
        conn = sqlite3.connect("stock_data.db")
        c = conn.cursor()
        c.execute("SELECT close FROM stock_data ORDER BY date DESC LIMIT 2")
        rows = c.fetchall()
        if len(rows) == 2:
            prev_close = rows[1][0]
            current_close = rows[0][0]
            if current_close < prev_close * 0.97:
                logging.warning(f"株価が -3% 以上下落しました: {current_close}")
        conn.close()
    except Exception as e:
        logging.error(f"SQLite データベースへの接続に失敗しました: {e}")
