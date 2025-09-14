"""
データベース初期化スクリプト
重複を解消し、統一されたデータベース構造を作成
"""

import os
import shutil
import sqlite3

from python.config import config


def init_database():
    """データベースを初期化"""

    # メインのデータベースパス
    main_db_path = config.db_path

    # 重複ディレクトリの確認と削除
    duplicate_path = os.path.join(os.path.dirname(__file__), "python/db")
    if os.path.exists(duplicate_path):
        print("重複ディレクトリを削除中: {duplicate_path}")
        shutil.rmtree(duplicate_path)

    # メインのDBディレクトリを作成
    db_dir = os.path.dirname(main_db_path)
    os.makedirs(db_dir, exist_ok=True)

    # データベース接続とテーブル作成
    conn = sqlite3.connect(main_db_path)
    cur = conn.cursor()

    # 基本テーブルの作成
    tables = [
        # 分足
        """
        CREATE TABLE IF NOT EXISTS intraday (
            code TEXT,
            timestamp DATETIME,
            price REAL,
            volume INTEGER,
            PRIMARY KEY (code, timestamp)
        )
        """,
        # 日足
        # 日次評価・損益記録
        """
        CREATE TABLE IF NOT EXISTS daily (
            code TEXT,
            date DATE,
            price REAL,                  -- 当日の株価
            market_value REAL,           -- 評価額
            unrealized_pl REAL,          -- 含み損益
            realized_pl REAL DEFAULT 0,  -- 実現損益（売却があった場合のみ）
            action TEXT DEFAULT 'HOLD',  -- その日のアクション ('BUY','SELL','HOLD')
            trade_quantity REAL DEFAULT 0, -- 売買数量
            trade_price REAL,            -- 売買価格
            PRIMARY KEY (code, date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS pre_buy_daily(
            code TEXT,
            date DATE,
            name TEXT,
            quantity INTEGER,
            target_price REAL,
            planned_date DATE,
            sector TEXT,
            status TEXT DEFAULT '購入予定',
            PRIMARY KEY (code, date)
        )
        """,
        # 収支
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
        """,
        # 保持株式
        """
        CREATE TABLE IF NOT EXISTS stock_data (
            code TEXT,
            date DATE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (code,date)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT
        )
        """,
        # 保有株式の全期間の変異
        """
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_name TEXT,
            code TEXT,
            quantity INTEGER,
            purchase_price REAL,
            purchase_date DATE,
            FOREIGN KEY (code) REFERENCES stocks(code)
        )
        """,
        """
CREATE TABLE IF NOT EXISTS trading_signals (
    code TEXT,
    signal_date DATE,
    signal_type TEXT, -- 'BUY', 'SELL', 'HOLD' など
    price REAL,
    reason TEXT,
    PRIMARY KEY (code, signal_date)
)
""",
    ]

    for table_sql in tables:
        cur.execute(table_sql)

    # インデックスの作成
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_intraday_code_date ON intraday(code, DATE(timestamp))",
        "CREATE INDEX IF NOT EXISTS idx_daily_code_date ON daily(code, date)",
        "CREATE INDEX IF NOT EXISTS idx_sample_daily_code_date ON pre_buy_daily(code, date)",
        "CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_portfolio_name ON portfolio_holdings(portfolio_name)",
        "CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_code ON portfolio_holdings(code)",
    ]

    for index_sql in indexes:
        cur.execute(index_sql)

    conn.commit()
    conn.close()

    print("データベース初期化完了: {main_db_path}")
    print("作成されたテーブル:")
    print("- intraday (分足データ)")
    print("- daily (保有中の銘柄データ)")
    print("- pre_buy_daily(購入予定の銘柄データ)")
    print("- portfolio (ポートフォリオ情報)")
    print("- stocks (銘柄情報)")
    print("- portfolio_holdings (ポートフォリオ保有銘柄)")


def check_database_status():
    """データベースの状態を確認"""

    main_db_path = os.path.join(os.path.dirname(__file__), "db/my_stock.db")

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
            cur.execute("SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print("  - {table}: {count}件")

        conn.close()
        return True

    except Exception as e:
        print("❌ データベース確認エラー: {e}")
        return False


if __name__ == "__main__":
    print("データベース初期化開始...")
    init_database()
    print("\nデータベース状態確認...")
    check_database_status()
