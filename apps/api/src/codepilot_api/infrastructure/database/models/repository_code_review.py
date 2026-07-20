"""Persisted repository-wide code-review model."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RepositoryCodeReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One current deterministic code review for an immutable source version."""

    __tablename__ = "repository_code_reviews"

    repository_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    review_version: Mapped[int] = mapped_column(Integer, nullable=False)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    scanned_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
