"""Ports required by the authentication use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from codepilot_api.domain.auth.entities import AuthUser, RefreshSession, TokenPair


class AuthRepository(Protocol):
    """Persistence operations required for user and refresh-session lifecycle."""

    async def find_user_by_email(self, email: str) -> AuthUser | None: ...

    async def find_user_by_id(self, user_id: UUID) -> AuthUser | None: ...

    async def create_user(self, email: str, display_name: str, password_hash: str) -> AuthUser: ...

    async def create_refresh_session(
        self, user_id: UUID, expires_at: datetime
    ) -> RefreshSession: ...

    async def find_refresh_session(self, session_id: UUID) -> RefreshSession | None: ...

    async def revoke_refresh_session(self, session_id: UUID, revoked_at: datetime) -> None: ...


class PasswordManager(Protocol):
    """Password hashing port."""

    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenIssuer(Protocol):
    """JWT issuance and validation port."""

    def issue_tokens(self, user: AuthUser, refresh_session_id: UUID) -> TokenPair: ...

    def decode_access_token(self, token: str) -> UUID: ...

    def decode_refresh_token(self, token: str) -> tuple[UUID, UUID]: ...
