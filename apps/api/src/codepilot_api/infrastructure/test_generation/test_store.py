"""SQLAlchemy adapter for generated unit-test persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.explanations.entities import RepositoryFunction
from codepilot_api.domain.test_generation.entities import (
    GeneratedTestPayload,
    GeneratedTestRecord,
    TestCoverageKind,
    UnitTestFramework,
)
from codepilot_api.infrastructure.database.models.generated_test import GeneratedTest


class SqlAlchemyGeneratedTestStore:
    """Store the latest test-generation result for every function and framework target."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_version(self, repository_version_id: UUID) -> tuple[GeneratedTestRecord, ...]:
        models = (
            await self._session.scalars(
                select(GeneratedTest)
                .where(GeneratedTest.repository_version_id == repository_version_id)
                .order_by(GeneratedTest.updated_at.desc())
            )
        ).all()
        return tuple(self._to_record(model) for model in models)

    async def upsert(
        self,
        repository_version_id: UUID,
        function: RepositoryFunction,
        end_line: int,
        framework: UnitTestFramework,
        test_file_path: str,
        payload: GeneratedTestPayload,
    ) -> GeneratedTestRecord:
        model = await self._session.scalar(
            select(GeneratedTest).where(
                GeneratedTest.repository_version_id == repository_version_id,
                GeneratedTest.function_path == function.path,
                GeneratedTest.function_line == function.line,
                GeneratedTest.framework == framework.value,
            )
        )
        if model is None:
            model = GeneratedTest(
                repository_version_id=repository_version_id,
                function_name=function.name,
                function_path=function.path,
                function_line=function.line,
                function_language=function.language,
                end_line=end_line,
                framework=framework.value,
                test_file_path=test_file_path,
                model=payload.model,
                summary=payload.summary,
                test_code=payload.test_code,
                coverage=[kind.value for kind in payload.coverage],
                notes=list(payload.notes),
            )
            self._session.add(model)
        else:
            model.function_name = function.name
            model.function_language = function.language
            model.end_line = end_line
            model.test_file_path = test_file_path
            model.model = payload.model
            model.summary = payload.summary
            model.test_code = payload.test_code
            model.coverage = [kind.value for kind in payload.coverage]
            model.notes = list(payload.notes)
            model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(model)

    @staticmethod
    def _to_record(model: GeneratedTest) -> GeneratedTestRecord:
        return GeneratedTestRecord(
            id=model.id,
            repository_version_id=model.repository_version_id,
            function=RepositoryFunction(
                name=model.function_name,
                path=model.function_path,
                line=model.function_line,
                language=model.function_language,
            ),
            end_line=model.end_line,
            framework=UnitTestFramework(model.framework),
            test_file_path=model.test_file_path,
            model=model.model,
            summary=model.summary,
            test_code=model.test_code,
            coverage=tuple(TestCoverageKind(value) for value in model.coverage),
            notes=tuple(str(value) for value in model.notes),
            created_at=SqlAlchemyGeneratedTestStore._as_utc(model.created_at),
            updated_at=SqlAlchemyGeneratedTestStore._as_utc(model.updated_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
