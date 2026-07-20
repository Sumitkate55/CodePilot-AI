"""Persisted generated unit-test file model."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GeneratedTest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One generated framework-matched test suite for a source function and version."""

    __tablename__ = "generated_tests"
    __table_args__ = (
        UniqueConstraint(
            "repository_version_id",
            "function_path",
            "function_line",
            "framework",
            name="uq_generated_tests_target_framework",
        ),
    )

    repository_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    function_name: Mapped[str] = mapped_column(String(240), nullable=False)
    function_path: Mapped[str] = mapped_column(String(1_024), nullable=False)
    function_line: Mapped[int] = mapped_column(Integer, nullable=False)
    function_language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    framework: Mapped[str] = mapped_column(String(20), nullable=False)
    test_file_path: Mapped[str] = mapped_column(String(1_024), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    test_code: Mapped[str] = mapped_column(Text, nullable=False)
    coverage: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
