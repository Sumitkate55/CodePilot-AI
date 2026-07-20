"""Ports for source-grounded refactoring proposals."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from codepilot_api.domain.refactoring.entities import (
    RefactoringContext,
    RefactorProposalPayload,
    RefactorProposalRecord,
    RefactorProposalStatus,
)


class RefactoringAgent(Protocol):
    """Generate one structured refactor from bounded source evidence."""

    async def propose(self, context: RefactoringContext) -> RefactorProposalPayload: ...


class RefactorProposalStore(Protocol):
    """Persist and retrieve one refactor proposal per review finding and source version."""

    async def list_by_version(
        self, repository_version_id: UUID
    ) -> tuple[RefactorProposalRecord, ...]: ...

    async def get_by_finding(
        self, repository_version_id: UUID, finding_key: str
    ) -> RefactorProposalRecord | None: ...

    async def create(
        self,
        repository_version_id: UUID,
        finding_key: str,
        path: str,
        start_line: int,
        end_line: int,
        source_start_line: int,
        source_end_line: int,
        original_source: str,
        diff: str,
        payload: RefactorProposalPayload,
    ) -> RefactorProposalRecord: ...

    async def set_status(
        self,
        repository_version_id: UUID,
        proposal_id: UUID,
        status: RefactorProposalStatus,
    ) -> RefactorProposalRecord | None: ...
