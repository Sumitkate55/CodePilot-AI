"""Framework-independent project-summary records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProjectSummaryContext:
    """Bounded repository evidence supplied to the AI project-summary agent."""

    repository_id: UUID
    repository_version_id: UUID
    repository_name: str
    source_type: str
    remote_url: str | None
    analysis_results: dict[str, object]


@dataclass(frozen=True, slots=True)
class ProjectSummaryPayload:
    """Validated, structured content produced by a project-summary agent."""

    model: str
    prompt_version: int
    content: dict[str, object]


@dataclass(frozen=True, slots=True)
class ProjectSummaryRecord:
    """Persisted AI project summary for one immutable repository version."""

    id: UUID
    repository_version_id: UUID
    model: str
    prompt_version: int
    content: dict[str, object]
    created_at: datetime
    updated_at: datetime
