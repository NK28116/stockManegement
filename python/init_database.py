"""
データベース初期化スクリプト
重複を解消し、統一されたデータベース構造を作成
"""

import sqlite3
import os
import shutil
from datetime import datetime

def init_database():
    """データベースを初期化"""
    
    # メインのデータベースパス
    main_db_path = os.path.join(os.path.dirname(__file__), "db/stock.db")
    
    # 重複ディレクトリの確認と削除
    duplicate_path = os.path.join(os.path.dirname(__file__), "python/db")
    if os.path.exists(duplicate_path):
        print(f"重複ディレクトリを削除中: {duplicate_path}")
        shutil.rmtree(duplicate_path)
    
    # メインのDBディレクトリを作成
    db_dir = os.path.dirname(main_db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    # データベース接続とテーブル作成
    conn = sqlite3.connect(main_db_path)
    cur = conn.cursor()
    
    # 基本テーブルの作成
    tables = [
        """
        CREATE TABLE IF NOT EXISTS intraday (
            code TEXT,
            timestamp DATETIME,
            price REAL,
            volume INTEGER,
            PRIMARY KEY (code, timestamp)
        )
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS sample_daily (
            code TEXT,
            date DATE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (code, date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS portfolio (
            code TEXT,
            name TEXT,
            quantity INTEGER,
            purchase_price REAL,
            purchase_date DATE,
            sector TEXT,
            weight REAL DEFAULT 0.0,
            PRIMARY KEY (code)
        )
        """
    ]
    
    for table_sql in tables:
        cur.execute(table_sql)
    
    # インデックスの作成
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_intraday_code_date ON intraday(code, DATE(timestamp))",
        "CREATE INDEX IF NOT EXISTS idx_daily_code_date ON daily(code, date)",
        "CREATE INDEX IF NOT EXISTS idx_sample_daily_code_date ON sample_daily(code, date)"
    ]
    
    for index_sql in indexes:
        cur.execute(index_sql)
    
    conn.commit()
    conn.close()
    
    print(f"データベース初期化完了: {main_db_path}")
    print("作成されたテーブル:")
    print("- intraday (分足データ)")
    print("- daily (日足データ)")
    print("- sample_daily (サンプル日足データ)")
    print("- portfolio (ポートフォリオ情報)")

def check_database_status():
    """データベースの状態を確認"""
    
    main_db_path = os.path.join(os.path.dirname(__file__), "db/stock.db")
    
    if not os.path.exists(main_db_path):
        print("❌ メインデータベースが見つかりません")
        return False
    
    # 重複ディレクトリの確認
    duplicate_path = os.path.join(os.path.dirname(__file__), "python/db")
    if os.path.exists(duplicate_path):
        print("❌ 重複ディレクトリが残っています")
        return False
    
    # データベースの内容確認
    try:
        conn = sqlite3.connect(main_db_path)
        cur = conn.cursor()
        
        # テーブル一覧を取得
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        
        print("✅ データベース構造:")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  - {table}: {count}件")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ データベース確認エラー: {e}")
        return False

if __name__ == "__main__":
    print("データベース初期化開始...")
    init_database()
    print("\nデータベース状態確認...")
    check_database_status()
