import logging
from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from python.config import config
from python.db.models import Base, Portfolio

logger = logging.getLogger(__name__)

# SQLAlchemy Engine 作成
# config.get_db_config() が dict を返すと仮定して URL を構築
# 実際には config 側で DATABASE_URL を返すのが一般的ですが、ここでは dict から構築します
db_conf = config.get_db_config()
DATABASE_URL = (
    f"postgresql://{db_conf.get('user', 'user')}:{db_conf.get('password', 'password')}@"
    f"{db_conf.get('host', 'localhost')}:{db_conf.get('port', '5432')}/{db_conf.get('dbname', 'stock_db')}"
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
    SQLAlchemy Core の upsert 機能を使用。
    """
    with get_db_session() as session:
        for row in data:
            # PostgreSQL特有の Upsert 構文 (INSERT ... ON CONFLICT DO UPDATE)
            stmt = insert(Portfolio).values(
                code=row["code"],
                name=row["name"],
                quantity=row["quantity"],
                purchase_price=row["purchase_price"],
                purchase_date=row["purchase_date"],
                status=row["status"],
                current_price=row["current_price"],
                profit_loss=row["profit_loss"],
                profit_loss_percent=row[
                    "profit_loss_percent"
                ],  # 数値型に変換されている前提
                last_updated=row["last_updated"],
                purpose=row["purpose"],
            )

            # code と purchase_date が重複したら更新
            # 注意: models.py で UniqueConstraint('code', 'purchase_date') が定義されている必要があります
            do_update_stmt = stmt.on_conflict_do_update(
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

            session.execute(do_update_stmt)

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
