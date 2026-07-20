"""Shared FastAPI dependencies for database and authentication access."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.application.auth.service import AuthenticationService
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
from codepilot_api.domain.auth.errors import AuthenticationFailed
from codepilot_api.infrastructure.auth.passwords import Argon2PasswordManager
from codepilot_api.infrastructure.auth.repository import SqlAlchemyAuthRepository
from codepilot_api.infrastructure.auth.tokens import JwtTokenIssuer
from codepilot_api.infrastructure.chat.chunker import SafeRepositoryChunker
from codepilot_api.infrastructure.chat.gemini_repository_chat import (
    GeminiEmbeddingProvider,
    GeminiGroundedChatAgent,
)
from codepilot_api.infrastructure.chat.index_store import SqlAlchemyRepositoryChatIndexStore
from codepilot_api.infrastructure.chat.ollama_repository_chat import (
    OllamaEmbeddingProvider,
    OllamaGroundedChatAgent,
)
from codepilot_api.infrastructure.chat.openai_repository_chat import (
    OpenAIEmbeddingProvider,
    OpenAIGroundedChatAgent,
)
from codepilot_api.infrastructure.chat.qdrant_repository_vector_store import (
    QdrantRepositoryVectorStore,
)
from codepilot_api.infrastructure.database.session import get_session
from codepilot_api.infrastructure.documentation.documentation_store import (
    SqlAlchemyDocumentationStore,
)
from codepilot_api.infrastructure.documentation.gemini_documentation_agent import (
    GeminiDocumentationAgent,
)
from codepilot_api.infrastructure.documentation.ollama_documentation_agent import (
    OllamaDocumentationAgent,
)
from codepilot_api.infrastructure.documentation.openai_documentation_agent import (
    OpenAIDocumentationAgent,
)
from codepilot_api.infrastructure.explanations.gemini_code_explanation_agent import (
    GeminiCodeExplanationAgent,
)
from codepilot_api.infrastructure.explanations.ollama_code_explanation_agent import (
    OllamaCodeExplanationAgent,
)
from codepilot_api.infrastructure.explanations.openai_code_explanation_agent import (
    OpenAICodeExplanationAgent,
)
from codepilot_api.infrastructure.refactoring.gemini_refactoring_agent import GeminiRefactoringAgent
from codepilot_api.infrastructure.refactoring.ollama_refactoring_agent import OllamaRefactoringAgent
from codepilot_api.infrastructure.refactoring.openai_refactoring_agent import OpenAIRefactoringAgent
from codepilot_api.infrastructure.refactoring.proposal_store import SqlAlchemyRefactorProposalStore
from codepilot_api.infrastructure.repositories.analysis_catalog import (
    SqlAlchemyRepositoryAnalysisStore,
)
from codepilot_api.infrastructure.repositories.analyzer import SecureRepositoryAnalyzer
from codepilot_api.infrastructure.repositories.catalog import SqlAlchemyRepositoryCatalog
from codepilot_api.infrastructure.repositories.importer import SecureWorkspaceImporter
from codepilot_api.infrastructure.repositories.storage import LocalRepositoryStorage
from codepilot_api.infrastructure.reviews.review_store import SqlAlchemyRepositoryCodeReviewStore
from codepilot_api.infrastructure.reviews.reviewer import SecureRepositoryCodeReviewer
from codepilot_api.infrastructure.summaries.gemini_project_summary_agent import (
    GeminiProjectSummaryAgent,
)
from codepilot_api.infrastructure.summaries.ollama_project_summary_agent import (
    OllamaProjectSummaryAgent,
)
from codepilot_api.infrastructure.summaries.openai_project_summary_agent import (
    OpenAIProjectSummaryAgent,
)
from codepilot_api.infrastructure.summaries.summary_store import SqlAlchemyProjectSummaryStore
from codepilot_api.infrastructure.test_generation.gemini_unit_test_agent import (
    GeminiUnitTestGenerationAgent,
)
from codepilot_api.infrastructure.test_generation.ollama_unit_test_agent import (
    OllamaUnitTestGenerationAgent,
)
from codepilot_api.infrastructure.test_generation.openai_unit_test_agent import (
    OpenAIUnitTestGenerationAgent,
)
from codepilot_api.infrastructure.test_generation.test_store import SqlAlchemyGeneratedTestStore
from codepilot_api.presentation.errors import AppError

bearer_security = HTTPBearer(auto_error=False)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one rollback-safe SQLAlchemy session for the current HTTP request."""
    async for session in get_session(request.app.state.session_factory):
        yield session


