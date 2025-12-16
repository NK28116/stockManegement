import os
import sys

from sqlalchemy import create_engine

# プロジェクトルートへのパスを通す（モジュール読み込み用）
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from python.database.models import Base  # noqa: E402

# 環境変数から接続情報を取得 (デフォルトはローカルDocker用)
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "stock_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def init_db():
    print(f"Connecting to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    try:
        engine = create_engine(DATABASE_URL)
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")


if __name__ == "__main__":
    init_db()
