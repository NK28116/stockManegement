import logging
import os
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, delete, update
from sqlalchemy.orm import sessionmaker

from python.config import config

# 全モデルをインポートして Base.metadata に登録する（create_all に必要）
from python.db.models import (
    Base,
    DailyPrice,
    Portfolio,
    Signal,
    SignalHistory,
    Stock,
    StockNote,
    Watchlist,
)

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
    engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
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
    # インターネット越し（Render → GCE等）で接続する場合のSSL指定。
    # CLOUD_PG_SSLMODE=require/verify-full などを指定すると付与される。
    sslmode = db_conf.get("sslmode")
    if sslmode:
        DATABASE_URL += f"?sslmode={sslmode}"
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

                stmt = (
                    sqlite_insert(Portfolio)
                    .values(
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
                    .on_conflict_do_update(
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


def _clean_portfolio_row(row: dict) -> dict:
    """
    CSVから読み込んだ1行を DB 挿入前にクリーニングする。
    - profit_loss_percent の "%" 文字列を除去して float に変換
    - None/NaN はそのまま None に統一
    """
    cleaned = dict(row)
    pct = cleaned.get("profit_loss_percent")
    if pct is not None and pct != "" and pct is not float:
        try:
            cleaned["profit_loss_percent"] = float(str(pct).replace("%", "").strip())
        except (ValueError, TypeError):
            cleaned["profit_loss_percent"] = None
    return cleaned


def sync_csv_to_portfolio() -> None:
    """
    config.codes_path のCSVを読み込み、portfolioテーブルへ全量 Upsert する。
    - profit_loss_percent の「%」文字列を自動除去（PostgreSQL Numeric 型対応）
    - NaN 値は None(NULL)に変換
    """
    csv_path = config.codes_path
    if not Path(csv_path).exists():
        logger.warning(f"sync_csv_to_portfolio: CSVが見つかりません: {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
        # NaN → None に統一
        df = df.where(pd.notnull(df), None)
        records = [_clean_portfolio_row(r) for r in df.to_dict("records")]
        upsert_portfolio_data(records)
        logger.info(f"✅ sync_csv_to_portfolio: {len(records)} 件を同期しました ({csv_path})")
    except Exception as e:
        logger.error(f"❌ sync_csv_to_portfolio エラー: {e}", exc_info=True)


def delete_portfolio_record(code: str) -> None:
    """
    portfolioテーブルから指定コードの全レコードを削除する。
    delete_stock() 呼び出し後に CSV との一貫性を保つために使用する。
    """
    try:
        with get_db_session() as session:
            stmt = delete(Portfolio).where(Portfolio.code == code)
            result = session.execute(stmt)
            session.commit()
            logger.info(f"✅ delete_portfolio_record: {code} を削除しました ({result.rowcount} 件)")
    except Exception as e:
        logger.error(f"❌ delete_portfolio_record エラー ({code}): {e}", exc_info=True)


def update_portfolio_status(code: str, status: str, quantity: int = 0) -> None:
    """
    portfolioテーブルの指定コードのステータスと数量を更新する。
    sell_stock() 呼び出し後に CSV との一貫性を保つために使用する。
    """
    try:
        with get_db_session() as session:
            stmt = update(Portfolio).where(Portfolio.code == code).values(status=status, quantity=quantity)
            result = session.execute(stmt)
            session.commit()
            logger.info(
                f"✅ update_portfolio_status: {code} を status={status}, quantity={quantity} に更新しました "
                f"({result.rowcount} 件)"
            )
    except Exception as e:
        logger.error(f"❌ update_portfolio_status エラー ({code}): {e}", exc_info=True)


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
