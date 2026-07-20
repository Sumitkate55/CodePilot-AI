"""Use cases for trusted refactor proposals and projected repository quality impact."""

from __future__ import annotations

import difflib
import re
from dataclasses import replace
from uuid import UUID

from codepilot_api.application.refactoring.contracts import RefactoringAgent, RefactorProposalStore
from codepilot_api.application.repositories.architecture_service import (
    RepositoryArchitectureService,
)
from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryCatalog,
)
from codepilot_api.application.reviews.contracts import RepositoryCodeReviewStore
from codepilot_api.domain.refactoring.entities import (
    RefactoringContext,
    RefactoringScore,
    RefactorProposalRecord,
    RefactorProposalStatus,
)
from codepilot_api.domain.refactoring.errors import (
    RefactoringDashboardNotFound,
    RefactoringFindingNotFound,
    RefactoringGenerationError,
    RefactorProposalNotFound,
)
from codepilot_api.domain.repositories.errors import RepositoryAnalysisNotFound, RepositoryNotFound
from codepilot_api.domain.reviews.entities import CodeReviewFinding, RepositoryCodeReviewRecord

SOURCE_CONTEXT_LINES = 12
MAX_PROPOSAL_SOURCE_LINES = 140
CREDENTIAL_LITERAL_PATTERN = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*[\"'])[^\"']+([\"'])"
)
SEVERITY_PENALTIES = {"critical": 20, "high": 10, "medium": 5, "low": 1}


