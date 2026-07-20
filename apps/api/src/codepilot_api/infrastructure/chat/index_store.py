"""SQLAlchemy adapter for repository RAG index status."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.chat.entities import RepositoryChatIndexRecord, RepositoryChatIndexStatus
from codepilot_api.infrastructure.database.models.repository_chat_index import RepositoryChatIndex


class SqlAlchemyRepositoryChatIndexStore:
    """Store current Qdrant index state for every immutable source version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_version(self, repository_version_id: UUID) -> RepositoryChatIndexRecord | None:
        model = await self._session.scalar(
            select(RepositoryChatIndex).where(
                RepositoryChatIndex.repository_version_id == repository_version_id
            )
        )
        return self._to_record(model) if model else None

    async def mark_ready(
        self,
        repository_version_id: UUID,
        indexing_version: int,
        embedding_model: str,
        chunk_count: int,
    ) -> RepositoryChatIndexRecord:
        model = await self._get_or_create(repository_version_id)
        model.indexing_version = indexing_version
        model.status = RepositoryChatIndexStatus.READY.value
        model.embedding_model = embedding_model
        model.chunk_count = chunk_count
        model.indexed_at = datetime.now(UTC)
        model.failure_message = None
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    async def mark_failed(
        self,
        repository_version_id: UUID,
        indexing_version: int,
        embedding_model: str,
        failure_message: str,
    ) -> RepositoryChatIndexRecord:
        model = await self._get_or_create(repository_version_id)
        model.indexing_version = indexing_version
        model.status = RepositoryChatIndexStatus.FAILED.value
        model.embedding_model = embedding_model
        model.chunk_count = 0
        model.indexed_at = None
        model.failure_message = failure_message[:1000]
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    async def _get_or_create(self, repository_version_id: UUID) -> RepositoryChatIndex:
        model = await self._session.scalar(
            select(RepositoryChatIndex).where(
                RepositoryChatIndex.repository_version_id == repository_version_id
            )
        )
        if model is None:
            model = RepositoryChatIndex(
                repository_version_id=repository_version_id,
                indexing_version=1,
                status=RepositoryChatIndexStatus.FAILED.value,
                embedding_model="",
                chunk_count=0,
            )
            self._session.add(model)
            await self._session.flush()
        return model

    @staticmethod
    def _to_record(model: RepositoryChatIndex) -> RepositoryChatIndexRecord:
        return RepositoryChatIndexRecord(
            id=model.id,
            repository_version_id=model.repository_version_id,
            indexing_version=model.indexing_version,
            status=RepositoryChatIndexStatus(model.status),
            embedding_model=model.embedding_model,
            chunk_count=model.chunk_count,
            indexed_at=SqlAlchemyRepositoryChatIndexStore._as_utc(model.indexed_at),
            failure_message=model.failure_message,
            created_at=SqlAlchemyRepositoryChatIndexStore._as_utc(model.created_at),
            updated_at=SqlAlchemyRepositoryChatIndexStore._as_utc(model.updated_at),
        )

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=UTC)
