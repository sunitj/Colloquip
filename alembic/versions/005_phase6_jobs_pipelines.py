"""Phase 6: Add jobs, pipelines, action proposals, and data connections.

Revision ID: 005
Revises: 004
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tool_invocations column to posts table
    op.add_column(
        "posts",
        sa.Column("tool_invocations", sa.JSON(), nullable=False, server_default="[]"),
    )

    # Nextflow process library catalog
    op.create_table(
        "nextflow_processes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("process_id", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(100), nullable=False, server_default=""),
        sa.Column("input_channels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("output_channels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("container", sa.String(500), nullable=False, server_default=""),
        sa.Column("resource_requirements", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
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
    )
    op.create_index("idx_nfproc_category", "nextflow_processes", ["category"])

    # Jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("deliberation_sessions.id"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(36), nullable=True),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("pipeline", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("compute_backend", sa.String(20), nullable=False, server_default="local"),
        sa.Column("compute_profile", sa.String(100), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("nextflow_run_id", sa.String(200), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("result_artifacts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_job_session", "jobs", ["session_id"])
    op.create_index("idx_job_status", "jobs", ["status"])
    op.create_index("idx_job_thread", "jobs", ["thread_id"])

    # Action proposals table
    op.create_table(
        "action_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("deliberation_sessions.id"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(36), nullable=True),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False, server_default="launch_pipeline"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_pipeline", sa.JSON(), nullable=True),
        sa.Column("proposed_params", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_proposal_session", "action_proposals", ["session_id"])
    op.create_index("idx_proposal_status", "action_proposals", ["status"])

    # Data connections table
    op.create_table(
        "data_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "subreddit_id",
            sa.String(36),
            sa.ForeignKey("subreddits.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("db_type", sa.String(20), nullable=False, server_default="postgresql"),
        sa.Column("connection_string", sa.Text(), nullable=False, server_default=""),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_dataconn_subreddit", "data_connections", ["subreddit_id"])


def downgrade() -> None:
    op.drop_table("data_connections")
    op.drop_table("action_proposals")
    op.drop_table("jobs")
    op.drop_table("nextflow_processes")
    op.drop_column("posts", "tool_invocations")
