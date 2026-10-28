"""bring legacy tables under migration control

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-25

portfolio / stocks / daily_prices / signal_history は init_db() の
Base.metadata.create_all() でのみ作られており、マイグレーション履歴に
存在しなかった。そのため新規 DB へ `alembic upgrade head` を実行しても
これらのテーブルが作られず、実スキーマと履歴がズレていた (PRIDEV-487)。

本リビジョンは **存在しないテーブルだけ** を作成する。既存 DB では
何も行わないため、破壊的な再作成は発生しない。
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# 履歴に載っていなかったテーブル。定義はモデルを単一の正として参照する。
LEGACY_TABLES = ("portfolio", "stocks", "daily_prices", "signal_history")


def _missing_tables(connection) -> list:
    inspector = sa.inspect(connection)
    present = set(inspector.get_table_names())
    return [name for name in LEGACY_TABLES if name not in present]


def upgrade() -> None:
    from python.db.models import Base

    connection = op.get_bind()
    missing = _missing_tables(connection)
    if not missing:
        # 既存 DB: すべて存在するので何もしない
        return

    Base.metadata.create_all(
        bind=connection,
        tables=[Base.metadata.tables[name] for name in missing],
        checkfirst=True,
    )


def downgrade() -> None:
    # 既存データを持つテーブルのため、履歴登録の巻き戻しでは削除しない。
    # (誤操作によるデータ消失を防ぐ。削除が必要な場合は手動で行う)
    pass
