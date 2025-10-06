"""
データベース初期化スクリプト
重複を解消し、統一されたデータベース構造を作成
"""

import logging

import psycopg2
from psycopg2 import Error as PgError

from python.config import config
from python.db.database import create_portfolio_table  # 新しく追加した関数をインポート

logger = logging.getLogger(__name__)


def init_database():
    """データベースを初期化"""
    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        # 既存のportfolioテーブルを削除（スキーマ変更を確実に適用するため）
        cur.execute("DROP TABLE IF EXISTS portfolio CASCADE;")
        logger.info("✅ 既存のportfolioテーブルを削除しました。")

        # 基本テーブルの作成
        tables = [
            # 分足
            """
            CREATE TABLE IF NOT EXISTS intraday (
                code TEXT,
                timestamp TIMESTAMP,
                price DOUBLE PRECISION,
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
                price DOUBLE PRECISION,                  -- 当日の株価
                market_value DOUBLE PRECISION,           -- 評価額
                unrealized_pl DOUBLE PRECISION,          -- 含み損益
                realized_pl DOUBLE PRECISION DEFAULT 0,  -- 実現損益（売却があった場合のみ）
                action TEXT DEFAULT 'HOLD',  -- その日のアクション ('BUY','SELL','HOLD')
                trade_quantity DOUBLE PRECISION DEFAULT 0, -- 売買数量
                trade_price DOUBLE PRECISION,            -- 売買価格
                PRIMARY KEY (code, date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS pre_buy_daily(
                code TEXT,
                date DATE,
                name TEXT,
                quantity INTEGER,
                target_price DOUBLE PRECISION,
                planned_date DATE,
                purpose TEXT,
                status TEXT DEFAULT '監視中',
                PRIMARY KEY (code, date)
            )
            """,
            # 保持株式
            """
            CREATE TABLE IF NOT EXISTS stock_data (
                code TEXT,
                date DATE,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (code,date)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS stocks (
                code TEXT PRIMARY KEY,
                name TEXT,
                purpose TEXT
            )
            """,
            # 保有株式の全期間の変異
            """
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                id SERIAL PRIMARY KEY,
                portfolio_name TEXT,
                code TEXT,
                quantity INTEGER,
                purchase_price DOUBLE PRECISION,
                purchase_date DATE,
                FOREIGN KEY (code) REFERENCES stocks(code)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                code TEXT NOT NULL,
                trade_type TEXT NOT NULL, -- 'buy' or 'sell'
                quantity INTEGER NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                trade_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code) REFERENCES stocks(code)
            )
            """,
            """
CREATE TABLE IF NOT EXISTS trading_signals (
    code TEXT,
    signal_date DATE,
    signal_type TEXT, -- 'BUY', 'SELL', 'HOLD' など
    price DOUBLE PRECISION,
    reason TEXT,
    PRIMARY KEY (code, signal_date)
)
""",
        ]

        for table_sql in tables:
            cur.execute(table_sql)

        # 新しいportfolioテーブルを作成
        create_portfolio_table()

        # 既存テーブルのカラム名を変更 (sector -> purpose)
        alter_column_sqls = [
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='stocks' AND column_name='sector') THEN
                    ALTER TABLE stocks RENAME COLUMN sector TO purpose;
                    RAISE NOTICE 'Column "sector" in table "stocks" renamed to "purpose".';
                END IF;
            END $$;
            """,
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='pre_buy_daily' AND column_name='sector') THEN
                    ALTER TABLE pre_buy_daily RENAME COLUMN sector TO purpose;
                    RAISE NOTICE 'Column "sector" in table "pre_buy_daily" renamed to "purpose".';
                END IF;
            END $$;
            """,
        ]

        for alter_sql in alter_column_sqls:
            cur.execute(alter_sql)

        # インデックスの作成
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_intraday_code_date ON intraday(code, CAST(timestamp AS DATE))",
            "CREATE INDEX IF NOT EXISTS idx_daily_code_date ON daily(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_sample_daily_code_date ON pre_buy_daily(code, date)",
            "CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_portfolio_name ON portfolio_holdings(portfolio_name)",
            "CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_code ON portfolio_holdings(code)",
        ]

        for index_sql in indexes:
            cur.execute(index_sql)

        conn.commit()
        logger.info(f"データベース初期化完了: {db_config['database']} on {db_config['host']}")
        logger.info("作成されたテーブル:")
        logger.info("- intraday (分足データ)")
        logger.info("- daily (保有中の銘柄データ)")
        logger.info("- pre_buy_daily(監視中の銘柄データ)")
        logger.info("- portfolio (ポートフォリオ情報 - my_stock.csvと同期)")
        logger.info("- stocks (銘柄情報)")
        logger.info("- portfolio_holdings (ポートフォリオ保有銘柄)")

    except PgError as e:
        logger.error(f"❌ データベース初期化エラー: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def check_database_status():
    """データベースの状態を確認"""

    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        # テーブル一覧を取得 (PostgreSQLの場合)
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cur.fetchall()]

        if not tables:
            logger.warning("❌ データベースにテーブルが見つかりません")
            return False

        logger.info("✅ データベース構造:")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            logger.info(f"  - {table}: {count}件")

        conn.close()
        return True

    except PgError as e:
        logger.error(f"❌ データベース確認エラー: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO) # ロギング設定を追加

    logger.info("データベース初期化開始...")
    init_database()
    logger.info("\nデータベース状態確認...")
    check_database_status()
