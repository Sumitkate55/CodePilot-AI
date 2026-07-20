"""Use cases for generating framework-matched unit tests from selected repository functions."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from uuid import UUID

from codepilot_api.application.explanations.contracts import RepositorySourceReader
from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryCatalog,
)
from codepilot_api.application.test_generation.contracts import (
    GeneratedTestStore,
    UnitTestGenerationAgent,
)
from codepilot_api.domain.explanations.entities import RepositoryFunction
from codepilot_api.domain.repositories.errors import RepositoryAnalysisNotFound, RepositoryNotFound
from codepilot_api.domain.test_generation.entities import (
    GeneratedTestRecord,
    TestGenerationContext,
    UnitTestFramework,
)
from codepilot_api.domain.test_generation.errors import (
    TestGenerationTargetNotFound,
)

MAX_TEST_TARGET_LINES = 220
CREDENTIAL_LITERAL_PATTERN = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*[\"'])[^\"']+([\"'])"
)
FRAMEWORK_BY_LANGUAGE = {
    "Python": UnitTestFramework.PYTEST,
    "JavaScript": UnitTestFramework.JEST,
    "TypeScript": UnitTestFramework.JEST,
    "Java": UnitTestFramework.JUNIT,
}


class UnitTestGenerationService:
    """Ensure tests are generated only for detected functions in owned stored source."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        source_reader: RepositorySourceReader,
        generated_test_store: GeneratedTestStore,
        agent: UnitTestGenerationAgent,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._source_reader = source_reader
        self._generated_test_store = generated_test_store
        self._agent = agent

    async def list_dashboard(self, owner_id: UUID, repository_id: UUID):
        """Return supported source-function targets and tests for the latest source version."""
        _repository, version, analysis = await self._latest_analysis(owner_id, repository_id)
        targets = self._supported_functions(analysis.results)
        generated = await self._generated_test_store.list_by_version(version.id)
        target_keys = {(target.path, target.line) for target, _framework in targets}
        return targets, tuple(
            item
            for item in generated
            if (item.function.path, item.function.line) in target_keys
        )

    async def generate(
        self, owner_id: UUID, repository_id: UUID, path: str, line: int
    ) -> GeneratedTestRecord:
        """Generate and persist a test file for an exact detected function target."""
        repository, version, analysis = await self._latest_analysis(owner_id, repository_id)
        function, framework = self._target_for(analysis.results, path, line)
        source_file = await self._source_reader.read_latest_file(
            owner_id, repository_id, function.path
        )
        source, end_line = self._extract_function(source_file.content, function.line)
        test_file_path = self._test_file_path(function.path, function.name, framework)
        payload = await self._agent.generate(
            TestGenerationContext(
                repository_id=repository.id,
                repository_version_id=version.id,
                function=function,
                end_line=end_line,
                framework=framework,
                test_file_path=test_file_path,
                source=self._redact_credentials(source),
            )
        )
        return await self._generated_test_store.upsert(
            repository_version_id=version.id,
            function=function,
            end_line=end_line,
            framework=framework,
            test_file_path=test_file_path,
            payload=payload,
        )

    async def _latest_analysis(self, owner_id: UUID, repository_id: UUID):
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        if not repository.versions:
            raise RepositoryAnalysisNotFound
        version = repository.versions[0]
        analysis = await self._analysis_store.get_by_version(version.id)
        if analysis is None:
            raise RepositoryAnalysisNotFound
        return repository, version, analysis

    @staticmethod
    def _supported_functions(
        results: dict[str, object],
    ) -> tuple[tuple[RepositoryFunction, UnitTestFramework], ...]:
        symbols = results.get("symbols", {})
        raw_functions = symbols.get("functions", []) if isinstance(symbols, dict) else []
        targets: list[tuple[RepositoryFunction, UnitTestFramework]] = []
        for item in raw_functions:
            if not isinstance(item, dict):
                continue
            language = item.get("language")
            framework = FRAMEWORK_BY_LANGUAGE.get(language) if isinstance(language, str) else None
            if framework is None:
                continue
            if not (
                isinstance(item.get("name"), str)
                and isinstance(item.get("path"), str)
                and isinstance(item.get("line"), int)
            ):
                continue
            targets.append(
                (
                    RepositoryFunction(
                        name=item["name"],
                        path=item["path"],
                        line=item["line"],
                        language=language,
                    ),
                    framework,
                )
            )
        return tuple(targets)

    @classmethod
    def _target_for(
        cls, results: dict[str, object], path: str, line: int
    ) -> tuple[RepositoryFunction, UnitTestFramework]:
        for function, framework in cls._supported_functions(results):
            if function.path == path and function.line == line:
                return function, framework
        raise TestGenerationTargetNotFound

    @staticmethod
    def _extract_function(content: str, start_line: int) -> tuple[str, int]:
        """Extract a bounded source function without parsing or executing repository code."""
        lines = content.splitlines()
        start_index = start_line - 1
        if start_index < 0 or start_index >= len(lines):
            raise TestGenerationTargetNotFound
        first_line = lines[start_index]
        indentation = len(first_line) - len(first_line.lstrip())
        brace_depth = 0
        has_brace = False
        end_index = min(len(lines), start_index + MAX_TEST_TARGET_LINES)
        for index in range(start_index, end_index):
            current = lines[index]
            if index > start_index and UnitTestGenerationService._starts_new_block(
                current, indentation, has_brace, brace_depth
            ):
                end_index = index
                break
            brace_depth += current.count("{") - current.count("}")
            has_brace = has_brace or "{" in current
            if index > start_index and has_brace and brace_depth <= 0:
                end_index = index + 1
                break
        source = "\n".join(lines[start_index:end_index]).strip()
        if not source:
            raise TestGenerationTargetNotFound
        return source, end_index

    @staticmethod
    def _starts_new_block(line: str, indentation: int, has_brace: bool, brace_depth: int) -> bool:
        stripped = line.lstrip()
        current_indentation = len(line) - len(stripped)
        if has_brace and brace_depth > 0:
            return False
        return current_indentation <= indentation and stripped.startswith(
            ("async def ", "def ", "class ", "export ", "function ", "public ", "private ")
        )

    @staticmethod
    def _test_file_path(path: str, function_name: str, framework: UnitTestFramework) -> str:
        source_path = PurePosixPath(path)
        stem = re.sub(r"[^A-Za-z0-9_]", "_", source_path.stem or function_name)
        if framework == UnitTestFramework.PYTEST:
            return f"tests/test_{stem}.py"
        if framework == UnitTestFramework.JEST:
            return f"__tests__/{stem}.test.js"
        return f"src/test/java/{stem[:1].upper()}{stem[1:]}Test.java"

    @staticmethod
    def _redact_credentials(source: str) -> str:
        """Prevent credential literals in source code from leaving the API process."""
        return CREDENTIAL_LITERAL_PATTERN.sub(r"\1<redacted>\2", source)
