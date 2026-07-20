"""Framework-independent code-review records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class CodeReviewCategory(StrEnum):
    """Supported repository-wide review categories."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    NAMING = "naming"
    DEAD_CODE = "dead_code"
    CODE_SMELL = "code_smell"
    LONG_FUNCTION = "long_function"
    DUPLICATE_CODE = "duplicate_code"


class CodeReviewSeverity(StrEnum):
    """Impact level of a review finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class CodeReviewFinding:
    """One evidence-backed issue found in stored repository source."""

    key: str
    category: CodeReviewCategory
    severity: CodeReviewSeverity
    confidence: int
    title: str
    description: str
    recommendation: str
    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class RepositoryCodeReviewPayload:
    """Portable results emitted by the deterministic repository reviewer."""

    review_version: int
    findings: tuple[CodeReviewFinding, ...]
    scanned_file_count: int


@dataclass(frozen=True, slots=True)
class RepositoryCodeReviewRecord:
    """Persisted review results for one immutable repository version."""

    id: UUID
    repository_version_id: UUID
    review_version: int
    findings: tuple[CodeReviewFinding, ...]
    scanned_file_count: int
    created_at: datetime
    updated_at: datetime
