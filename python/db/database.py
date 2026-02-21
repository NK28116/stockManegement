import logging
import os
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from python.config import config
# 全モデルをインポートして Base.metadata に登録する（create_all に必要）
from python.db.models import Base, DailyPrice, Portfolio, Signal, SignalHistory, Stock

logger = logging.getLogger(__name__)

# SQLAlchemy Engine 作成
# DB_TYPE=sqlite の場合はローカル SQLite を使用し、それ以外は PostgreSQL を使用する
_db_type = os.getenv("DB_TYPE", "postgresql").lower()

if _db_type == "sqlite":
    _sqlite_path = os.getenv(
        "SQLITE_PATH",
        str(Path(__file__).resolve().parent.parent.parent / "test_stock.db"),
    )
    DATABASE_URL = f"sqlite:///{_sqlite_path}"
    engine = create_engine(
        DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
    )
    logger.info(f"SQLite モードで起動: {_sqlite_path}")
    # SQLite 環境では Alembic マイグレーションを使わないため、
    # エンジン生成直後に全テーブルを自動作成する
    Base.metadata.create_all(bind=engine)
    logger.info("SQLite: テーブル自動作成完了 (create_all)")
else:
    # config.get_db_config() のキーは 'database' (dbname ではない)
    db_conf = config.get_db_config()
    DATABASE_URL = (
        f"postgresql://{db_conf.get('user', 'user')}:{db_conf.get('password', 'password')}@"
        f"{db_conf.get('host', 'localhost')}:{db_conf.get('port', '5432')}/{db_conf.get('database', 'stock_db')}"
    )
    engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    テーブル作成（初回のみ使用、通常はAlembicを使う）
    """
    Base.metadata.create_all(bind=engine)
    logger.info("✅ データベーステーブルの初期化完了")


@contextmanager
def get_db_session():
    """
    DBセッションを提供するコンテキストマネージャ
    with get_db_session() as session: で使用
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def get_portfolio_data() -> pd.DataFrame:
    """
    portfolioテーブルからすべてのデータを取得し、DataFrameで返す。
    """
    query = "SELECT * FROM portfolio ORDER BY code, purchase_date"
    try:
        # pandas の read_sql は SQLAlchemy engine を受け取れる
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        logger.error(f"❌ portfolioデータ取得エラー: {e}")
        return pd.DataFrame()


def upsert_portfolio_data(data: list[dict]):
    """
    my_stock.csvから読み込んだデータをportfolioテーブルに挿入または更新する。
    DB_TYPE に応じて PostgreSQL / SQLite のどちらでも動作する。
    """
    with get_db_session() as session:
        for row in data:
            if _db_type == "sqlite":
                # SQLite: INSERT OR REPLACE を利用
                from sqlalchemy.dialects.sqlite import insert as sqlite_insert

                stmt = sqlite_insert(Portfolio).values(
                    code=row["code"],
                    name=row["name"],
                    quantity=row["quantity"],
                    purchase_price=row["purchase_price"],
                    purchase_date=row["purchase_date"],
                    status=row["status"],
                    current_price=row["current_price"],
                    profit_loss=row["profit_loss"],
                    profit_loss_percent=row["profit_loss_percent"],
                    last_updated=row["last_updated"],
                    purpose=row["purpose"],
                ).on_conflict_do_update(
                    index_elements=["code", "purchase_date"],
                    set_={
                        "name": row["name"],
                        "quantity": row["quantity"],
                        "purchase_price": row["purchase_price"],
                        "status": row["status"],
                        "current_price": row["current_price"],
                        "profit_loss": row["profit_loss"],
                        "profit_loss_percent": row["profit_loss_percent"],
                        "last_updated": row["last_updated"],
                        "purpose": row["purpose"],
                    },
                )
            else:
                # PostgreSQL: INSERT ... ON CONFLICT DO UPDATE
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                stmt = pg_insert(Portfolio).values(
                    code=row["code"],
                    name=row["name"],
                    quantity=row["quantity"],
                    purchase_price=row["purchase_price"],
                    purchase_date=row["purchase_date"],
                    status=row["status"],
                    current_price=row["current_price"],
                    profit_loss=row["profit_loss"],
                    profit_loss_percent=row["profit_loss_percent"],
                    last_updated=row["last_updated"],
                    purpose=row["purpose"],
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uix_portfolio_code_date",
                    set_={
                        "name": stmt.excluded.name,
                        "quantity": stmt.excluded.quantity,
                        "purchase_price": stmt.excluded.purchase_price,
                        "status": stmt.excluded.status,
                        "current_price": stmt.excluded.current_price,
                        "profit_loss": stmt.excluded.profit_loss,
                        "profit_loss_percent": stmt.excluded.profit_loss_percent,
                        "last_updated": stmt.excluded.last_updated,
                        "purpose": stmt.excluded.purpose,
                    },
                )

            session.execute(stmt)

        session.commit()
        logger.info(f"✅ {len(data)} 件のportfolioデータを処理しました。")


def get_db_connection():
    """
    旧コード互換用: DB接続を返す
    """
    return engine.connect()


def create_portfolio_table():
    """
    旧コード互換用: ポートフォリオテーブル作成
    現在は init_db() で一括作成されるため、それを呼び出す
    """
    init_db()
