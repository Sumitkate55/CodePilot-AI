"""Create repository intelligence profiles.

Revision ID: 20260717_003
Revises: 20260717_002
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260717_003"
down_revision: str | None = "20260717_002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one bounded intelligence profile for each stored source version."""
    op.create_table(
        "repository_analyses",
        sa.Column("repository_version_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repository_analyses_repository_version_id",
        "repository_analyses",
        ["repository_version_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove persisted repository intelligence profiles."""
    op.drop_index("ix_repository_analyses_repository_version_id", table_name="repository_analyses")
    op.drop_table("repository_analyses")
