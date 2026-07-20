"""Create AI project-summary profiles.

Revision ID: 20260717_004
Revises: 20260717_003
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260717_004"
down_revision: str | None = "20260717_003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one structured AI summary per immutable repository version."""
    op.create_table(
        "repository_summaries",
        sa.Column("repository_version_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repository_summaries_repository_version_id",
        "repository_summaries",
        ["repository_version_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove persisted AI project summaries."""
    op.drop_index("ix_repository_summaries_repository_version_id", table_name="repository_summaries")
    op.drop_table("repository_summaries")
