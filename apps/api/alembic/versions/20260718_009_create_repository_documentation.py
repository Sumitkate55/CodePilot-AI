"""Create generated repository documentation bundles.

Revision ID: 20260718_009
Revises: 20260718_008
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_009"
down_revision: str | None = "20260718_008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist one current documentation bundle for every source version."""
    op.create_table(
        "repository_documentation",
        sa.Column("repository_version_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("documents", sa.JSON(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repository_documentation_repository_version_id",
        "repository_documentation",
        ["repository_version_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove generated documentation bundles."""
    op.drop_index("ix_repository_documentation_repository_version_id", table_name="repository_documentation")
    op.drop_table("repository_documentation")
