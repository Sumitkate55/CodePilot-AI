"""Persisted source-grounded refactoring proposal model."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RefactorProposal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One AI refactor proposal for one review finding in one immutable source version."""

    __tablename__ = "refactor_proposals"
    __table_args__ = (
        UniqueConstraint(
            "repository_version_id", "finding_key", name="uq_refactor_proposals_version_finding"
        ),
    )

    repository_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    finding_key: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(1_024), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    source_start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    original_source: Mapped[str] = mapped_column(Text, nullable=False)
    replacement_source: Mapped[str] = mapped_column(Text, nullable=False)
    diff: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_quality_gain: Mapped[int] = mapped_column(Integer, nullable=False)
    impact_summary: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    testing_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
