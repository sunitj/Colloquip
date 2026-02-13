"""Baseline schema: sessions, posts, energy, consensus, platform tables.

Revision ID: 001
Revises: None
Create Date: 2026-02-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Core deliberation tables
    op.create_table(
        "subreddits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("purpose", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("output_template", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("participation_model", sa.String(20), nullable=False, server_default="guided"),
        sa.Column("engine_overrides", sa.JSON, nullable=True),
        sa.Column("tool_configs", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("min_agents", sa.Integer, nullable=False, server_default="3"),
        sa.Column("max_agents", sa.Integer, nullable=False, server_default="8"),
        sa.Column("always_include_red_team", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("max_cost_per_thread_usd", sa.Float, server_default="5.0"),
        sa.Column("monthly_budget_usd", sa.Float, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "deliberation_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("hypothesis", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("current_phase", sa.String(20), nullable=False, server_default="explore"),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("subreddit_id", sa.String(36), sa.ForeignKey("subreddits.id"), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("deliberation_sessions.id"),
            nullable=False,
        ),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("stance", sa.String(20), nullable=False),
        sa.Column("citations", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("key_claims", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("questions_raised", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("connections_identified", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("novelty_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("phase", sa.String(20), nullable=False),
        sa.Column("triggered_by", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_posts_session", "posts", ["session_id"])
    op.create_index("idx_posts_agent", "posts", ["agent_id"])
    op.create_index("idx_posts_phase", "posts", ["phase"])

    op.create_table(
        "energy_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("deliberation_sessions.id"),
            nullable=False,
        ),
        sa.Column("turn", sa.Integer, nullable=False),
        sa.Column("energy", sa.Float, nullable=False),
        sa.Column("novelty", sa.Float),
        sa.Column("disagreement", sa.Float),
        sa.Column("questions", sa.Float),
        sa.Column("staleness", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_energy_session", "energy_history", ["session_id"])

    op.create_table(
        "consensus_maps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("deliberation_sessions.id"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("agreements", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("disagreements", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("minority_positions", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("serendipity_connections", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("final_stances", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", name="uq_consensus_session"),
    )

    # Agent identity and membership tables
    op.create_table(
        "agent_identities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_type", sa.String(100), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("expertise_tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("persona_prompt", sa.Text, nullable=False),
        sa.Column("phase_mandates", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("domain_keywords", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("knowledge_scope", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("evaluation_criteria", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("is_red_team", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_agent_type", "agent_identities", ["agent_type"])

    op.create_table(
        "subreddit_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agent_identities.id"), nullable=False),
        sa.Column("subreddit_id", sa.String(36), sa.ForeignKey("subreddits.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("role_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("tool_access", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("threads_participated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_posts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_id", "subreddit_id", name="uq_agent_subreddit"),
    )
    op.create_index("idx_membership_subreddit", "subreddit_memberships", ["subreddit_id"])
    op.create_index("idx_membership_agent", "subreddit_memberships", ["agent_id"])

    # Synthesis and cost tables
    op.create_table(
        "syntheses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("deliberation_sessions.id"),
            nullable=False,
        ),
        sa.Column("template_type", sa.String(50), nullable=False),
        sa.Column("sections", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("audit_chains", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("total_citations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("citation_verification", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", name="uq_synthesis_session"),
    )

    op.create_table(
        "cost_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("deliberation_sessions.id"),
            nullable=False,
        ),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("model", sa.String(100), nullable=False, server_default="default"),
        sa.Column("estimated_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_cost_session", "cost_records", ["session_id"])


def downgrade() -> None:
    op.drop_table("cost_records")
    op.drop_table("syntheses")
    op.drop_table("subreddit_memberships")
    op.drop_table("agent_identities")
    op.drop_table("consensus_maps")
    op.drop_table("energy_history")
    op.drop_table("posts")
    op.drop_table("deliberation_sessions")
    op.drop_table("subreddits")
