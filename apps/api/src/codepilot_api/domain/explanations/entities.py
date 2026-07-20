"""Records used to explain a detected function from repository source."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RepositoryFunction:
    """A function previously detected by deterministic repository intelligence."""

    name: str
    path: str
    line: int
    language: str | None


@dataclass(frozen=True, slots=True)
class CodeExplanationContext:
    """Bounded source evidence provided to an AI explanation adapter."""

    repository_id: UUID
    repository_version_id: UUID
    function: RepositoryFunction
    end_line: int
    source: str


@dataclass(frozen=True, slots=True)
class CodeExplanationPayload:
    """A structured, source-grounded explanation returned by an AI adapter."""

    model: str
    content: dict[str, object]
