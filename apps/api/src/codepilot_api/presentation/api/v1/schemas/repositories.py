"""Repository management HTTP schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from codepilot_api.domain.chat.entities import (
    RepositoryChatAnswer,
    RepositoryChatIndexRecord,
    RepositoryChatIndexStatus,
)
from codepilot_api.domain.documentation.entities import DocumentationRecord
from codepilot_api.domain.explanations.entities import RepositoryFunction
from codepilot_api.domain.refactoring.entities import (
    RefactoringScore,
    RefactorProposalRecord,
    RefactorProposalStatus,
    RefactorRisk,
)
from codepilot_api.domain.repositories.architecture import (
    ArchitectureNodeKind,
    RepositoryArchitectureGraph,
    RepositorySourceFile,
)
from codepilot_api.domain.repositories.entities import (
    RepositoryAnalysisRecord,
    RepositoryRecord,
    RepositorySource,
    RepositoryVersionRecord,
)
from codepilot_api.domain.reviews.entities import (
    CodeReviewCategory,
    CodeReviewFinding,
    CodeReviewSeverity,
    RepositoryCodeReviewRecord,
)
from codepilot_api.domain.summaries.entities import ProjectSummaryRecord
from codepilot_api.domain.test_generation.entities import (
    GeneratedTestRecord,
    TestCoverageKind,
    UnitTestFramework,
)


class GitHubImportRequest(BaseModel):
    """Public GitHub URL import request."""

    model_config = ConfigDict(str_strip_whitespace=True)

    github_url: str = Field(min_length=19, max_length=2048)
    display_name: str | None = Field(default=None, max_length=120)


class RepositoryVersionResponse(BaseModel):
    """A stored immutable repository version."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    version_number: int
    source_type: RepositorySource
    source_url: str | None
    commit_sha: str | None
    file_count: int
    size_bytes: int
    created_at: datetime


class RepositoryResponse(BaseModel):
    """Repository summary and its version history."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    name: str
    source_type: RepositorySource
    remote_url: str | None
    created_at: datetime
    versions: list[RepositoryVersionResponse]


class RepositoryAnalysisResponse(BaseModel):
    """Persisted deterministic intelligence for the newest repository version."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    repository_version_id: UUID
    analysis_version: int
    results: dict[str, Any]
    file_count: int
    line_count: int
    created_at: datetime
    updated_at: datetime


class ArchitectureGraphNodeResponse(BaseModel):
    """One visual node for the architecture workspace."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: ArchitectureNodeKind
    label: str
    description: str
    file_path: str | None
    line: int | None


class ArchitectureGraphEdgeResponse(BaseModel):
    """One visual edge for the architecture workspace."""

    model_config = ConfigDict(frozen=True)

    id: str
    source: str
    target: str
    label: str | None


class RepositoryArchitectureGraphResponse(BaseModel):
    """A deterministic graph for the latest analyzed repository version."""

    model_config = ConfigDict(frozen=True)

    repository_version_id: UUID
    analysis_version: int
    nodes: list[ArchitectureGraphNodeResponse]
    edges: list[ArchitectureGraphEdgeResponse]


class RepositorySourceFileResponse(BaseModel):
    """A safe, bounded source-file preview selected from the architecture graph."""

    model_config = ConfigDict(frozen=True)

    repository_version_id: UUID
    path: str
    content: str
    language: str | None


class RepositoryFunctionResponse(BaseModel):
    """One detected function available to explain."""

    model_config = ConfigDict(frozen=True)

    name: str
    path: str
    line: int
    language: str | None


class CodeExplanationRequest(BaseModel):
    """A function location selected from the latest analyzed repository version."""

    model_config = ConfigDict(str_strip_whitespace=True)

    path: str = Field(min_length=1, max_length=1_024)
    line: int = Field(ge=1, le=1_000_000)


class CodeExplanationResponse(BaseModel):
    """A structured explanation grounded in one selected function excerpt."""

    model_config = ConfigDict(frozen=True)

    function: RepositoryFunctionResponse
    end_line: int
    model: str
    content: dict[str, Any]


class CodeReviewFindingResponse(BaseModel):
    """One source-backed repository-wide review finding."""

    model_config = ConfigDict(frozen=True)

    key: str
    category: CodeReviewCategory
    severity: CodeReviewSeverity
    confidence: int = Field(ge=0, le=100)
    title: str
    description: str
    recommendation: str
    path: str
    start_line: int
    end_line: int


class RepositoryCodeReviewResponse(BaseModel):
    """A persisted review of the latest immutable repository version."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    repository_version_id: UUID
    review_version: int
    findings: list[CodeReviewFindingResponse]
    scanned_file_count: int
    severity_counts: dict[str, int]
    category_counts: dict[str, int]
    created_at: datetime
    updated_at: datetime


