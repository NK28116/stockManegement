import psycopg2
from psycopg2 import Error as PgError

from python.config import config


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
        print(f"❌ データベース接続エラー: {e}")
        raise
