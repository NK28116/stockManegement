import sqlite3
import os
import shutil
from datetime import datetime

def init_database():
    """データベース初期化（新スキーマ対応）"""
    
    db_path = os.path.join(os.path.dirname(__file__), "db/stock.db")
    
    # 重複ディレクトリ削除
    duplicate_path = os.path.join(os.path.dirname(__file__), "python/db")
    if os.path.exists(duplicate_path):
        print(f"重複ディレクトリを削除中: {duplicate_path}")
        shutil.rmtree(duplicate_path)
    
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 外部キー有効化
    cur.execute("PRAGMA foreign_keys = ON;")
    
    # テーブル作成
    tables = [
        # 株式基本情報
        """
        CREATE TABLE IF NOT EXISTS stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # 株価データ
        """
        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            date DATE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(code) REFERENCES stocks(code)
        )
        """,
        # ポートフォリオ保有情報
        """
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            quantity INTEGER,
            purchase_price REAL,
            purchase_date DATE,
            portfolio_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(code) REFERENCES stocks(code)
        )
        """,
        # 売買シグナル
        """
        CREATE TABLE IF NOT EXISTS trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            signal_date DATE,
            signal_type TEXT,
            price REAL,
            reason TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(code) REFERENCES stocks(code)
        )
        """
    ]
    
    for sql in tables:
        cur.execute(sql)
    
    # インデックス作成
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_stock_prices_code_date ON stock_prices(code, date)",
        "CREATE INDEX IF NOT EXISTS idx_portfolio_code_name ON portfolio_holdings(code, portfolio_name)",
        "CREATE INDEX IF NOT EXISTS idx_signals_code_date ON trading_signals(code, signal_date)"
    ]
    
    for idx in indexes:
        cur.execute(idx)
    
    conn.commit()
    conn.close()
    
    print(f"✅ データベース初期化完了: {db_path}")

def check_database_status():
    """データベース状態確認"""
    db_path = os.path.join(os.path.dirname(__file__), "db/stock.db")
    
    if not os.path.exists(db_path):
        print("❌ データベースが存在しません")
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    
    print("✅ データベース構造:")
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  - {table}: {count}件")
    
    conn.close()
    return True

if __name__ == "__main__":
    print("データベース初期化開始...")
    init_database()
    print("\nデータベース状態確認...")
    check_database_status()