class RefactorProposalRequest(BaseModel):
    """A code-review finding selected for an AI refactor proposal."""

    model_config = ConfigDict(str_strip_whitespace=True)

    finding_key: str = Field(min_length=8, max_length=64)


class RefactorProposalDecisionRequest(BaseModel):
    """An explicit user decision for one generated refactor proposal."""

    status: Literal[RefactorProposalStatus.ACCEPTED, RefactorProposalStatus.REJECTED]


class RefactorProposalResponse(BaseModel):
    """An auditable AI proposal and its Git-style diff."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    repository_version_id: UUID
    finding_key: str
    path: str
    start_line: int
    end_line: int
    source_start_line: int
    source_end_line: int
    title: str
    rationale: str
    original_source: str
    replacement_source: str
    diff: str
    model: str
    risk: RefactorRisk
    confidence: int = Field(ge=0, le=100)
    estimated_quality_gain: int = Field(ge=1, le=20)
    impact_summary: list[str]
    testing_steps: list[str]
    status: RefactorProposalStatus
    created_at: datetime
    updated_at: datetime


class RefactoringScoreResponse(BaseModel):
    """Live quality score and projected impact from stored refactor decisions."""

    model_config = ConfigDict(frozen=True)

    baseline: int = Field(ge=0, le=100)
    current: int = Field(ge=0, le=100)
    potential: int = Field(ge=0, le=100)
    accepted_quality_gain: int = Field(ge=0)
    available_quality_gain: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    proposed_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    remaining_finding_count: int = Field(ge=0)


class RepositoryRefactoringDashboardResponse(BaseModel):
    """Current review evidence, AI refactors, and a live repository score."""

    model_config = ConfigDict(frozen=True)

    review: RepositoryCodeReviewResponse
    score: RefactoringScoreResponse
    proposals: list[RefactorProposalResponse]


class TestGenerationRequest(BaseModel):
    """One analyzed function selected for source-grounded unit-test generation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    path: str = Field(min_length=1, max_length=1_024)
    line: int = Field(ge=1, le=1_000_000)


class TestGenerationTargetResponse(BaseModel):
    """A function supported by one deterministic unit-test framework."""

    model_config = ConfigDict(frozen=True)

    function: RepositoryFunctionResponse
    framework: UnitTestFramework


class GeneratedTestResponse(BaseModel):
    """One persisted complete generated test file for a repository function."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    repository_version_id: UUID
    function: RepositoryFunctionResponse
    framework: UnitTestFramework
    test_path: str
    model: str
    summary: str
    test_code: str
    coverage: list[TestCoverageKind]
    notes: list[str]
    created_at: datetime
    updated_at: datetime


class TestGenerationDashboardResponse(BaseModel):
    """Available test targets and persisted generated unit tests."""

    model_config = ConfigDict(frozen=True)

    targets: list[TestGenerationTargetResponse]
    generated_tests: list[GeneratedTestResponse]


class ProjectSummaryResponse(BaseModel):
    """Structured AI project summary for the latest repository version."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    repository_version_id: UUID
    model: str
    prompt_version: int
    content: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RepositoryDocumentationResponse(BaseModel):
    """Five generated Markdown documents for the latest repository source version."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    repository_version_id: UUID
    model: str
    prompt_version: int
    documents: dict[str, str]
    notes: list[str]
    created_at: datetime
    updated_at: datetime


class RepositoryChatIndexResponse(BaseModel):
    """The current vector-index status for the latest repository version."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    repository_version_id: UUID
    indexing_version: int
    status: RepositoryChatIndexStatus
    embedding_model: str
    chunk_count: int
    indexed_at: datetime | None
    failure_message: str | None
    updated_at: datetime


class RepositoryChatRequest(BaseModel):
    """One user question answered from the selected repository only."""

    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=3, max_length=4_000)


