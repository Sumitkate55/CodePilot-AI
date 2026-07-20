"""Relational models registered with SQLAlchemy metadata."""

from codepilot_api.infrastructure.database.models.generated_test import GeneratedTest
from codepilot_api.infrastructure.database.models.refactor_proposal import RefactorProposal
from codepilot_api.infrastructure.database.models.refresh_session import RefreshSession
from codepilot_api.infrastructure.database.models.repository import Repository
from codepilot_api.infrastructure.database.models.repository_analysis import RepositoryAnalysis
from codepilot_api.infrastructure.database.models.repository_chat_index import RepositoryChatIndex
from codepilot_api.infrastructure.database.models.repository_code_review import RepositoryCodeReview
from codepilot_api.infrastructure.database.models.repository_documentation import (
    RepositoryDocumentation,
)
from codepilot_api.infrastructure.database.models.repository_summary import RepositorySummary
from codepilot_api.infrastructure.database.models.repository_version import RepositoryVersion
from codepilot_api.infrastructure.database.models.user import User

__all__ = [
    "GeneratedTest",
    "RefactorProposal",
    "RefreshSession",
    "Repository",
    "RepositoryAnalysis",
    "RepositoryChatIndex",
    "RepositoryCodeReview",
    "RepositoryDocumentation",
    "RepositorySummary",
    "RepositoryVersion",
    "User",
]
