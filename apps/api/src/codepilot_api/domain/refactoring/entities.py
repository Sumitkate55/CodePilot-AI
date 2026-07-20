"""Framework-independent refactoring-advisor records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from codepilot_api.domain.reviews.entities import CodeReviewFinding


class RefactorProposalStatus(StrEnum):
    """A user's decision for an AI-generated proposal."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RefactorRisk(StrEnum):
    """Change risk estimated from the selected source evidence."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class RefactoringContext:
    """Bounded, redacted source evidence submitted to one refactoring agent."""

    repository_id: UUID
    repository_version_id: UUID
    finding: CodeReviewFinding
    source_start_line: int
    source_end_line: int
    source: str


@dataclass(frozen=True, slots=True)
class RefactorProposalPayload:
    """A structured proposal returned by an AI provider for one finding."""

    model: str
    title: str
    rationale: str
    replacement_source: str
    risk: RefactorRisk
    confidence: int
    estimated_quality_gain: int
    impact_summary: tuple[str, ...]
    testing_steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RefactorProposalRecord:
    """Persisted proposal, source evidence, diff, and user decision."""

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
    confidence: int
    estimated_quality_gain: int
    impact_summary: tuple[str, ...]
    testing_steps: tuple[str, ...]
    status: RefactorProposalStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RefactoringScore:
    """Current and potential quality scores derived from saved review findings."""

    baseline: int
    current: int
    potential: int
    accepted_quality_gain: int
    available_quality_gain: int
    accepted_count: int
    proposed_count: int
    rejected_count: int
    remaining_finding_count: int
