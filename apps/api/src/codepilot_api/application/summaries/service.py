"""AI project-summary application service."""

from __future__ import annotations

from uuid import UUID

from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryCatalog,
)
from codepilot_api.application.repositories.intelligence_service import (
    RepositoryIntelligenceService,
)
from codepilot_api.application.summaries.contracts import ProjectSummaryAgent, ProjectSummaryStore
from codepilot_api.domain.repositories.entities import RepositoryRecord
from codepilot_api.domain.repositories.errors import RepositoryNotFound
from codepilot_api.domain.summaries.entities import (
    ProjectSummaryContext,
    ProjectSummaryRecord,
)
from codepilot_api.domain.summaries.errors import ProjectSummaryNotFound


class ProjectSummaryService:
    """Generate and retain source-grounded summaries for the latest repository version."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        summary_store: ProjectSummaryStore,
        intelligence_service: RepositoryIntelligenceService,
        agent: ProjectSummaryAgent,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._summary_store = summary_store
        self._intelligence_service = intelligence_service
        self._agent = agent

    async def generate_latest(self, owner_id: UUID, repository_id: UUID) -> ProjectSummaryRecord:
        """Generate a structured summary, first deriving deterministic intelligence if needed."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        analysis = await self._analysis_store.get_by_version(version.id)
        if analysis is None:
            analysis = await self._intelligence_service.analyze_latest(owner_id, repository_id)
        context = ProjectSummaryContext(
            repository_id=repository.id,
            repository_version_id=version.id,
            repository_name=repository.name,
            source_type=version.source_type.value,
            remote_url=repository.remote_url,
            analysis_results=analysis.results,
        )
        payload = await self._agent.generate(context)
        return await self._summary_store.upsert(version.id, payload)

    async def get_latest(self, owner_id: UUID, repository_id: UUID) -> ProjectSummaryRecord:
        """Return the saved project summary for the latest immutable source version."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        summary = await self._summary_store.get_by_version(version.id)
        if summary is None:
            raise ProjectSummaryNotFound
        return summary

    async def _get_repository(self, owner_id: UUID, repository_id: UUID) -> RepositoryRecord:
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        return repository

    @staticmethod
    def _latest_version(repository: RepositoryRecord):
        if not repository.versions:
            raise ProjectSummaryNotFound
        return repository.versions[0]
