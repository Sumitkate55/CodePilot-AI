"""Repository-version persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from codepilot_api.infrastructure.database.models.repository import Repository


class RepositoryVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable snapshot of a stored source tree."""

    __tablename__ = "repository_versions"
    __table_args__ = (
        UniqueConstraint("repository_id", "version_number", name="uq_repository_versions_number"),
    )

    repository_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    repository: Mapped[Repository] = relationship(back_populates="versions")
