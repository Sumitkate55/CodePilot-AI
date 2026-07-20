"""Create repository RAG index-status records.

Revision ID: 20260718_005
Revises: 20260717_004
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_005"
down_revision: str | None = "20260717_004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Track Qdrant index readiness for each immutable repository version."""
    op.create_table(
        "repository_chat_indexes",
        sa.Column("repository_version_id", sa.Uuid(), nullable=False),
        sa.Column("indexing_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repository_chat_indexes_repository_version_id",
        "repository_chat_indexes",
        ["repository_version_id"],
        unique=True,
    )


def downgrade() -> None:
    """Remove repository RAG index-status records."""
    op.drop_index("ix_repository_chat_indexes_repository_version_id", table_name="repository_chat_indexes")
    op.drop_table("repository_chat_indexes")
