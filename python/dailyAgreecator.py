import sqlite3
from datetime import datetime

DB_PATH = "python/db/stock.db"

def aggregate_daily(code: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute("""
        SELECT MIN(price), MAX(price), 
               (SELECT price FROM intraday WHERE code=? AND DATE(timestamp)=? ORDER BY timestamp ASC LIMIT 1),
               (SELECT price FROM intraday WHERE code=? AND DATE(timestamp)=? ORDER BY timestamp DESC LIMIT 1)
        FROM intraday WHERE code=? AND DATE(timestamp)=?
    """, (code, today, code, today, code, today))
    row = cur.fetchone()

    if row and row[0]:
        low, high, open_, close = row
        cur.execute("INSERT OR REPLACE INTO daily (code, date, open, high, low, close) VALUES (?,?,?,?,?,?)",
                    (code, today, open_, high, low, close))
        conn.commit()
    conn.close()

if __name__ == "__main__":
    aggregate_daily("7203")