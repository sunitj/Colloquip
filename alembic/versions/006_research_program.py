"""Add research_program columns to subreddits table.

Revision ID: 006
Revises: 005
Create Date: 2026-03-16
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subreddits",
        sa.Column("research_program", sa.Text(), nullable=True),
    )
    op.add_column(
        "subreddits",
        sa.Column(
            "research_program_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("subreddits", "research_program_version")
    op.drop_column("subreddits", "research_program")