def get_authentication_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthenticationService:
    """Compose the authentication service with production adapters."""
    settings = request.app.state.settings
    return AuthenticationService(
        repository=SqlAlchemyAuthRepository(session),
        password_manager=Argon2PasswordManager(),
        token_issuer=JwtTokenIssuer(settings),
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )


def get_repository_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RepositoryService:
    """Compose repository management with scoped local storage and secure import adapters."""
    settings = request.app.state.settings
    return RepositoryService(
        catalog=SqlAlchemyRepositoryCatalog(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
        workspace_importer=SecureWorkspaceImporter(settings),
    )


def get_repository_intelligence_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RepositoryIntelligenceService:
    """Compose deterministic repository intelligence with scoped source storage."""
    settings = request.app.state.settings
    return RepositoryIntelligenceService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
        analyzer=SecureRepositoryAnalyzer(settings),
    )


def get_repository_architecture_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RepositoryArchitectureService:
    """Compose architecture graph generation with owned repository storage."""
    settings = request.app.state.settings
    return RepositoryArchitectureService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
    )


def get_repository_code_review_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RepositoryCodeReviewService:
    """Compose bounded static code review with repository ownership and saved analysis."""
    settings = request.app.state.settings
    return RepositoryCodeReviewService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        review_store=SqlAlchemyRepositoryCodeReviewStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
        reviewer=SecureRepositoryCodeReviewer(settings),
    )


def get_refactoring_advisor_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RefactoringAdvisorService:
    """Compose source-grounded refactoring proposals with the configured AI provider."""
    settings = request.app.state.settings
    source_reader = RepositoryArchitectureService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
    )
    agent = getattr(request.app.state, "refactoring_agent", None)
    return RefactoringAdvisorService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        review_store=SqlAlchemyRepositoryCodeReviewStore(session),
        proposal_store=SqlAlchemyRefactorProposalStore(session),
        source_reader=source_reader,
        agent=agent or _refactoring_agent(settings),
    )


def get_unit_test_generation_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UnitTestGenerationService:
    """Compose source-grounded unit-test generation for an owned repository version."""
    settings = request.app.state.settings
    source_reader = RepositoryArchitectureService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
    )
    agent = getattr(request.app.state, "unit_test_generation_agent", None)
    return UnitTestGenerationService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        source_reader=source_reader,
        generated_test_store=SqlAlchemyGeneratedTestStore(session),
        agent=agent or _unit_test_generation_agent(settings),
    )


def get_code_explanation_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CodeExplanationService:
    """Compose source-validated function explanations with the selected AI provider."""
    settings = request.app.state.settings
    source_reader = RepositoryArchitectureService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
    )
    agent = getattr(request.app.state, "code_explanation_agent", None)
    return CodeExplanationService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        source_reader=source_reader,
        agent=agent or _code_explanation_agent(settings),
    )


def get_project_summary_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectSummaryService:
    """Compose provider-selected summaries with the latest stored repository intelligence."""
    settings = request.app.state.settings
    intelligence_service = RepositoryIntelligenceService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
        analyzer=SecureRepositoryAnalyzer(settings),
    )
    agent = getattr(request.app.state, "project_summary_agent", None)
    return ProjectSummaryService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        summary_store=SqlAlchemyProjectSummaryStore(session),
        intelligence_service=intelligence_service,
        agent=agent or _project_summary_agent(settings),
    )


def get_documentation_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentationService:
    """Compose metadata-grounded repository documentation with the selected AI provider."""
    settings = request.app.state.settings
    intelligence_service = RepositoryIntelligenceService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
        analyzer=SecureRepositoryAnalyzer(settings),
    )
    agent = getattr(request.app.state, "documentation_agent", None)
    return DocumentationService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        analysis_store=SqlAlchemyRepositoryAnalysisStore(session),
        documentation_store=SqlAlchemyDocumentationStore(session),
        intelligence_service=intelligence_service,
        agent=agent or _documentation_agent(settings),
    )


