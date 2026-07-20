"""Create persisted repository-wide code reviews.

Revision ID: 20260718_006
Revises: 20260718_005
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_006"
down_revision: str | None = "20260718_005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one review record for each immutable repository version."""
    op.create_table(
        "repository_code_reviews",
        sa.Column("repository_version_id", sa.Uuid(), nullable=False),
        sa.Column("review_version", sa.Integer(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False),
        sa.Column("scanned_file_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repository_code_reviews_repository_version_id",
        "repository_code_reviews",
        ["repository_version_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove persisted repository code-review records."""
    op.drop_index("ix_repository_code_reviews_repository_version_id", table_name="repository_code_reviews")
    op.drop_table("repository_code_reviews")