class RefactoringAdvisorService:
    """Generate auditable proposals without mutating immutable stored source snapshots."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        review_store: RepositoryCodeReviewStore,
        proposal_store: RefactorProposalStore,
        source_reader: RepositoryArchitectureService,
        agent: RefactoringAgent,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._review_store = review_store
        self._proposal_store = proposal_store
        self._source_reader = source_reader
        self._agent = agent

    async def get_dashboard(self, owner_id: UUID, repository_id: UUID):
        """Return current review evidence, proposals, and projected quality impact."""
        repository, version, review = await self._latest_review(owner_id, repository_id)
        reviewed_keys = {finding.key for finding in review.findings}
        proposals = tuple(
            proposal
            for proposal in await self._proposal_store.list_by_version(version.id)
            if proposal.finding_key in reviewed_keys
        )
        return repository, review, proposals, self._score(review, proposals)

    async def generate_proposal(
        self, owner_id: UUID, repository_id: UUID, finding_key: str
    ) -> RefactorProposalRecord:
        """Generate or reuse one AI refactor for an exact stored review finding."""
        repository, version, review = await self._latest_review(owner_id, repository_id)
        finding = self._finding_for_key(review, finding_key)
        existing = await self._proposal_store.get_by_finding(version.id, finding.key)
        if existing is not None:
            return existing

        source_file = await self._source_reader.read_latest_file(
            owner_id, repository_id, finding.path
        )
        source_start_line, source_end_line, source = self._source_context(
            source_file.content, finding.start_line, finding.end_line
        )
        safe_source = self._redact_credentials(source)
        payload = await self._agent.propose(
            RefactoringContext(
                repository_id=repository.id,
                repository_version_id=version.id,
                finding=finding,
                source_start_line=source_start_line,
                source_end_line=source_end_line,
                source=safe_source,
            )
        )
        if self._normalized_source(safe_source) == self._normalized_source(
            payload.replacement_source
        ):
            raise RefactoringGenerationError(
                "The AI provider did not produce a meaningful source replacement. Please try again."
            )
        payload = replace(
            payload,
            estimated_quality_gain=min(
                payload.estimated_quality_gain, SEVERITY_PENALTIES[finding.severity.value]
            ),
        )
        diff = self._unified_diff(finding.path, safe_source, payload.replacement_source)
        return await self._proposal_store.create(
            repository_version_id=version.id,
            finding_key=finding.key,
            path=finding.path,
            start_line=finding.start_line,
            end_line=finding.end_line,
            source_start_line=source_start_line,
            source_end_line=source_end_line,
            original_source=safe_source,
            diff=diff,
            payload=payload,
        )

    async def decide_proposal(
        self,
        owner_id: UUID,
        repository_id: UUID,
        proposal_id: UUID,
        status: RefactorProposalStatus,
    ) -> RefactorProposalRecord:
        """Record an accept or reject decision for a proposal in the current source version."""
        _repository, version, _review = await self._latest_review(owner_id, repository_id)
        proposal = await self._proposal_store.set_status(version.id, proposal_id, status)
        if proposal is None:
            raise RefactorProposalNotFound
        return proposal

    async def _latest_review(self, owner_id: UUID, repository_id: UUID):
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        if not repository.versions:
            raise RepositoryAnalysisNotFound
        version = repository.versions[0]
        if await self._analysis_store.get_by_version(version.id) is None:
            raise RepositoryAnalysisNotFound
        review = await self._review_store.get_by_version(version.id)
        if review is None:
            raise RefactoringDashboardNotFound
        return repository, version, review

    @staticmethod
    def _finding_for_key(review: RepositoryCodeReviewRecord, finding_key: str) -> CodeReviewFinding:
        for finding in review.findings:
            if finding.key == finding_key:
                return finding
        raise RefactoringFindingNotFound

    @staticmethod
    def _source_context(content: str, start_line: int, end_line: int) -> tuple[int, int, str]:
        lines = content.splitlines()
        start_index = max(0, start_line - 1 - SOURCE_CONTEXT_LINES)
        end_index = min(len(lines), end_line + SOURCE_CONTEXT_LINES)
        if end_index - start_index > MAX_PROPOSAL_SOURCE_LINES:
            end_index = start_index + MAX_PROPOSAL_SOURCE_LINES
        source = "\n".join(lines[start_index:end_index])
        if not source:
            raise RefactoringFindingNotFound
        return start_index + 1, end_index, source

    @staticmethod
    def _redact_credentials(source: str) -> str:
        """Avoid sending credential values to either local or remote AI providers."""
        return CREDENTIAL_LITERAL_PATTERN.sub(r"\1<redacted>\2", source)

    @staticmethod
    def _unified_diff(path: str, original: str, replacement: str) -> str:
        """Create a Git-style diff that can be copied without mutating stored source."""
        return "\n".join(
            difflib.unified_diff(
                original.splitlines(),
                replacement.splitlines(),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )

    @staticmethod
    def _normalized_source(value: str) -> str:
        """Compare code while ignoring trailing whitespace from provider formatting."""
        return "\n".join(line.rstrip() for line in value.strip().splitlines())

    @staticmethod
    def _score(
        review: RepositoryCodeReviewRecord, proposals: tuple[RefactorProposalRecord, ...]
    ) -> RefactoringScore:
        baseline_penalty = sum(
            SEVERITY_PENALTIES[finding.severity.value] for finding in review.findings
        )
        baseline = max(0, 100 - baseline_penalty)
        accepted = [
            proposal for proposal in proposals if proposal.status == RefactorProposalStatus.ACCEPTED
        ]
        proposed = [
            proposal for proposal in proposals if proposal.status == RefactorProposalStatus.PROPOSED
        ]
        rejected = [
            proposal for proposal in proposals if proposal.status == RefactorProposalStatus.REJECTED
        ]
        accepted_gain = sum(proposal.estimated_quality_gain for proposal in accepted)
        available_gain = accepted_gain + sum(
            proposal.estimated_quality_gain for proposal in proposed
        )
        accepted_keys = {proposal.finding_key for proposal in accepted}
        return RefactoringScore(
            baseline=baseline,
            current=min(100, baseline + accepted_gain),
            potential=min(100, baseline + available_gain),
            accepted_quality_gain=accepted_gain,
            available_quality_gain=available_gain,
            accepted_count=len(accepted),
            proposed_count=len(proposed),
            rejected_count=len(rejected),
            remaining_finding_count=sum(
                1 for finding in review.findings if finding.key not in accepted_keys
            ),
        )
