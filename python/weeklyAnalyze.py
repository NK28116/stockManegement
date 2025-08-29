import sqlite3
from datetime import datetime, timedelta
from utils.indicators import moving_average, rsi

DB_PATH = "python/db/stock.db"

def weekly_analysis(code: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 直近4週間分を取得
    cur.execute("SELECT date, close FROM daily WHERE code=? ORDER BY date DESC LIMIT 20", (code,))
    rows = cur.fetchall()
    if len(rows) < 5:
        return None

    closes = [r[1] for r in rows[::-1]]
    ma5 = moving_average(closes, 5)
    ma20 = moving_average(closes, 20)
    current_rsi = rsi(closes, 14)

    print(f"週次分析 {code}")
    print(f"MA5={ma5[-1]:.2f}, MA20={ma20[-1]:.2f}, RSI14={current_rsi:.2f}")

    conn.close()

if __name__ == "__main__":
    weekly_analysis("7203")