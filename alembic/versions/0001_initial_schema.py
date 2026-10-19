"""initial schema: logs + llm_cache

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("reviewed_label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_logs_source", "logs", ["source"])
    op.create_index("ix_logs_label", "logs", ["label"])
    op.create_index("ix_logs_tier", "logs", ["tier"])
    op.create_table(
        "llm_cache",
        sa.Column("key", sa.String(600), primary_key=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("llm_cache")
    op.drop_index("ix_logs_tier", table_name="logs")
    op.drop_index("ix_logs_label", table_name="logs")
    op.drop_index("ix_logs_source", table_name="logs")
    op.drop_table("logs")
