"""SQLAlchemy adapter for generated repository documentation bundles."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.documentation.entities import DocumentationPayload, DocumentationRecord
from codepilot_api.infrastructure.database.models.repository_documentation import (
    RepositoryDocumentation,
)


class SqlAlchemyDocumentationStore:
    """Store the current Markdown documentation bundle for each source version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_version(self, repository_version_id: UUID) -> DocumentationRecord | None:
        model = await self._session.scalar(
            select(RepositoryDocumentation).where(
                RepositoryDocumentation.repository_version_id == repository_version_id
            )
        )
        return self._to_record(model) if model else None

    async def upsert(
        self, repository_version_id: UUID, payload: DocumentationPayload
    ) -> DocumentationRecord:
        model = await self._session.scalar(
            select(RepositoryDocumentation).where(
                RepositoryDocumentation.repository_version_id == repository_version_id
            )
        )
        if model is None:
            model = RepositoryDocumentation(
                repository_version_id=repository_version_id,
                model=payload.model,
                prompt_version=payload.prompt_version,
                documents=payload.documents,
                notes=list(payload.notes),
            )
            self._session.add(model)
        else:
            model.model = payload.model
            model.prompt_version = payload.prompt_version
            model.documents = payload.documents
            model.notes = list(payload.notes)
            model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    @staticmethod
    def _to_record(model: RepositoryDocumentation) -> DocumentationRecord:
        return DocumentationRecord(
            id=model.id,
            repository_version_id=model.repository_version_id,
            model=model.model,
            prompt_version=model.prompt_version,
            documents={str(key): str(value) for key, value in model.documents.items()},
            notes=tuple(str(note) for note in model.notes),
            created_at=SqlAlchemyDocumentationStore._as_utc(model.created_at),
            updated_at=SqlAlchemyDocumentationStore._as_utc(model.updated_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
