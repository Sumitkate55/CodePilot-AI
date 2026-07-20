"""Create generated unit-test artifact records.

Revision ID: 20260718_008
Revises: 20260718_007
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_008"
down_revision: str | None = "20260718_007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create generated test files scoped to one immutable repository source version."""
    op.create_table(
        "generated_tests",
        sa.Column("repository_version_id", sa.Uuid(), nullable=False),
        sa.Column("function_name", sa.String(length=240), nullable=False),
        sa.Column("function_path", sa.String(length=1024), nullable=False),
        sa.Column("function_line", sa.Integer(), nullable=False),
        sa.Column("function_language", sa.String(length=80), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("framework", sa.String(length=20), nullable=False),
        sa.Column("test_file_path", sa.String(length=1024), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("test_code", sa.Text(), nullable=False),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["repository_version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "repository_version_id",
            "function_path",
            "function_line",
            "framework",
            name="uq_generated_tests_target_framework",
        ),
    )
    op.create_index("ix_generated_tests_repository_version_id", "generated_tests", ["repository_version_id"])


def downgrade() -> None:
    """Remove generated unit-test artifact records."""
    op.drop_index("ix_generated_tests_repository_version_id", table_name="generated_tests")
    op.drop_table("generated_tests")
