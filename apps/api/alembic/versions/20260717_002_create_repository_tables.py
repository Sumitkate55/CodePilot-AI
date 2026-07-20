"""Create repository and repository version tables.

Revision ID: 20260717_002
Revises: 20260717_001
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260717_002"
down_revision: str | None = "20260717_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create repository ownership and immutable source-version metadata."""
    op.create_table(
        "repositories",
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("remote_url", sa.String(length=2048), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repositories_owner_id", "repositories", ["owner_id"])
    op.create_index(
        "uq_repositories_owner_remote_url",
        "repositories",
        ["owner_id", "remote_url"],
        unique=True,
    )
    op.create_table(
        "repository_versions",
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "version_number", name="uq_repository_versions_number"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_repository_versions_repository_id", "repository_versions", ["repository_id"])


def downgrade() -> None:
    """Remove repository metadata after its version records."""
    op.drop_index("ix_repository_versions_repository_id", table_name="repository_versions")
    op.drop_table("repository_versions")
    op.drop_index("uq_repositories_owner_remote_url", table_name="repositories")
    op.drop_index("ix_repositories_owner_id", table_name="repositories")
    op.drop_table("repositories")
