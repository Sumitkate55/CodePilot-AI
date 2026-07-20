"""SQLAlchemy adapter for repository code-review persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.reviews.entities import (
    CodeReviewCategory,
    CodeReviewFinding,
    CodeReviewSeverity,
    RepositoryCodeReviewPayload,
    RepositoryCodeReviewRecord,
)
from codepilot_api.infrastructure.database.models.repository_code_review import RepositoryCodeReview


class SqlAlchemyRepositoryCodeReviewStore:
    """Store one current review result for each immutable repository version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_version(
        self, repository_version_id: UUID
    ) -> RepositoryCodeReviewRecord | None:
        model = await self._session.scalar(
            select(RepositoryCodeReview).where(
                RepositoryCodeReview.repository_version_id == repository_version_id
            )
        )
        return self._to_record(model) if model else None

    async def upsert(
        self, repository_version_id: UUID, payload: RepositoryCodeReviewPayload
    ) -> RepositoryCodeReviewRecord:
        model = await self._session.scalar(
            select(RepositoryCodeReview).where(
                RepositoryCodeReview.repository_version_id == repository_version_id
            )
        )
        serialized_findings = [self._serialize_finding(finding) for finding in payload.findings]
        if model is None:
            model = RepositoryCodeReview(
                repository_version_id=repository_version_id,
                review_version=payload.review_version,
                findings=serialized_findings,
                scanned_file_count=payload.scanned_file_count,
            )
            self._session.add(model)
        else:
            model.review_version = payload.review_version
            model.findings = serialized_findings
            model.scanned_file_count = payload.scanned_file_count
            model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    @staticmethod
    def _serialize_finding(finding: CodeReviewFinding) -> dict[str, object]:
        return {
            "key": finding.key,
            "category": finding.category.value,
            "severity": finding.severity.value,
            "confidence": finding.confidence,
            "title": finding.title,
            "description": finding.description,
            "recommendation": finding.recommendation,
            "path": finding.path,
            "start_line": finding.start_line,
            "end_line": finding.end_line,
        }

    @staticmethod
    def _to_record(model: RepositoryCodeReview) -> RepositoryCodeReviewRecord:
        return RepositoryCodeReviewRecord(
            id=model.id,
            repository_version_id=model.repository_version_id,
            review_version=model.review_version,
            findings=tuple(
                CodeReviewFinding(
                    key=str(item["key"]),
                    category=CodeReviewCategory(str(item["category"])),
                    severity=CodeReviewSeverity(str(item["severity"])),
                    confidence=int(item["confidence"]),
                    title=str(item["title"]),
                    description=str(item["description"]),
                    recommendation=str(item["recommendation"]),
                    path=str(item["path"]),
                    start_line=int(item["start_line"]),
                    end_line=int(item["end_line"]),
                )
                for item in model.findings
                if isinstance(item, dict)
            ),
            scanned_file_count=model.scanned_file_count,
            created_at=SqlAlchemyRepositoryCodeReviewStore._as_utc(model.created_at),
            updated_at=SqlAlchemyRepositoryCodeReviewStore._as_utc(model.updated_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
