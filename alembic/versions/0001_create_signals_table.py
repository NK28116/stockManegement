"""create signals table

Revision ID: 0001
Revises:
Create Date: 2026-02-21

"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("detected_patterns", sa.String(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("take_profit", sa.Float(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_signals_symbol"), "signals", ["symbol"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_signals_symbol"), table_name="signals")
    op.drop_table("signals")
