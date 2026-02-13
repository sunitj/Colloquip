"""Phase 4: Add watcher and notification tables.

Revision ID: 003
Revises: 002
Create Date: 2026-02-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("watcher_type", sa.String(20), nullable=False),
        sa.Column("subreddit_id", sa.String(36), sa.ForeignKey("subreddits.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("query", sa.Text, nullable=False, server_default=""),
        sa.Column("poll_interval_seconds", sa.Integer, nullable=False, server_default="300"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("auto_create_thread", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("auto_thread_approval_rate", sa.Float, nullable=True),
        sa.Column("created_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_watcher_subreddit", "watchers", ["subreddit_id"])

    op.create_table(
        "watcher_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("watcher_id", sa.String(36), sa.ForeignKey("watchers.id"), nullable=False),
        sa.Column("subreddit_id", sa.String(36), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("source_type", sa.String(50), nullable=False, server_default=""),
        sa.Column("source_id", sa.String(200), nullable=False, server_default=""),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("raw_data", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("triage_signal", sa.String(20), nullable=True),
        sa.Column("triage_reasoning", sa.Text, nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_event_watcher", "watcher_events", ["watcher_id"])
    op.create_index("idx_event_subreddit", "watcher_events", ["subreddit_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("watcher_id", sa.String(36), sa.ForeignKey("watchers.id"), nullable=False),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("subreddit_id", sa.String(36), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("signal", sa.String(20), nullable=False),
        sa.Column("suggested_hypothesis", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("action_taken", sa.String(20), nullable=True),
        sa.Column("thread_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_notification_subreddit", "notifications", ["subreddit_id"])
    op.create_index("idx_notification_status", "notifications", ["status"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("watcher_events")
    op.drop_table("watchers")