class RepositoryChatCitationResponse(BaseModel):
    """A cited source excerpt used to support a repository answer."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    path: str
    start_line: int
    end_line: int
    score: float
    excerpt: str


class RepositoryChatResponse(BaseModel):
    """A source-grounded response with only verified retrieved citations."""

    model_config = ConfigDict(frozen=True)

    answer: str
    citations: list[RepositoryChatCitationResponse]
    grounded: bool
    model: str | None


def version_response(version: RepositoryVersionRecord) -> RepositoryVersionResponse:
    """Map storage metadata to a safe public version response."""
    return RepositoryVersionResponse(
        id=version.id,
        version_number=version.version_number,
        source_type=version.source_type,
        source_url=version.source_url,
        commit_sha=version.commit_sha,
        file_count=version.file_count,
        size_bytes=version.size_bytes,
        created_at=version.created_at,
    )


def repository_response(repository: RepositoryRecord) -> RepositoryResponse:
    """Map a domain repository to its public response including history."""
    return RepositoryResponse(
        id=repository.id,
        name=repository.name,
        source_type=repository.source_type,
        remote_url=repository.remote_url,
        created_at=repository.created_at,
        versions=[version_response(version) for version in repository.versions],
    )


def repository_analysis_response(
    analysis: RepositoryAnalysisRecord,
) -> RepositoryAnalysisResponse:
    """Map persisted analysis records without exposing any source-file contents."""
    return RepositoryAnalysisResponse(
        id=analysis.id,
        repository_version_id=analysis.repository_version_id,
        analysis_version=analysis.analysis_version,
        results=analysis.results,
        file_count=analysis.file_count,
        line_count=analysis.line_count,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


def repository_architecture_graph_response(
    graph: RepositoryArchitectureGraph,
) -> RepositoryArchitectureGraphResponse:
    """Map a framework-independent graph to the public API response."""
    return RepositoryArchitectureGraphResponse(
        repository_version_id=graph.repository_version_id,
        analysis_version=graph.analysis_version,
        nodes=[
            ArchitectureGraphNodeResponse(
                id=node.id,
                kind=node.kind,
                label=node.label,
                description=node.description,
                file_path=node.file_path,
                line=node.line,
            )
            for node in graph.nodes
        ],
        edges=[
            ArchitectureGraphEdgeResponse(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                label=edge.label,
            )
            for edge in graph.edges
        ],
    )


def repository_source_file_response(file: RepositorySourceFile) -> RepositorySourceFileResponse:
    """Map a safe source preview without storage metadata."""
    return RepositorySourceFileResponse(
        repository_version_id=file.repository_version_id,
        path=file.path,
        content=file.content,
        language=file.language,
    )


def repository_function_response(function: RepositoryFunction) -> RepositoryFunctionResponse:
    """Map deterministic function metadata to the public API."""
    return RepositoryFunctionResponse(
        name=function.name,
        path=function.path,
        line=function.line,
        language=function.language,
    )


def code_review_finding_response(finding: CodeReviewFinding) -> CodeReviewFindingResponse:
    """Map a framework-independent review finding to the public API schema."""
    return CodeReviewFindingResponse(
        key=finding.key,
        category=finding.category,
        severity=finding.severity,
        confidence=finding.confidence,
        title=finding.title,
        description=finding.description,
        recommendation=finding.recommendation,
        path=finding.path,
        start_line=finding.start_line,
        end_line=finding.end_line,
    )


def repository_code_review_response(
    review: RepositoryCodeReviewRecord,
) -> RepositoryCodeReviewResponse:
    """Map persisted review data and expose only reviewed source locations."""
    severity_counts = {severity.value: 0 for severity in CodeReviewSeverity}
    category_counts = {category.value: 0 for category in CodeReviewCategory}
    for finding in review.findings:
        severity_counts[finding.severity.value] += 1
        category_counts[finding.category.value] += 1
    return RepositoryCodeReviewResponse(
        id=review.id,
        repository_version_id=review.repository_version_id,
        review_version=review.review_version,
        findings=[code_review_finding_response(finding) for finding in review.findings],
        scanned_file_count=review.scanned_file_count,
        severity_counts=severity_counts,
        category_counts=category_counts,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def refactor_proposal_response(proposal: RefactorProposalRecord) -> RefactorProposalResponse:
    """Map a stored proposal without exposing credentials or provider configuration."""
    return RefactorProposalResponse(
        id=proposal.id,
        repository_version_id=proposal.repository_version_id,
        finding_key=proposal.finding_key,
        path=proposal.path,
        start_line=proposal.start_line,
        end_line=proposal.end_line,
        source_start_line=proposal.source_start_line,
        source_end_line=proposal.source_end_line,
        title=proposal.title,
        rationale=proposal.rationale,
        original_source=proposal.original_source,
        replacement_source=proposal.replacement_source,
        diff=proposal.diff,
        model=proposal.model,
        risk=proposal.risk,
        confidence=proposal.confidence,
        estimated_quality_gain=proposal.estimated_quality_gain,
        impact_summary=list(proposal.impact_summary),
        testing_steps=list(proposal.testing_steps),
        status=proposal.status,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


def refactoring_score_response(score: RefactoringScore) -> RefactoringScoreResponse:
    """Map score fields so the client can render live impact without recomputing it."""
    return RefactoringScoreResponse(
        baseline=score.baseline,
        current=score.current,
        potential=score.potential,
        accepted_quality_gain=score.accepted_quality_gain,
        available_quality_gain=score.available_quality_gain,
        accepted_count=score.accepted_count,
        proposed_count=score.proposed_count,
        rejected_count=score.rejected_count,
        remaining_finding_count=score.remaining_finding_count,
    )


def repository_refactoring_dashboard_response(
    review: RepositoryCodeReviewRecord,
    proposals: tuple[RefactorProposalRecord, ...],
    score: RefactoringScore,
) -> RepositoryRefactoringDashboardResponse:
    """Map current refactoring-advisor data for the repository-detail workspace."""
    return RepositoryRefactoringDashboardResponse(
        review=repository_code_review_response(review),
        score=refactoring_score_response(score),
        proposals=[refactor_proposal_response(proposal) for proposal in proposals],
    )


def generated_test_response(record: GeneratedTestRecord) -> GeneratedTestResponse:
    """Map one persisted generated test to a client-safe response."""
    return GeneratedTestResponse(
        id=record.id,
        repository_version_id=record.repository_version_id,
        function=repository_function_response(record.function),
        framework=record.framework,
        test_path=record.test_file_path,
        model=record.model,
        summary=record.summary,
        test_code=record.test_code,
        coverage=list(record.coverage),
        notes=list(record.notes),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def test_generation_dashboard_response(
    targets: tuple[tuple[RepositoryFunction, UnitTestFramework], ...],
    generated_tests: tuple[GeneratedTestRecord, ...],
) -> TestGenerationDashboardResponse:
    """Map supported targets and saved test files for the repository workspace."""
    return TestGenerationDashboardResponse(
        targets=[
            TestGenerationTargetResponse(
                function=repository_function_response(function), framework=framework
            )
            for function, framework in targets
        ],
        generated_tests=[generated_test_response(record) for record in generated_tests],
    )


def project_summary_response(summary: ProjectSummaryRecord) -> ProjectSummaryResponse:
    """Map a persisted AI summary without exposing provider credentials or raw source files."""
    return ProjectSummaryResponse(
        id=summary.id,
        repository_version_id=summary.repository_version_id,
        model=summary.model,
        prompt_version=summary.prompt_version,
        content=summary.content,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )


def repository_documentation_response(
    documentation: DocumentationRecord,
) -> RepositoryDocumentationResponse:
    """Map persisted Markdown documentation without exposing provider configuration."""
    return RepositoryDocumentationResponse(
        id=documentation.id,
        repository_version_id=documentation.repository_version_id,
        model=documentation.model,
        prompt_version=documentation.prompt_version,
        documents=documentation.documents,
        notes=list(documentation.notes),
        created_at=documentation.created_at,
        updated_at=documentation.updated_at,
    )


def repository_chat_index_response(
    index: RepositoryChatIndexRecord,
) -> RepositoryChatIndexResponse:
    """Map index metadata without exposing Qdrant configuration."""
    return RepositoryChatIndexResponse(
        id=index.id,
        repository_version_id=index.repository_version_id,
        indexing_version=index.indexing_version,
        status=index.status,
        embedding_model=index.embedding_model,
        chunk_count=index.chunk_count,
        indexed_at=index.indexed_at,
        failure_message=index.failure_message,
        updated_at=index.updated_at,
    )


def repository_chat_response(answer: RepositoryChatAnswer) -> RepositoryChatResponse:
    """Map grounded answer citations to the client-facing response model."""
    return RepositoryChatResponse(
        answer=answer.answer,
        citations=[
            RepositoryChatCitationResponse(
                source_id=citation.source_id,
                path=citation.path,
                start_line=citation.start_line,
                end_line=citation.end_line,
                score=citation.score,
                excerpt=citation.excerpt,
            )
            for citation in answer.citations
        ],
        grounded=answer.grounded,
        model=answer.model,
    )
