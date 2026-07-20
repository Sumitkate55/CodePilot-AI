"""Framework-independent authentication entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthUser:
    """The user information required by authentication use cases."""

    id: UUID
    email: str
    display_name: str
    password_hash: str
    is_active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshSession:
    """A revocable server-side refresh session."""

    id: UUID
    user_id: UUID
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Access and refresh tokens issued as a single authentication result."""

    access_token: str
    refresh_token: str
    access_token_expires_in: int


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """Authenticated user and newly rotated token pair."""

    user: AuthUser
    tokens: TokenPair
