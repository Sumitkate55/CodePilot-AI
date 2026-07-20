"""Persisted index status for Qdrant repository chunks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RepositoryChatIndex(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One current Qdrant index state for each immutable repository version."""

    __tablename__ = "repository_chat_indexes"

    repository_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    indexing_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
