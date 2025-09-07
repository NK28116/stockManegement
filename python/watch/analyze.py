import sqlite3
import logging

# ログ出力の設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_stock_data():
    try:
        conn = sqlite3.connect('stock_data.db')
        c = conn.cursor()
        c.execute('SELECT close FROM stock_data ORDER BY date DESC LIMIT 2')
        rows = c.fetchall()
        if len(rows) == 2:
            prev_close = rows[1][0]
            current_close = rows[0][0]
            if current_close < prev_close * 0.97:
                logging.warning(f"株価が -3% 以上下落しました: {current_close}")
        conn.close()
    except Exception as e:
        logging.error(f"SQLite データベースへの接続に失敗しました: {e}")