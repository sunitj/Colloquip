"""Add research_jobs table for autonomous research loops.

Revision ID: 007
Revises: 006
Create Date: 2026-03-16
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "subreddit_id",
            sa.String(36),
            sa.ForeignKey("subreddits.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("research_program_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_iteration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("threads_completed", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("threads_discarded", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("baseline_metric", sa.Float(), nullable=True),
        sa.Column("best_metric", sa.Float(), nullable=True),
        sa.Column("metric_history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_cost_usd", sa.Float(), nullable=False, server_default="25.0"),
        sa.Column("max_threads_per_hour", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("max_runtime_hours", sa.Float(), nullable=False, server_default="24.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_rjob_subreddit", "research_jobs", ["subreddit_id"])
    op.create_index("idx_rjob_status", "research_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("research_jobs")
