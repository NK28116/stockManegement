import sqlite3
from datetime import datetime
from utils.indicators import moving_average
from utils.alert import send_alert

DB_PATH = "python/db/stock.db"

import sqlite3

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # intraday（分足用）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS intraday (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            timestamp TEXT,
            price REAL
        )
    """)
    # daily（日足用）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL
        )
    """)
    # weekly（週足用）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            week_start TEXT,
            week_end TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL
        )
    """)
    conn.commit()
    conn.close()


def monitor_and_trade(code: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 最新の分足データを取得
    cur.execute("SELECT timestamp, price FROM intraday WHERE code=? ORDER BY timestamp DESC LIMIT 3", (code,))
    rows = cur.fetchall()
    if len(rows) < 3:
        return
    
    prices = [r[1] for r in rows[::-1]]  # 古い順に並べ替え
    signals = []

    for i in range(1, len(prices)):
        if prices[i] > prices[i-1]:
            signals.append("+")
        elif prices[i] < prices[i-1]:
            signals.append("-")

    decision = None
    if signals == ["+", "+"]:
        decision = "BUY"
    elif signals == ["+", "-"]:
        decision = "HOLD"
    elif signals == ["-", "-"]:
        decision = "SELL"

    if decision:
        send_alert(f"{datetime.now()} {code}: {decision} {prices[-1]}")
    conn.close()

if __name__ == "__main__":
    init_db()
    monitor_and_trade("7203")  # トヨタの例


