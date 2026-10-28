# python/db/url.py
"""DB 接続 URL の組み立て (副作用なし)

`python/db/database.py` は import 時に SQLite のテーブル自動作成を行うため、
Alembic の env.py から import すると **マイグレーション実行前にテーブルが
出来上がってしまい** `alembic upgrade head` が失敗していた (PRIDEV-487)。

URL の組み立てだけを本モジュールへ切り出し、env.py はこちらを参照する。
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["build_database_url", "is_sqlite", "sqlite_path"]

DEFAULT_SQLITE_FILENAME = "test_stock.db"


def is_sqlite() -> bool:
    return os.getenv("DB_TYPE", "postgresql").lower() == "sqlite"


def sqlite_path() -> str:
    return os.getenv(
        "SQLITE_PATH",
        str(Path(__file__).resolve().parent.parent.parent / DEFAULT_SQLITE_FILENAME),
    )


def build_database_url() -> str:
    """DB_TYPE に応じた SQLAlchemy 接続 URL を返す。"""
    if is_sqlite():
        return f"sqlite:///{sqlite_path()}"

    from python.config import config

    db_conf = config.get_db_config()
    url = (
        f"postgresql://{db_conf.get('user', 'user')}:{db_conf.get('password', 'password')}@"
        f"{db_conf.get('host', 'localhost')}:{db_conf.get('port', '5432')}/"
        f"{db_conf.get('database', 'stock_db')}"
    )
    # インターネット越し（Render → GCE等）で接続する場合の SSL 指定。
    # CLOUD_PG_SSLMODE=require/verify-full などを指定すると付与される。
    sslmode = db_conf.get("sslmode")
    if sslmode:
        url += f"?sslmode={sslmode}"
    return url
