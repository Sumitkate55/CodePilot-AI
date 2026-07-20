"""Ports for structured function explanations."""

from __future__ import annotations

from typing import Protocol

from codepilot_api.domain.explanations.entities import (
    CodeExplanationContext,
    CodeExplanationPayload,
)
from codepilot_api.domain.repositories.architecture import RepositorySourceFile


class CodeExplanationAgent(Protocol):
    """Generate an explanation from bounded selected source evidence."""

    async def explain(self, context: CodeExplanationContext) -> CodeExplanationPayload: ...


class RepositorySourceReader(Protocol):
    """Read a bounded, safe text source file owned by the current user."""

    async def read_latest_file(
        self, owner_id, repository_id, requested_path: str
    ) -> RepositorySourceFile: ...
