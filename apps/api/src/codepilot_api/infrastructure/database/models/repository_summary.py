"""Persisted AI project-summary model."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RepositorySummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One current AI project summary for an immutable repository version."""

    __tablename__ = "repository_summaries"

    repository_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
