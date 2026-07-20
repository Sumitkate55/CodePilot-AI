"""Persisted source-grounded repository documentation model."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RepositoryDocumentation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One current Markdown documentation bundle for an immutable repository version."""

    __tablename__ = "repository_documentation"

    repository_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    documents: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
