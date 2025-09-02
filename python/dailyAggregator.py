import sqlite3
import os
from datetime import datetime
from typing import Optional, Tuple

# データベースパスを統一
DB_PATH = os.path.join(os.path.dirname(__file__), "db/stock.db")

def aggregate_daily(code: str) -> bool:
    """
    分足データを日足データに集計する
    
    Args:
        code: 証券コード
        
    Returns:
        bool: 集計が成功したかどうか
    """
    try:
        # DBディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # テーブルが存在しない場合は作成
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intraday (
                code TEXT,
                timestamp DATETIME,
                price REAL,
                volume INTEGER
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily (
                code TEXT,
                date DATE,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (code, date)
            )
        """)

        today = datetime.now().strftime("%Y-%m-%d")
        
        # データが存在するかチェック
        cur.execute("SELECT COUNT(*) FROM intraday WHERE code=? AND DATE(timestamp)=?", (code, today))
        if cur.fetchone()[0] == 0:
            print(f"警告: {code}の{today}の分足データが見つかりません")
            conn.close()
            return False
        
        cur.execute("""
            SELECT MIN(price), MAX(price), 
                   (SELECT price FROM intraday WHERE code=? AND DATE(timestamp)=? ORDER BY timestamp ASC LIMIT 1),
                   (SELECT price FROM intraday WHERE code=? AND DATE(timestamp)=? ORDER BY timestamp DESC LIMIT 1),
                   SUM(volume)
            FROM intraday WHERE code=? AND DATE(timestamp)=?
        """, (code, today, code, today, code, today))
        
        row = cur.fetchone()

        if row and row[0] is not None:
            low, high, open_, close, volume = row
            cur.execute("""
                INSERT OR REPLACE INTO daily (code, date, open, high, low, close, volume) 
                VALUES (?,?,?,?,?,?,?)
            """, (code, today, open_, high, low, close, volume))
            conn.commit()
            print(f"{code}の{today}の日足データを集計しました")
            return True
        else:
            print(f"警告: {code}の{today}のデータが不完全です")
            return False
            
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")
        return False
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = aggregate_daily("7203")
    if success:
        print("集計完了")
    else:
        print("集計失敗")
