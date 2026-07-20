"""Use cases for generating persisted repository documentation."""

from __future__ import annotations

from uuid import UUID

from codepilot_api.application.documentation.contracts import DocumentationAgent, DocumentationStore
from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryCatalog,
)
from codepilot_api.application.repositories.intelligence_service import (
    RepositoryIntelligenceService,
)
from codepilot_api.domain.documentation.entities import DocumentationContext, DocumentationRecord
from codepilot_api.domain.documentation.errors import DocumentationNotFound
from codepilot_api.domain.repositories.entities import RepositoryRecord
from codepilot_api.domain.repositories.errors import RepositoryNotFound


class DocumentationService:
    """Generate documentation only from the newest owned source-version intelligence."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        documentation_store: DocumentationStore,
        intelligence_service: RepositoryIntelligenceService,
        agent: DocumentationAgent,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._documentation_store = documentation_store
        self._intelligence_service = intelligence_service
        self._agent = agent

    async def generate_latest(self, owner_id: UUID, repository_id: UUID) -> DocumentationRecord:
        """Generate a source-grounded Markdown bundle, analyzing the latest version when needed."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        analysis = await self._analysis_store.get_by_version(version.id)
        if analysis is None:
            analysis = await self._intelligence_service.analyze_latest(owner_id, repository_id)
        payload = await self._agent.generate(
            DocumentationContext(
                repository_id=repository.id,
                repository_version_id=version.id,
                repository_name=repository.name,
                source_type=version.source_type.value,
                remote_url=repository.remote_url,
                analysis_results=analysis.results,
            )
        )
        return await self._documentation_store.upsert(version.id, payload)

    async def get_latest(self, owner_id: UUID, repository_id: UUID) -> DocumentationRecord:
        """Return the saved documentation bundle for the latest immutable repository version."""
        repository = await self._get_repository(owner_id, repository_id)
        documentation = await self._documentation_store.get_by_version(
            self._latest_version(repository).id
        )
        if documentation is None:
            raise DocumentationNotFound
        return documentation

    async def _get_repository(self, owner_id: UUID, repository_id: UUID) -> RepositoryRecord:
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        return repository

    @staticmethod
    def _latest_version(repository: RepositoryRecord):
        if not repository.versions:
            raise DocumentationNotFound
        return repository.versions[0]
