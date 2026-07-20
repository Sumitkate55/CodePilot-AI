"""Framework-independent architecture graph records derived from repository intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ArchitectureNodeKind(StrEnum):
    """Visual kinds rendered by the architecture workspace."""

    REPOSITORY = "repository"
    FRONTEND = "frontend"
    BACKEND = "backend"
    SOURCE = "source"
    SERVICE = "service"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"


@dataclass(frozen=True, slots=True)
class ArchitectureGraphNode:
    """One navigable component of an analyzed repository."""

    id: str
    kind: ArchitectureNodeKind
    label: str
    description: str
    file_path: str | None = None
    line: int | None = None


@dataclass(frozen=True, slots=True)
class ArchitectureGraphEdge:
    """One evidence-derived relationship between architecture components."""

    id: str
    source: str
    target: str
    label: str | None = None


@dataclass(frozen=True, slots=True)
class RepositoryArchitectureGraph:
    """A graph for the latest immutable repository version."""

    repository_version_id: UUID
    analysis_version: int
    nodes: tuple[ArchitectureGraphNode, ...]
    edges: tuple[ArchitectureGraphEdge, ...]


@dataclass(frozen=True, slots=True)
class RepositorySourceFile:
    """A bounded, safe source preview opened from a graph node."""

    repository_version_id: UUID
    path: str
    content: str
    language: str | None
