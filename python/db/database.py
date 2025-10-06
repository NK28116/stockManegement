import logging

import pandas as pd # 追加
import psycopg2
from psycopg2 import Error as PgError
from psycopg2.extras import execute_values

from python.config import config

logger = logging.getLogger(__name__)


def get_db_connection():
    """
    PostgreSQLデータベースへの接続を確立し、接続オブジェクトを返す。
    """
    conn = None
    try:
        db_config = config.get_db_config()
        conn = psycopg2.connect(**db_config)
        return conn
    except PgError as e:
        logger.error(f"❌ データベース接続エラー: {e}")
        raise


def create_portfolio_table():
    """
    portfolioテーブルを作成する。
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                code TEXT NOT NULL,
                name TEXT,
                quantity INTEGER,
                purchase_price REAL,
                purchase_date DATE NOT NULL,
                status TEXT,
                current_price REAL,
                profit_loss REAL,
                profit_loss_percent TEXT,
                last_updated TIMESTAMP,
                purpose TEXT,
                PRIMARY KEY (code, purchase_date)
            )
            """
        )
        conn.commit()
        logger.info("✅ portfolioテーブルが正常に作成または既に存在します。")
    except PgError as e:
        logger.error(f"❌ portfolioテーブル作成エラー: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_portfolio_data():
    """
    portfolioテーブルからすべてのデータを取得する。
    """
    conn = None
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM portfolio ORDER BY code, purchase_date", conn)
        return df
    except PgError as e:
        logger.error(f"❌ portfolioデータ取得エラー: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def upsert_portfolio_data(data):
    """
    my_stock.csvから読み込んだデータをportfolioテーブルに挿入または更新する。
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # データをタプルのリストに変換
        values = [
            (
                row["code"],
                row["name"],
                row["quantity"],
                row["purchase_price"],
                row[
                    "purchase_date"
                ],  # CSVから読み込んだ日付文字列がそのまま入ることを想定。psycopg2が自動変換
                row["status"],
                row["current_price"],
                row["profit_loss"],
                row["profit_loss_percent"],
                row["last_updated"],  # CSVから読み込んだタイムスタンプ文字列がそのまま入ることを想定
                row["purpose"],
            )
            for row in data
        ]

        # ON CONFLICT DO UPDATE を使用して挿入または更新
        execute_values(
            cur,
            """
            INSERT INTO portfolio (
                code, name, quantity, purchase_price, purchase_date,
                status, current_price, profit_loss, profit_loss_percent,
                last_updated, purpose
            ) VALUES %s
            ON CONFLICT (code, purchase_date) DO UPDATE SET
                name = EXCLUDED.name,
                quantity = EXCLUDED.quantity,
                purchase_price = EXCLUDED.purchase_price,
                status = EXCLUDED.status,
                current_price = EXCLUDED.current_price,
                profit_loss = EXCLUDED.profit_loss,
                profit_loss_percent = EXCLUDED.profit_loss_percent,
                last_updated = EXCLUDED.last_updated,
                purpose = EXCLUDED.purpose
            """,
            values,
        )
        conn.commit()
        logger.info("✅ portfolioデータが正常に挿入または更新されました。")
    except PgError as e:
        logger.error(f"❌ portfolioデータ挿入/更新エラー: {e}")
        raise
    finally:
        if conn:
            conn.close()
