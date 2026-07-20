"""Repository persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from codepilot_api.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from codepilot_api.infrastructure.database.models.repository_version import RepositoryVersion


class Repository(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A logical repository owned by one authenticated user."""

    __tablename__ = "repositories"
    __table_args__ = (
        Index("uq_repositories_owner_remote_url", "owner_id", "remote_url", unique=True),
    )

    owner_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    remote_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    versions: Mapped[list[RepositoryVersion]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RepositoryVersion.version_number.desc()",
    )
