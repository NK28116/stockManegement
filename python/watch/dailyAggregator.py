import sqlite3
import logging

# ログ出力の設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def save_data_to_db(data):
    try:
        conn = sqlite3.connect('stock_data.db')
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS stock_data (date TEXT, open REAL, high REAL, low REAL, close REAL)')
        c.execute('INSERT INTO stock_data VALUES (?, ?, ?, ?, ?)', (data.index[0], data['Open'][0], data['High'][0], data['Low'][0], data['Close'][0]))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"SQLite データベースへの接続とデータ保存に失敗しました: {e}")