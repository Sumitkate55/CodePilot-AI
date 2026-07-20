"""Ports required by repository management use cases."""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol
from uuid import UUID

from codepilot_api.domain.repositories.entities import (
    ImportedWorkspace,
    RepositoryAnalysisPayload,
    RepositoryAnalysisRecord,
    RepositoryRecord,
    RepositorySource,
    RepositoryVersionRecord,
)


class RepositoryCatalog(Protocol):
    """Transactional repository metadata persistence port."""

    async def find_by_owner_and_remote(
        self, owner_id: UUID, remote_url: str
    ) -> RepositoryRecord | None: ...

    async def find_zip_by_owner_and_name(
        self, owner_id: UUID, name: str
    ) -> RepositoryRecord | None: ...

    async def get_by_owner(
        self, owner_id: UUID, repository_id: UUID
    ) -> RepositoryRecord | None: ...

    async def list_by_owner(self, owner_id: UUID) -> tuple[RepositoryRecord, ...]: ...

    async def next_version_number(self, repository_id: UUID) -> int: ...

    async def create_repository(
        self,
        repository_id: UUID,
        owner_id: UUID,
        name: str,
        source_type: RepositorySource,
        remote_url: str | None,
    ) -> RepositoryRecord: ...

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
    ) -> RepositoryVersionRecord: ...

    async def delete(self, repository: RepositoryRecord) -> None: ...


class WorkspaceImporter(Protocol):
    """Securely turn an external source into a validated workspace directory."""

    async def clone_github(self, source_url: str, destination: Path) -> ImportedWorkspace: ...

    def extract_zip(self, archive_path: Path, destination: Path) -> ImportedWorkspace: ...


class RepositoryStorage(Protocol):
    """Persist and remove validated source workspaces on local/object storage."""

    def staging_directory(self) -> AbstractContextManager[Path]: ...

    def persist(
        self, source_root: Path, owner_id: UUID, repository_id: UUID, version_id: UUID
    ) -> str: ...

    def resolve_storage_key(self, storage_key: str) -> Path: ...

    def delete_version(self, owner_id: UUID, repository_id: UUID, version_id: UUID) -> None: ...

    def delete_repository(self, owner_id: UUID, repository_id: UUID) -> None: ...


class RepositoryAnalyzer(Protocol):
    """Derive deterministic source intelligence without changing the workspace."""

    def analyze(self, source_root: Path) -> RepositoryAnalysisPayload: ...


class RepositoryAnalysisStore(Protocol):
    """Persist and retrieve a repository-version intelligence profile."""

    async def get_by_version(
        self, repository_version_id: UUID
    ) -> RepositoryAnalysisRecord | None: ...

    async def upsert(
        self, repository_version_id: UUID, payload: RepositoryAnalysisPayload
    ) -> RepositoryAnalysisRecord: ...
