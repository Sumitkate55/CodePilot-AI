"""Create persisted refactoring-advisor proposals.

Revision ID: 20260718_007
Revises: 20260718_006
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_007"
down_revision: str | None = "20260718_006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create one auditable refactor proposal per source version and review finding."""
    op.create_table(
        "refactor_proposals",
        sa.Column("repository_version_id", sa.Uuid(), nullable=False),
        sa.Column("finding_key", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("source_start_line", sa.Integer(), nullable=False),
        sa.Column("source_end_line", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("original_source", sa.Text(), nullable=False),
        sa.Column("replacement_source", sa.Text(), nullable=False),
        sa.Column("diff", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("estimated_quality_gain", sa.Integer(), nullable=False),
        sa.Column("impact_summary", sa.JSON(), nullable=False),
        sa.Column("testing_steps", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_version_id", "finding_key", name="uq_refactor_proposals_version_finding"),
    )
    op.create_index("ix_refactor_proposals_repository_version_id", "refactor_proposals", ["repository_version_id"])


def downgrade() -> None:
    """Remove refactoring-advisor proposals."""
    op.drop_index("ix_refactor_proposals_repository_version_id", table_name="refactor_proposals")
    op.drop_table("refactor_proposals")
