"""SQLAlchemy implementation of the repository metadata catalog."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from codepilot_api.domain.repositories.entities import (
    RepositoryRecord,
    RepositorySource,
    RepositoryVersionRecord,
)
from codepilot_api.infrastructure.database.models.repository import Repository
from codepilot_api.infrastructure.database.models.repository_version import RepositoryVersion


class SqlAlchemyRepositoryCatalog:
    """Persist user-scoped repositories and their immutable versions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_owner_and_remote(
        self, owner_id: UUID, remote_url: str
    ) -> RepositoryRecord | None:
        statement = self._repository_statement().where(
            Repository.owner_id == owner_id,
            Repository.remote_url == remote_url,
        )
        model = await self._session.scalar(statement)
        return self._to_record(model) if model else None

    async def find_zip_by_owner_and_name(
        self, owner_id: UUID, name: str
    ) -> RepositoryRecord | None:
        statement = self._repository_statement().where(
            Repository.owner_id == owner_id,
            Repository.source_type == RepositorySource.ZIP.value,
            Repository.name == name,
        )
        model = await self._session.scalar(statement)
        return self._to_record(model) if model else None

    async def get_by_owner(self, owner_id: UUID, repository_id: UUID) -> RepositoryRecord | None:
        statement = self._repository_statement().where(
            Repository.owner_id == owner_id,
            Repository.id == repository_id,
        )
        model = await self._session.scalar(statement)
        return self._to_record(model) if model else None

    async def list_by_owner(self, owner_id: UUID) -> tuple[RepositoryRecord, ...]:
        statement = (
            self._repository_statement()
            .where(Repository.owner_id == owner_id)
            .order_by(Repository.updated_at.desc())
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(self._to_record(model) for model in models)

    async def next_version_number(self, repository_id: UUID) -> int:
        version_number = await self._session.scalar(
            select(func.coalesce(func.max(RepositoryVersion.version_number), 0)).where(
                RepositoryVersion.repository_id == repository_id
            )
        )
        return int(version_number or 0) + 1

    async def create_repository(
        self,
        repository_id: UUID,
        owner_id: UUID,
        name: str,
        source_type: RepositorySource,
        remote_url: str | None,
    ) -> RepositoryRecord:
        model = Repository(
            id=repository_id,
            owner_id=owner_id,
            name=name,
            source_type=source_type.value,
            remote_url=remote_url,
        )
        self._session.add(model)
        await self._session.flush()
        return RepositoryRecord(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            source_type=RepositorySource(model.source_type),
            remote_url=model.remote_url,
            created_at=self._as_utc(model.created_at),
            versions=(),
        )

    async def add_version(
        self,
        version_id: UUID,
        repository_id: UUID,
        version_number: int,
        source_type: RepositorySource,
        source_url: str | None,
        commit_sha: str | None,
        storage_key: str,
        file_count: int,
        size_bytes: int,
    ) -> RepositoryVersionRecord:
        model = RepositoryVersion(
            id=version_id,
            repository_id=repository_id,
            version_number=version_number,
            source_type=source_type.value,
            source_url=source_url,
            commit_sha=commit_sha,
            storage_key=storage_key,
            file_count=file_count,
            size_bytes=size_bytes,
        )
        self._session.add(model)
        repository = await self._session.get(Repository, repository_id)
        if repository is not None:
            repository.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_version_record(model)

    async def delete(self, repository: RepositoryRecord) -> None:
        model = await self._session.get(Repository, repository.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    @staticmethod
    def _repository_statement():
        return (
            select(Repository)
            .options(selectinload(Repository.versions))
            .execution_options(populate_existing=True)
        )

    @staticmethod
    def _to_record(model: Repository) -> RepositoryRecord:
        versions = tuple(
            SqlAlchemyRepositoryCatalog._to_version_record(version) for version in model.versions
        )
        return RepositoryRecord(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            source_type=RepositorySource(model.source_type),
            remote_url=model.remote_url,
            created_at=SqlAlchemyRepositoryCatalog._as_utc(model.created_at),
            versions=versions,
        )

    @staticmethod
    def _to_version_record(model: RepositoryVersion) -> RepositoryVersionRecord:
        return RepositoryVersionRecord(
            id=model.id,
            repository_id=model.repository_id,
            version_number=model.version_number,
            source_type=RepositorySource(model.source_type),
            source_url=model.source_url,
            commit_sha=model.commit_sha,
            storage_key=model.storage_key,
            file_count=model.file_count,
            size_bytes=model.size_bytes,
            created_at=SqlAlchemyRepositoryCatalog._as_utc(model.created_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
