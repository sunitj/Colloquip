"""Phase 5: Add cross-reference and outcome tracking tables.

Revision ID: 004
Revises: 003
Create Date: 2026-02-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cross_references",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_memory_id",
            sa.String(36),
            sa.ForeignKey("synthesis_memories.id"),
            nullable=False,
        ),
        sa.Column(
            "target_memory_id",
            sa.String(36),
            sa.ForeignKey("synthesis_memories.id"),
            nullable=False,
        ),
        sa.Column("source_subreddit_id", sa.String(36), nullable=False),
        sa.Column("target_subreddit_id", sa.String(36), nullable=False),
        sa.Column("source_subreddit_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("target_subreddit_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("similarity", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("shared_entities", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("reasoning", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_crossref_source", "cross_references", ["source_memory_id"])
    op.create_index("idx_crossref_target", "cross_references", ["target_memory_id"])

    op.create_table(
        "outcome_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thread_id", sa.String(36), nullable=False),
        sa.Column("subreddit_id", sa.String(36), nullable=False),
        sa.Column("outcome_type", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("evidence", sa.Text, nullable=False, server_default=""),
        sa.Column("conclusions_evaluated", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("agent_assessments", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("reported_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_outcome_thread", "outcome_reports", ["thread_id"])
    op.create_index("idx_outcome_subreddit", "outcome_reports", ["subreddit_id"])


def downgrade() -> None:
    op.drop_table("outcome_reports")
    op.drop_table("cross_references")