def get_repository_chat_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RepositoryChatService:
    """Compose secure source chunking, Qdrant retrieval, and grounded repository chat."""
    settings = request.app.state.settings
    embeddings = getattr(request.app.state, "repository_chat_embeddings", None)
    vector_store = getattr(request.app.state, "repository_chat_vector_store", None)
    agent = getattr(request.app.state, "repository_chat_agent", None)
    return RepositoryChatService(
        repository_catalog=SqlAlchemyRepositoryCatalog(session),
        index_store=SqlAlchemyRepositoryChatIndexStore(session),
        storage=LocalRepositoryStorage(settings.repository_storage_root),
        chunker=SafeRepositoryChunker(settings),
        embeddings=embeddings or _repository_chat_embeddings(settings),
        vector_store=vector_store
        or QdrantRepositoryVectorStore(settings, _embedding_model_name(settings)),
        agent=agent or _repository_chat_agent(settings),
        embedding_model=_embedding_model_name(settings),
        search_limit=settings.repository_rag_search_limit,
        min_score=settings.repository_rag_min_score,
    )


def _project_summary_agent(settings):
    """Choose the configured generation adapter without leaking it into application services."""
    if settings.ai_provider.value == "ollama":
        return OllamaProjectSummaryAgent(settings)
    if settings.ai_provider.value == "gemini":
        return GeminiProjectSummaryAgent(settings)
    return OpenAIProjectSummaryAgent(settings)


def _code_explanation_agent(settings):
    """Choose the configured explanation adapter."""
    if settings.ai_provider.value == "ollama":
        return OllamaCodeExplanationAgent(settings)
    if settings.ai_provider.value == "gemini":
        return GeminiCodeExplanationAgent(settings)
    return OpenAICodeExplanationAgent(settings)


def _refactoring_agent(settings):
    """Choose the provider-specific refactoring adapter without leaking it into use cases."""
    if settings.ai_provider.value == "ollama":
        return OllamaRefactoringAgent(settings)
    if settings.ai_provider.value == "gemini":
        return GeminiRefactoringAgent(settings)
    return OpenAIRefactoringAgent(settings)


def _unit_test_generation_agent(settings):
    """Choose the provider-specific test generator without leaking it into use cases."""
    if settings.ai_provider.value == "ollama":
        return OllamaUnitTestGenerationAgent(settings)
    if settings.ai_provider.value == "gemini":
        return GeminiUnitTestGenerationAgent(settings)
    return OpenAIUnitTestGenerationAgent(settings)


def _documentation_agent(settings):
    """Choose the provider-specific documentation generator."""
    if settings.ai_provider.value == "ollama":
        return OllamaDocumentationAgent(settings)
    if settings.ai_provider.value == "gemini":
        return GeminiDocumentationAgent(settings)
    return OpenAIDocumentationAgent(settings)


def _repository_chat_embeddings(settings):
    """Choose the configured embedding adapter."""
    if settings.ai_provider.value == "ollama":
        return OllamaEmbeddingProvider(settings)
    if settings.ai_provider.value == "gemini":
        return GeminiEmbeddingProvider(settings)
    return OpenAIEmbeddingProvider(settings)


def _repository_chat_agent(settings):
    """Choose the configured grounded-answer adapter."""
    if settings.ai_provider.value == "ollama":
        return OllamaGroundedChatAgent(settings)
    if settings.ai_provider.value == "gemini":
        return GeminiGroundedChatAgent(settings)
    return OpenAIGroundedChatAgent(settings)


def _embedding_model_name(settings) -> str:
    """Persist the model that generated vectors so an index remains traceable."""
    if settings.ai_provider.value == "ollama":
        return f"ollama/{settings.ollama_embedding_model}"
    if settings.ai_provider.value == "gemini":
        return f"gemini/{settings.gemini_embedding_model}/{settings.gemini_embedding_dimensions}"
    return settings.openai_embedding_model


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_security)],
    service: Annotated[AuthenticationService, Depends(get_authentication_service)],
) -> AuthUser:
    """Require a valid bearer access token and resolve its active user."""
    if credentials is None:
        raise AppError(
            code="authentication_required",
            message="Authentication is required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return await service.current_user(credentials.credentials)
    except AuthenticationFailed as error:
        raise AppError(
            code="invalid_access_token",
            message="Your access token is invalid or has expired.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
