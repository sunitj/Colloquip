"""Phase 3: Add institutional memory tables.

Revision ID: 002
Revises: 001
Create Date: 2026-02-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "synthesis_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thread_id", sa.String(36), nullable=False),
        sa.Column("subreddit_id", sa.String(36), nullable=False),
        sa.Column("subreddit_name", sa.String(100), nullable=False),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("synthesis_content", sa.Text, nullable=False, server_default=""),
        sa.Column("key_conclusions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("citations_used", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("agents_involved", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("template_type", sa.String(50), nullable=False, server_default=""),
        sa.Column("confidence_level", sa.String(50), nullable=False, server_default=""),
        sa.Column("evidence_quality", sa.String(50), nullable=False, server_default=""),
        sa.Column("embedding", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_synmem_subreddit", "synthesis_memories", ["subreddit_id"])
    op.create_index("idx_synmem_thread", "synthesis_memories", ["thread_id"])

    op.create_table(
        "memory_annotations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("memory_id", sa.String(36), sa.ForeignKey("synthesis_memories.id"), nullable=False),
        sa.Column("annotation_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_annotation_memory", "memory_annotations", ["memory_id"])


def downgrade() -> None:
    op.drop_table("memory_annotations")
    op.drop_table("synthesis_memories")
