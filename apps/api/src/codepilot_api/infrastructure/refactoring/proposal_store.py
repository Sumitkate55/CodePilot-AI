"""SQLAlchemy adapter for refactoring proposal persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.refactoring.entities import (
    RefactorProposalPayload,
    RefactorProposalRecord,
    RefactorProposalStatus,
    RefactorRisk,
)
from codepilot_api.infrastructure.database.models.refactor_proposal import RefactorProposal


class SqlAlchemyRefactorProposalStore:
    """Persist refactor proposals and explicit accept/reject decisions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_version(
        self, repository_version_id: UUID
    ) -> tuple[RefactorProposalRecord, ...]:
        models = (
            await self._session.scalars(
                select(RefactorProposal)
                .where(RefactorProposal.repository_version_id == repository_version_id)
                .order_by(RefactorProposal.updated_at.desc())
            )
        ).all()
        return tuple(self._to_record(model) for model in models)

    async def get_by_finding(
        self, repository_version_id: UUID, finding_key: str
    ) -> RefactorProposalRecord | None:
        model = await self._session.scalar(
            select(RefactorProposal).where(
                RefactorProposal.repository_version_id == repository_version_id,
                RefactorProposal.finding_key == finding_key,
            )
        )
        return self._to_record(model) if model else None

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
    ) -> RefactorProposalRecord:
        model = RefactorProposal(
            repository_version_id=repository_version_id,
            finding_key=finding_key,
            path=path,
            start_line=start_line,
            end_line=end_line,
            source_start_line=source_start_line,
            source_end_line=source_end_line,
            title=payload.title,
            rationale=payload.rationale,
            original_source=original_source,
            replacement_source=payload.replacement_source,
            diff=diff,
            model=payload.model,
            risk=payload.risk.value,
            confidence=payload.confidence,
            estimated_quality_gain=payload.estimated_quality_gain,
            impact_summary=list(payload.impact_summary),
            testing_steps=list(payload.testing_steps),
            status=RefactorProposalStatus.PROPOSED.value,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_record(model)

    async def set_status(
        self,
        repository_version_id: UUID,
        proposal_id: UUID,
        status: RefactorProposalStatus,
    ) -> RefactorProposalRecord | None:
        model = await self._session.scalar(
            select(RefactorProposal).where(
                RefactorProposal.id == proposal_id,
                RefactorProposal.repository_version_id == repository_version_id,
            )
        )
        if model is None:
            return None
        model.status = status.value
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    @staticmethod
    def _to_record(model: RefactorProposal) -> RefactorProposalRecord:
        return RefactorProposalRecord(
            id=model.id,
            repository_version_id=model.repository_version_id,
            finding_key=model.finding_key,
            path=model.path,
            start_line=model.start_line,
            end_line=model.end_line,
            source_start_line=model.source_start_line,
            source_end_line=model.source_end_line,
            title=model.title,
            rationale=model.rationale,
            original_source=model.original_source,
            replacement_source=model.replacement_source,
            diff=model.diff,
            model=model.model,
            risk=RefactorRisk(model.risk),
            confidence=model.confidence,
            estimated_quality_gain=model.estimated_quality_gain,
            impact_summary=tuple(str(value) for value in model.impact_summary),
            testing_steps=tuple(str(value) for value in model.testing_steps),
            status=RefactorProposalStatus(model.status),
            created_at=SqlAlchemyRefactorProposalStore._as_utc(model.created_at),
            updated_at=SqlAlchemyRefactorProposalStore._as_utc(model.updated_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
