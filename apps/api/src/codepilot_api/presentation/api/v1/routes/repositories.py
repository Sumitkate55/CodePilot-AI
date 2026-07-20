"""Authenticated repository upload, history, and deletion endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.application.chat.service import RepositoryChatService
from codepilot_api.application.documentation.service import DocumentationService
from codepilot_api.application.explanations.service import CodeExplanationService
from codepilot_api.application.refactoring.service import RefactoringAdvisorService
from codepilot_api.application.repositories.architecture_service import (
    RepositoryArchitectureService,
)
from codepilot_api.application.repositories.intelligence_service import (
    RepositoryIntelligenceService,
)
from codepilot_api.application.repositories.service import RepositoryService
from codepilot_api.application.reviews.service import RepositoryCodeReviewService
from codepilot_api.application.summaries.service import ProjectSummaryService
from codepilot_api.application.test_generation.service import UnitTestGenerationService
from codepilot_api.domain.auth.entities import AuthUser
from codepilot_api.domain.chat.errors import (
    RepositoryChatConfigurationError,
    RepositoryChatGenerationError,
    RepositoryChatIndexingError,
    RepositoryChatNotIndexed,
)
from codepilot_api.domain.documentation.errors import (
    DocumentationConfigurationError,
    DocumentationGenerationError,
    DocumentationNotFound,
)
from codepilot_api.domain.explanations.errors import (
    CodeExplanationConfigurationError,
    CodeExplanationGenerationError,
    CodeExplanationNotFound,
)
from codepilot_api.domain.refactoring.entities import RefactorProposalStatus
from codepilot_api.domain.refactoring.errors import (
    RefactoringConfigurationError,
    RefactoringDashboardNotFound,
    RefactoringFindingNotFound,
    RefactoringGenerationError,
    RefactorProposalNotFound,
)
from codepilot_api.domain.repositories.errors import (
    RepositoryAnalysisError,
    RepositoryAnalysisNotFound,
    RepositoryImportError,
    RepositoryNotFound,
)
from codepilot_api.domain.repositories.identifiers import (
    normalize_github_url,
    normalize_repository_name,
    repository_name_from_filename,
)
from codepilot_api.domain.reviews.errors import (
    RepositoryCodeReviewError,
    RepositoryCodeReviewNotFound,
)
from codepilot_api.domain.summaries.errors import (
    ProjectSummaryConfigurationError,
    ProjectSummaryGenerationError,
    ProjectSummaryNotFound,
    ProjectSummaryRateLimitedError,
)
from codepilot_api.domain.test_generation.errors import (
    TestGenerationConfigurationError,
    TestGenerationError,
    TestGenerationTargetNotFound,
)
from codepilot_api.infrastructure.repositories.importer import SecureWorkspaceImporter
from codepilot_api.infrastructure.repositories.storage import LocalRepositoryStorage
from codepilot_api.presentation.api.v1.schemas.repositories import (
    CodeExplanationRequest,
    CodeExplanationResponse,
    GeneratedTestResponse,
    GitHubImportRequest,
    ProjectSummaryResponse,
    RefactorProposalDecisionRequest,
    RefactorProposalRequest,
    RefactorProposalResponse,
    RepositoryAnalysisResponse,
    RepositoryArchitectureGraphResponse,
    RepositoryChatIndexResponse,
    RepositoryChatRequest,
    RepositoryChatResponse,
    RepositoryCodeReviewResponse,
    RepositoryDocumentationResponse,
    RepositoryFunctionResponse,
    RepositoryRefactoringDashboardResponse,
    RepositoryResponse,
    RepositorySourceFileResponse,
    RepositoryVersionResponse,
    TestGenerationDashboardResponse,
    TestGenerationRequest,
    generated_test_response,
    project_summary_response,
    refactor_proposal_response,
    repository_analysis_response,
    repository_architecture_graph_response,
    repository_chat_index_response,
    repository_chat_response,
    repository_code_review_response,
    repository_documentation_response,
    repository_function_response,
    repository_refactoring_dashboard_response,
    repository_response,
    repository_source_file_response,
    test_generation_dashboard_response,
    version_response,
)
from codepilot_api.presentation.dependencies import (
    get_code_explanation_service,
    get_current_user,
    get_db_session,
    get_documentation_service,
    get_project_summary_service,
    get_refactoring_advisor_service,
    get_repository_architecture_service,
    get_repository_chat_service,
    get_repository_code_review_service,
    get_repository_intelligence_service,
    get_repository_service,
    get_unit_test_generation_service,
)
from codepilot_api.presentation.errors import AppError

router = APIRouter(prefix="/repositories")

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
RepositoryManager = Annotated[RepositoryService, Depends(get_repository_service)]
RepositoryIntelligence = Annotated[
    RepositoryIntelligenceService, Depends(get_repository_intelligence_service)
]
RepositoryArchitecture = Annotated[
    RepositoryArchitectureService, Depends(get_repository_architecture_service)
]
RepositoryCodeReviewManager = Annotated[
    RepositoryCodeReviewService, Depends(get_repository_code_review_service)
]
RefactoringAdvisor = Annotated[RefactoringAdvisorService, Depends(get_refactoring_advisor_service)]
UnitTestGenerator = Annotated[
    UnitTestGenerationService, Depends(get_unit_test_generation_service)
]
CodeExplanationManager = Annotated[CodeExplanationService, Depends(get_code_explanation_service)]
ProjectSummaryManager = Annotated[ProjectSummaryService, Depends(get_project_summary_service)]
RepositoryChatManager = Annotated[RepositoryChatService, Depends(get_repository_chat_service)]
DocumentationManager = Annotated[DocumentationService, Depends(get_documentation_service)]
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]


async def commit_repository_change(session: AsyncSession) -> None:
    """Commit repository metadata and normalize concurrent import conflicts."""
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise AppError(
            code="repository_conflict",
            message="The repository changed concurrently. Please retry the import.",
            status_code=status.HTTP_409_CONFLICT,
        ) from error


def import_error(error: RepositoryImportError) -> AppError:
    """Convert safe source validation/import errors into a stable public API error."""
    return AppError(
        code="invalid_repository_source",
        message=str(error),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


@router.post(
    "/import/github", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED
)
async def import_github_repository(
    payload: GitHubImportRequest,
    current_user: CurrentUser,
    service: RepositoryManager,
    session: DatabaseSession,
) -> RepositoryResponse:
    """Clone a public GitHub repository and add a version to its import history."""
    try:
        source_url, derived_name = normalize_github_url(payload.github_url)
        name = (
            normalize_repository_name(payload.display_name)
            if payload.display_name
            else derived_name
        )
        repository = await service.import_github(current_user.id, source_url, name)
    except RepositoryImportError as error:
        raise import_error(error) from error

    await commit_repository_change(session)
    return repository_response(repository)


@router.post("/upload", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def upload_repository_archive(
    request: Request,
    file: Annotated[UploadFile, File(description="A ZIP archive containing one repository")],
    current_user: CurrentUser,
    service: RepositoryManager,
    session: DatabaseSession,
    repository_name: Annotated[str | None, Form()] = None,
) -> RepositoryResponse:
    """Securely stream, extract, and store a ZIP repository upload."""
    settings = request.app.state.settings
    storage = LocalRepositoryStorage(settings.repository_storage_root)
    importer = SecureWorkspaceImporter(settings)
    try:
        name = (
            normalize_repository_name(repository_name)
            if repository_name
            else repository_name_from_filename(file.filename)
        )
        with storage.staging_directory() as staging:
            archive_path = await importer.save_upload(file, staging / "upload.zip")
            repository = await service.import_zip(current_user.id, name, archive_path)
    except RepositoryImportError as error:
        raise import_error(error) from error

    await commit_repository_change(session)
    return repository_response(repository)


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    current_user: CurrentUser, service: RepositoryManager
) -> list[RepositoryResponse]:
    """List every repository owned by the authenticated user."""
    repositories = await service.list_repositories(current_user.id)
    return [repository_response(repository) for repository in repositories]


@router.post("/{repository_id}/analyze", response_model=RepositoryAnalysisResponse)
async def analyze_repository(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryIntelligence,
    session: DatabaseSession,
) -> RepositoryAnalysisResponse:
    """Analyze the latest immutable source version and persist its intelligence profile."""
    try:
        analysis = await service.analyze_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisError as error:
        raise AppError(
            "repository_analysis_failed", str(error), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from error
    await commit_repository_change(session)
    return repository_analysis_response(analysis)


@router.get("/{repository_id}/analysis", response_model=RepositoryAnalysisResponse)
async def get_repository_analysis(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryIntelligence,
) -> RepositoryAnalysisResponse:
    """Return saved intelligence for the latest immutable source version."""
    try:
        analysis = await service.get_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "This repository has not been analyzed yet.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return repository_analysis_response(analysis)


@router.get(
    "/{repository_id}/architecture-graph", response_model=RepositoryArchitectureGraphResponse
)
async def get_repository_architecture_graph(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryArchitecture,
) -> RepositoryArchitectureGraphResponse:
    """Return a deterministic, source-intelligence-derived architecture graph."""
    try:
        graph = await service.get_latest_graph(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before opening its architecture graph.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return repository_architecture_graph_response(graph)


@router.get("/{repository_id}/files/{file_path:path}", response_model=RepositorySourceFileResponse)
async def get_repository_source_file(
    repository_id: UUID,
    file_path: str,
    current_user: CurrentUser,
    service: RepositoryArchitecture,
) -> RepositorySourceFileResponse:
    """Open a safe, bounded text source preview selected from the architecture graph."""
    try:
        source_file = await service.read_latest_file(current_user.id, repository_id, file_path)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_file_unavailable",
            "The repository has no stored source version.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RepositoryAnalysisError as error:
        raise AppError(
            "repository_file_unavailable", str(error), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from error
    return repository_source_file_response(source_file)


@router.get("/{repository_id}/functions", response_model=list[RepositoryFunctionResponse])
async def list_repository_functions(
    repository_id: UUID,
    current_user: CurrentUser,
    service: CodeExplanationManager,
) -> list[RepositoryFunctionResponse]:
    """List functions detected in the latest analysis and eligible for explanation."""
    try:
        functions = await service.list_latest_functions(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before explaining its functions.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return [repository_function_response(function) for function in functions]


@router.post("/{repository_id}/explain-code", response_model=CodeExplanationResponse)
async def explain_repository_code(
    repository_id: UUID,
    payload: CodeExplanationRequest,
    current_user: CurrentUser,
    service: CodeExplanationManager,
) -> CodeExplanationResponse:
    """Explain one detected function using only its selected source excerpt."""
    try:
        function, end_line, explanation = await service.explain_latest(
            current_user.id, repository_id, payload.path, payload.line
        )
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before explaining its functions.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except CodeExplanationNotFound as error:
        raise AppError(
            "function_not_found",
            "Select a function detected in the latest repository analysis.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except CodeExplanationConfigurationError as error:
        raise AppError(
            "code_explanation_not_configured", str(error), status.HTTP_503_SERVICE_UNAVAILABLE
        ) from error
    except (CodeExplanationGenerationError, RepositoryAnalysisError) as error:
        raise AppError(
            "code_explanation_unavailable", str(error), status.HTTP_502_BAD_GATEWAY
        ) from error
    return CodeExplanationResponse(
        function=repository_function_response(function),
        end_line=end_line,
        model=explanation.model,
        content=explanation.content,
    )


@router.post("/{repository_id}/review", response_model=RepositoryCodeReviewResponse)
async def review_repository_code(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryCodeReviewManager,
    session: DatabaseSession,
) -> RepositoryCodeReviewResponse:
    """Run a bounded, source-grounded review of the latest analyzed repository version."""
    try:
        review = await service.review_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before running code review.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RepositoryCodeReviewError as error:
        raise AppError(
            "repository_code_review_failed", str(error), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from error
    await commit_repository_change(session)
    return repository_code_review_response(review)


@router.get("/{repository_id}/review", response_model=RepositoryCodeReviewResponse)
async def get_repository_code_review(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryCodeReviewManager,
) -> RepositoryCodeReviewResponse:
    """Return the latest saved code review for the authenticated repository owner."""
    try:
        review = await service.get_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before opening code review.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RepositoryCodeReviewNotFound as error:
        raise AppError(
            "repository_code_review_not_found",
            "This repository has not been reviewed yet.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return repository_code_review_response(review)


@router.get("/{repository_id}/refactoring", response_model=RepositoryRefactoringDashboardResponse)
async def get_refactoring_dashboard(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RefactoringAdvisor,
) -> RepositoryRefactoringDashboardResponse:
    """Return current findings, generated refactors, and a live quality-impact report."""
    try:
        _repository, review, proposals, score = await service.get_dashboard(
            current_user.id, repository_id
        )
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before opening the refactoring advisor.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RefactoringDashboardNotFound as error:
        raise AppError(
            "repository_code_review_not_found",
            "Run repository code review before opening the refactoring advisor.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return repository_refactoring_dashboard_response(review, proposals, score)


@router.post("/{repository_id}/refactoring/proposals", response_model=RefactorProposalResponse)
async def generate_refactor_proposal(
    repository_id: UUID,
    payload: RefactorProposalRequest,
    current_user: CurrentUser,
    service: RefactoringAdvisor,
    session: DatabaseSession,
) -> RefactorProposalResponse:
    """Generate one AI proposal and Git-style diff for an exact review finding."""
    try:
        proposal = await service.generate_proposal(
            current_user.id, repository_id, payload.finding_key
        )
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before generating a refactor.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RefactoringDashboardNotFound as error:
        raise AppError(
            "repository_code_review_not_found",
            "Run repository code review before generating a refactor.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RefactoringFindingNotFound as error:
        raise AppError(
            "refactoring_finding_not_found",
            "Select a finding from the latest repository code review.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RefactoringConfigurationError as error:
        raise AppError(
            "refactoring_not_configured", str(error), status.HTTP_503_SERVICE_UNAVAILABLE
        ) from error
    except (RefactoringGenerationError, RepositoryAnalysisError) as error:
        raise AppError(
            "refactoring_unavailable", str(error), status.HTTP_502_BAD_GATEWAY
        ) from error
    await commit_repository_change(session)
    return refactor_proposal_response(proposal)


@router.patch(
    "/{repository_id}/refactoring/proposals/{proposal_id}", response_model=RefactorProposalResponse
)
async def decide_refactor_proposal(
    repository_id: UUID,
    proposal_id: UUID,
    payload: RefactorProposalDecisionRequest,
    current_user: CurrentUser,
    service: RefactoringAdvisor,
    session: DatabaseSession,
) -> RefactorProposalResponse:
    """Persist an explicit accept or reject decision without mutating stored source."""
    try:
        proposal = await service.decide_proposal(
            current_user.id,
            repository_id,
            proposal_id,
            RefactorProposalStatus(payload.status),
        )
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before deciding on a refactor.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RefactoringDashboardNotFound as error:
        raise AppError(
            "repository_code_review_not_found",
            "Run repository code review before deciding on a refactor.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except RefactorProposalNotFound as error:
        raise AppError(
            "refactor_proposal_not_found",
            "This refactor proposal is unavailable for the latest repository version.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    await commit_repository_change(session)
    return refactor_proposal_response(proposal)


@router.get("/{repository_id}/test-generation", response_model=TestGenerationDashboardResponse)
async def get_test_generation_dashboard(
    repository_id: UUID,
    current_user: CurrentUser,
    service: UnitTestGenerator,
) -> TestGenerationDashboardResponse:
    """Return testable functions and latest generated tests for the owned source version."""
    try:
        targets, generated_tests = await service.list_dashboard(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before generating unit tests.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return test_generation_dashboard_response(targets, generated_tests)


@router.post("/{repository_id}/test-generation", response_model=GeneratedTestResponse)
async def generate_unit_tests(
    repository_id: UUID,
    payload: TestGenerationRequest,
    current_user: CurrentUser,
    service: UnitTestGenerator,
    session: DatabaseSession,
) -> GeneratedTestResponse:
    """Generate and persist a complete test file for one supported source function."""
    try:
        generated_test = await service.generate(
            current_user.id, repository_id, payload.path, payload.line
        )
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisNotFound as error:
        raise AppError(
            "repository_analysis_not_found",
            "Analyze this repository before generating unit tests.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except TestGenerationTargetNotFound as error:
        raise AppError(
            "test_generation_target_not_found",
            "Select a detected Python, JavaScript, TypeScript, or Java function.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    except TestGenerationConfigurationError as error:
        raise AppError(
            "test_generation_not_configured", str(error), status.HTTP_503_SERVICE_UNAVAILABLE
        ) from error
    except (TestGenerationError, RepositoryAnalysisError) as error:
        raise AppError(
            "test_generation_unavailable", str(error), status.HTTP_502_BAD_GATEWAY
        ) from error
    await commit_repository_change(session)
    return generated_test_response(generated_test)


@router.post("/{repository_id}/summary", response_model=ProjectSummaryResponse)
async def generate_project_summary(
    repository_id: UUID,
    current_user: CurrentUser,
    service: ProjectSummaryManager,
    session: DatabaseSession,
) -> ProjectSummaryResponse:
    """Generate and persist a GPT-5 summary for the latest immutable source version."""
    try:
        summary = await service.generate_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryAnalysisError as error:
        raise AppError(
            "repository_analysis_failed", str(error), status.HTTP_422_UNPROCESSABLE_CONTENT
        ) from error
    except ProjectSummaryNotFound as error:
        raise AppError(
            "project_summary_unavailable",
            "The repository has no stored source version to summarize.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ) from error
    except ProjectSummaryConfigurationError as error:
        raise AppError(
            "ai_not_configured", str(error), status.HTTP_503_SERVICE_UNAVAILABLE
        ) from error
    except ProjectSummaryRateLimitedError as error:
        headers = (
            {"Retry-After": str(error.retry_after_seconds)}
            if error.retry_after_seconds is not None
            else None
        )
        raise AppError(
            "ai_rate_limited",
            str(error),
            status.HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
        ) from error
    except ProjectSummaryGenerationError as error:
        raise AppError(
            "project_summary_unavailable", str(error), status.HTTP_502_BAD_GATEWAY
        ) from error
    await commit_repository_change(session)
    return project_summary_response(summary)


@router.post("/{repository_id}/documentation", response_model=RepositoryDocumentationResponse)
async def generate_repository_documentation(
    repository_id: UUID,
    current_user: CurrentUser,
    service: DocumentationManager,
    session: DatabaseSession,
) -> RepositoryDocumentationResponse:
    """Generate README, API, folder, installation, and usage Markdown documents."""
    try:
        documentation = await service.generate_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except DocumentationNotFound as error:
        raise AppError(
            "documentation_unavailable",
            "The repository has no stored source version to document.",
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ) from error
    except DocumentationConfigurationError as error:
        raise AppError(
            "documentation_not_configured", str(error), status.HTTP_503_SERVICE_UNAVAILABLE
        ) from error
    except (DocumentationGenerationError, RepositoryAnalysisError) as error:
        raise AppError(
            "documentation_unavailable", str(error), status.HTTP_502_BAD_GATEWAY
        ) from error
    await commit_repository_change(session)
    return repository_documentation_response(documentation)


@router.get("/{repository_id}/documentation", response_model=RepositoryDocumentationResponse)
async def get_repository_documentation(
    repository_id: UUID,
    current_user: CurrentUser,
    service: DocumentationManager,
) -> RepositoryDocumentationResponse:
    """Return the saved documentation bundle for the newest stored source version."""
    try:
        documentation = await service.get_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except DocumentationNotFound as error:
        raise AppError(
            "repository_documentation_not_found",
            "This repository does not have generated documentation yet.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return repository_documentation_response(documentation)


@router.get("/{repository_id}/summary", response_model=ProjectSummaryResponse)
async def get_project_summary(
    repository_id: UUID,
    current_user: CurrentUser,
    service: ProjectSummaryManager,
) -> ProjectSummaryResponse:
    """Return the saved GPT-5 summary for the latest immutable source version."""
    try:
        summary = await service.get_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except ProjectSummaryNotFound as error:
        raise AppError(
            "project_summary_not_found",
            "This repository does not have a generated project summary yet.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return project_summary_response(summary)


@router.post("/{repository_id}/chat/index", response_model=RepositoryChatIndexResponse)
async def index_repository_for_chat(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryChatManager,
    session: DatabaseSession,
) -> RepositoryChatIndexResponse:
    """Embed safe source chunks for the latest repository version in Qdrant."""
    try:
        index = await service.index_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryChatConfigurationError as error:
        raise AppError(
            "repository_chat_not_configured", str(error), status.HTTP_503_SERVICE_UNAVAILABLE
        ) from error
    except RepositoryChatIndexingError as error:
        raise AppError(
            "repository_chat_indexing_failed", str(error), status.HTTP_502_BAD_GATEWAY
        ) from error
    await commit_repository_change(session)
    return repository_chat_index_response(index)


@router.get("/{repository_id}/chat/index", response_model=RepositoryChatIndexResponse)
async def get_repository_chat_index(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryChatManager,
) -> RepositoryChatIndexResponse:
    """Return vector-index state for the latest repository version."""
    try:
        index = await service.get_index_latest(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryChatNotIndexed as error:
        raise AppError(
            "repository_chat_not_indexed",
            "This repository has not been indexed for chat yet.",
            status.HTTP_404_NOT_FOUND,
        ) from error
    return repository_chat_index_response(index)


@router.post("/{repository_id}/chat", response_model=RepositoryChatResponse)
async def ask_repository_chat(
    repository_id: UUID,
    payload: RepositoryChatRequest,
    current_user: CurrentUser,
    service: RepositoryChatManager,
) -> RepositoryChatResponse:
    """Answer only from cited source chunks retrieved from the repository's latest version."""
    try:
        answer = await service.ask(current_user.id, repository_id, payload.question)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    except RepositoryChatNotIndexed as error:
        raise AppError(
            "repository_chat_not_indexed",
            "Index this repository for chat before asking a question.",
            status.HTTP_409_CONFLICT,
        ) from error
    except RepositoryChatConfigurationError as error:
        raise AppError(
            "repository_chat_not_configured", str(error), status.HTTP_503_SERVICE_UNAVAILABLE
        ) from error
    except (RepositoryChatIndexingError, RepositoryChatGenerationError) as error:
        raise AppError(
            "repository_chat_unavailable", str(error), status.HTTP_502_BAD_GATEWAY
        ) from error
    return repository_chat_response(answer)


@router.get("/{repository_id}/versions", response_model=list[RepositoryVersionResponse])
async def list_repository_versions(
    repository_id: UUID, current_user: CurrentUser, service: RepositoryManager
) -> list[RepositoryVersionResponse]:
    """Return immutable history for one user-owned repository."""
    try:
        repository = await service.get_repository(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    return [version_response(version) for version in repository.versions]


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: UUID, current_user: CurrentUser, service: RepositoryManager
) -> RepositoryResponse:
    """Return one user-owned repository and its full version history."""
    try:
        repository = await service.get_repository(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    return repository_response(repository)


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID,
    current_user: CurrentUser,
    service: RepositoryManager,
    session: DatabaseSession,
) -> Response:
    """Delete all metadata and stored source versions for one repository."""
    try:
        await service.delete_repository(current_user.id, repository_id)
    except RepositoryNotFound as error:
        raise AppError(
            "repository_not_found", "Repository not found.", status.HTTP_404_NOT_FOUND
        ) from error
    await commit_repository_change(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
