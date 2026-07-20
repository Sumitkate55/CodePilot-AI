"""Ports used by generated unit-test application use cases."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from codepilot_api.domain.explanations.entities import RepositoryFunction
from codepilot_api.domain.test_generation.entities import (
    GeneratedTestPayload,
    GeneratedTestRecord,
    TestGenerationContext,
    UnitTestFramework,
)


class UnitTestGenerationAgent(Protocol):
    """Generate one complete unit-test file from one selected function excerpt."""

    async def generate(self, context: TestGenerationContext) -> GeneratedTestPayload: ...


class GeneratedTestStore(Protocol):
    """Persist generated test files per immutable source version and function target."""

    async def list_by_version(
        self, repository_version_id: UUID
    ) -> tuple[GeneratedTestRecord, ...]: ...

    async def upsert(
        self,
        repository_version_id: UUID,
        function: RepositoryFunction,
        end_line: int,
        framework: UnitTestFramework,
        test_file_path: str,
        payload: GeneratedTestPayload,
    ) -> GeneratedTestRecord: ...
