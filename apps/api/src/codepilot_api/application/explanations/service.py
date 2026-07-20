"""Use cases for listing and source-groundedly explaining repository functions."""

from __future__ import annotations

from codepilot_api.application.explanations.contracts import (
    CodeExplanationAgent,
    RepositorySourceReader,
)
from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryCatalog,
)
from codepilot_api.domain.explanations.entities import (
    CodeExplanationContext,
    CodeExplanationPayload,
    RepositoryFunction,
)
from codepilot_api.domain.explanations.errors import CodeExplanationNotFound
from codepilot_api.domain.repositories.errors import RepositoryAnalysisNotFound, RepositoryNotFound

MAX_EXPLAINED_LINES = 220


class CodeExplanationService:
    """Ensure only detected, owned functions can be submitted to an AI provider."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        source_reader: RepositorySourceReader,
        agent: CodeExplanationAgent,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._source_reader = source_reader
        self._agent = agent

    async def list_latest_functions(
        self, owner_id, repository_id
    ) -> tuple[RepositoryFunction, ...]:
        """Return deterministic function metadata from the latest analyzed repository version."""
        _repository, _version, analysis = await self._latest_analysis(owner_id, repository_id)
        functions = analysis.results.get("symbols", {})
        function_items = functions.get("functions", []) if isinstance(functions, dict) else []
        return tuple(
            RepositoryFunction(
                name=str(item["name"]),
                path=str(item["path"]),
                line=int(item["line"]),
                language=item.get("language") if isinstance(item.get("language"), str) else None,
            )
            for item in function_items
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("path"), str)
            and isinstance(item.get("line"), int)
        )

    async def explain_latest(
        self, owner_id, repository_id, path: str, line: int
    ) -> tuple[RepositoryFunction, int, CodeExplanationPayload]:
        """Explain one function only after it matches persisted analysis evidence."""
        repository, version, _analysis = await self._latest_analysis(owner_id, repository_id)
        function = await self._find_function(owner_id, repository_id, path, line)
        source_file = await self._source_reader.read_latest_file(
            owner_id, repository_id, function.path
        )
        source, end_line = self._extract_function(source_file.content, function.line)
        payload = await self._agent.explain(
            CodeExplanationContext(
                repository_id=repository.id,
                repository_version_id=version.id,
                function=function,
                end_line=end_line,
                source=source,
            )
        )
        return function, end_line, payload

    async def _find_function(
        self, owner_id, repository_id, path: str, line: int
    ) -> RepositoryFunction:
        functions = await self.list_latest_functions(owner_id, repository_id)
        for function in functions:
            if function.path == path and function.line == line:
                return function
        raise CodeExplanationNotFound

    async def _latest_analysis(self, owner_id, repository_id):
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
    def _extract_function(content: str, start_line: int) -> tuple[str, int]:
        """Extract a conservative function block without parsing or executing source code."""
        lines = content.splitlines()
        start_index = start_line - 1
        if start_index < 0 or start_index >= len(lines):
            raise CodeExplanationNotFound
        first_line = lines[start_index]
        indentation = len(first_line) - len(first_line.lstrip())
        brace_depth = 0
        has_brace = False
        end_index = min(len(lines), start_index + MAX_EXPLAINED_LINES)
        for index in range(start_index, end_index):
            current = lines[index]
            if index > start_index and CodeExplanationService._starts_new_block(
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
            raise CodeExplanationNotFound
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
