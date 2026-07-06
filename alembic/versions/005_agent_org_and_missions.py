"""Phase 6: Agent organization, subreddit missions, budgets, approvals, autoresearch.

Adds:
- Subreddit mission fields (program.md-style directive + parsed objectives)
- Per-agent budget/cost tracking on memberships + reports_to_agent_id + autoresearch_policy
- autoresearch_enabled flag on agent identities
- approval_requests table (Paperclip-style human-in-loop queue)
- autoresearch_runs table (audit trail for Karpathy-style research loops)

All additions are nullable/defaulted so existing rows remain valid.

Revision ID: 005
Revises: 004
Create Date: 2026-04-10
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- subreddits: mission fields ----
    with op.batch_alter_table("subreddits") as batch:
        batch.add_column(sa.Column("mission_md", sa.Text, nullable=True))
        batch.add_column(
            sa.Column("mission_objectives", sa.JSON, nullable=False, server_default="[]")
        )
        batch.add_column(
            sa.Column("mission_version", sa.Integer, nullable=False, server_default="1")
        )
        batch.add_column(sa.Column("mission_updated_at", sa.DateTime(timezone=True), nullable=True))

    # ---- subreddit_memberships: per-agent budgets + org + autoresearch policy ----
    with op.batch_alter_table("subreddit_memberships") as batch:
        batch.add_column(sa.Column("max_cost_per_thread_usd", sa.Float, nullable=True))
        batch.add_column(sa.Column("monthly_budget_usd", sa.Float, nullable=True))
        batch.add_column(
            sa.Column("lifetime_cost_usd", sa.Float, nullable=False, server_default="0.0")
        )
        batch.add_column(
            sa.Column("lifetime_input_tokens", sa.Integer, nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("lifetime_output_tokens", sa.Integer, nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("current_month_cost_usd", sa.Float, nullable=False, server_default="0.0")
        )
        batch.add_column(
            sa.Column("current_month_reset_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("reports_to_agent_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("autoresearch_policy", sa.JSON, nullable=True))

    # ---- agent_identities: opt-in flag for autoresearch ----
    with op.batch_alter_table("agent_identities") as batch:
        batch.add_column(
            sa.Column(
                "autoresearch_enabled",
                sa.Boolean,
                nullable=False,
                server_default=sa.false(),
            )
        )

    # ---- approval_requests ----
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "subreddit_id",
            sa.String(36),
            sa.ForeignKey("subreddits.id"),
            nullable=False,
        ),
        sa.Column("request_type", sa.String(30), nullable=False),
        sa.Column("initiator", sa.String(200), nullable=False, server_default=""),
        sa.Column("target_ref", sa.String(200), nullable=True),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("estimated_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("ttl_seconds", sa.Integer, nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.String(200), nullable=True),
    )
    op.create_index(
        "idx_approval_subreddit_status",
        "approval_requests",
        ["subreddit_id", "status"],
    )
    op.create_index("idx_approval_requested_at", "approval_requests", ["requested_at"])

    # ---- autoresearch_runs ----
    op.create_table(
        "autoresearch_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thread_id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("subreddit_id", sa.String(36), nullable=True),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("scratchpad", sa.Text, nullable=False, server_default=""),
        sa.Column("steps", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("metric_name", sa.String(50), nullable=False, server_default=""),
        sa.Column("metric_start", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("metric_end", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_autoresearch_thread", "autoresearch_runs", ["thread_id"])
    op.create_index("idx_autoresearch_agent", "autoresearch_runs", ["agent_id"])


def downgrade() -> None:
    op.drop_index("idx_autoresearch_agent", table_name="autoresearch_runs")
    op.drop_index("idx_autoresearch_thread", table_name="autoresearch_runs")
    op.drop_table("autoresearch_runs")

    op.drop_index("idx_approval_requested_at", table_name="approval_requests")
    op.drop_index("idx_approval_subreddit_status", table_name="approval_requests")
    op.drop_table("approval_requests")

    with op.batch_alter_table("agent_identities") as batch:
        batch.drop_column("autoresearch_enabled")

    with op.batch_alter_table("subreddit_memberships") as batch:
        batch.drop_column("autoresearch_policy")
        batch.drop_column("reports_to_agent_id")
        batch.drop_column("current_month_reset_at")
        batch.drop_column("current_month_cost_usd")
        batch.drop_column("lifetime_output_tokens")
        batch.drop_column("lifetime_input_tokens")
        batch.drop_column("lifetime_cost_usd")
        batch.drop_column("monthly_budget_usd")
        batch.drop_column("max_cost_per_thread_usd")

    with op.batch_alter_table("subreddits") as batch:
        batch.drop_column("mission_updated_at")
        batch.drop_column("mission_version")
        batch.drop_column("mission_objectives")
        batch.drop_column("mission_md")
