"""Persisted repository intelligence profile model."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RepositoryAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One current deterministic intelligence result for an immutable source version."""

    __tablename__ = "repository_analyses"

    repository_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
