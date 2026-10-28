"""add watchlist and stock_notes tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-23

"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_watchlist_code"),
    )
    op.create_index(op.f("ix_watchlist_code"), "watchlist", ["code"], unique=False)

    op.create_table(
        "stock_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_notes_code"), "stock_notes", ["code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_notes_code"), table_name="stock_notes")
    op.drop_table("stock_notes")
    op.drop_index(op.f("ix_watchlist_code"), table_name="watchlist")
    op.drop_table("watchlist")
