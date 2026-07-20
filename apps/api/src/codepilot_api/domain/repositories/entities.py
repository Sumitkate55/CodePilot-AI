"""Framework-independent repository records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RepositorySource(StrEnum):
    """Supported ways a source repository enters CodePilot."""

    GITHUB = "github"
    ZIP = "zip"


@dataclass(frozen=True, slots=True)
class RepositoryVersionRecord:
    """One immutable stored version of a repository."""

    id: UUID
    repository_id: UUID
    version_number: int
    source_type: RepositorySource
    source_url: str | None
    commit_sha: str | None
    storage_key: str
    file_count: int
    size_bytes: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RepositoryRecord:
    """A user-owned repository and its immutable import history."""

    id: UUID
    owner_id: UUID
    name: str
    source_type: RepositorySource
    remote_url: str | None
    created_at: datetime
    versions: tuple[RepositoryVersionRecord, ...]


@dataclass(frozen=True, slots=True)
class ImportedWorkspace:
    """Validated source workspace ready to be persisted as one repository version."""

    source_root: str
    file_count: int
    size_bytes: int
    commit_sha: str | None


@dataclass(frozen=True, slots=True)
class RepositoryAnalysisPayload:
    """Portable deterministic intelligence results produced for one source version."""

    analysis_version: int
    results: dict[str, object]
    file_count: int
    line_count: int


@dataclass(frozen=True, slots=True)
class RepositoryAnalysisRecord:
    """Persisted intelligence profile for one immutable repository version."""

    id: UUID
    repository_version_id: UUID
    analysis_version: int
    results: dict[str, object]
    file_count: int
    line_count: int
    created_at: datetime
    updated_at: datetime
