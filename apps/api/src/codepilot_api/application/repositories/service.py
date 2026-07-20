"""Repository ingestion and lifecycle application service."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from codepilot_api.application.repositories.contracts import (
    RepositoryCatalog,
    RepositoryStorage,
    WorkspaceImporter,
)
from codepilot_api.domain.repositories.entities import RepositoryRecord, RepositorySource
from codepilot_api.domain.repositories.errors import RepositoryNotFound


class RepositoryService:
    """Create immutable repository versions from secure GitHub and ZIP workspaces."""

    def __init__(
        self,
        catalog: RepositoryCatalog,
        storage: RepositoryStorage,
        workspace_importer: WorkspaceImporter,
    ) -> None:
        self._catalog = catalog
        self._storage = storage
        self._workspace_importer = workspace_importer

    async def import_github(self, owner_id: UUID, source_url: str, name: str) -> RepositoryRecord:
        """Clone a GitHub repository and persist it as a new immutable version."""
        with self._storage.staging_directory() as staging:
            workspace = await self._workspace_importer.clone_github(source_url, staging / "source")
            return await self._persist_workspace(
                owner_id=owner_id,
                source_type=RepositorySource.GITHUB,
                name=name,
                remote_url=source_url,
                source_url=source_url,
                source_root=Path(workspace.source_root),
                file_count=workspace.file_count,
                size_bytes=workspace.size_bytes,
                commit_sha=workspace.commit_sha,
            )

    async def import_zip(self, owner_id: UUID, name: str, archive_path: Path) -> RepositoryRecord:
        """Extract a validated ZIP archive and persist it as a new immutable version."""
        with self._storage.staging_directory() as staging:
            workspace = self._workspace_importer.extract_zip(archive_path, staging / "source")
            return await self._persist_workspace(
                owner_id=owner_id,
                source_type=RepositorySource.ZIP,
                name=name,
                remote_url=None,
                source_url=None,
                source_root=Path(workspace.source_root),
                file_count=workspace.file_count,
                size_bytes=workspace.size_bytes,
                commit_sha=None,
            )

    async def list_repositories(self, owner_id: UUID) -> tuple[RepositoryRecord, ...]:
        """List repositories owned by the authenticated user."""
        return await self._catalog.list_by_owner(owner_id)

    async def get_repository(self, owner_id: UUID, repository_id: UUID) -> RepositoryRecord:
        """Get a repository only if it belongs to the authenticated user."""
        repository = await self._catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        return repository

    async def delete_repository(self, owner_id: UUID, repository_id: UUID) -> None:
        """Remove repository metadata and its scoped source storage."""
        repository = await self.get_repository(owner_id, repository_id)
        self._storage.delete_repository(owner_id, repository.id)
        await self._catalog.delete(repository)

    async def _persist_workspace(
        self,
        owner_id: UUID,
        source_type: RepositorySource,
        name: str,
        remote_url: str | None,
        source_url: str | None,
        source_root: Path,
        file_count: int,
        size_bytes: int,
        commit_sha: str | None,
    ) -> RepositoryRecord:
        existing = (
            await self._catalog.find_by_owner_and_remote(owner_id, remote_url)
            if remote_url
            else await self._catalog.find_zip_by_owner_and_name(owner_id, name)
        )
        repository_id = existing.id if existing else uuid4()
        version_id = uuid4()
        version_number = await self._catalog.next_version_number(repository_id) if existing else 1
        storage_key = self._storage.persist(source_root, owner_id, repository_id, version_id)

        try:
            if existing is None:
                await self._catalog.create_repository(
                    repository_id, owner_id, name, source_type, remote_url
                )
            await self._catalog.add_version(
                version_id=version_id,
                repository_id=repository_id,
                version_number=version_number,
                source_type=source_type,
                source_url=source_url,
                commit_sha=commit_sha,
                storage_key=storage_key,
                file_count=file_count,
                size_bytes=size_bytes,
            )
        except Exception:
            self._storage.delete_version(owner_id, repository_id, version_id)
            raise

        repository = await self._catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RuntimeError("Repository persistence did not return the imported repository.")
        return repository
