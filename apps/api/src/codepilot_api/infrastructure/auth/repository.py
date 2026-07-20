"""SQLAlchemy implementation of the authentication repository port."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.domain.auth.entities import (
    AuthUser,
)
from codepilot_api.domain.auth.entities import (
    RefreshSession as RefreshSessionRecord,
)
from codepilot_api.infrastructure.database.models import RefreshSession, User


class SqlAlchemyAuthRepository:
    """Persist users and revocable refresh sessions through one SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_user_by_email(self, email: str) -> AuthUser | None:
        """Find a user by normalized email address."""
        model = await self._session.scalar(select(User).where(User.email == email))
        return self._to_auth_user(model) if model else None

    async def find_user_by_id(self, user_id: UUID) -> AuthUser | None:
        """Find a user by primary key."""
        model = await self._session.get(User, user_id)
        return self._to_auth_user(model) if model else None

    async def create_user(self, email: str, display_name: str, password_hash: str) -> AuthUser:
        """Stage a new user and flush its generated fields."""
        model = User(email=email, display_name=display_name, password_hash=password_hash)
        self._session.add(model)
        await self._session.flush()
        return self._to_auth_user(model)

    async def create_refresh_session(
        self, user_id: UUID, expires_at: datetime
    ) -> RefreshSessionRecord:
        """Stage a refresh session bound to a user and expiration time."""
        model = RefreshSession(user_id=user_id, expires_at=expires_at)
        self._session.add(model)
        await self._session.flush()
        return self._to_refresh_session(model)

    async def find_refresh_session(self, session_id: UUID) -> RefreshSessionRecord | None:
        """Find a refresh session and lock it while a token rotation is in progress."""
        statement = select(RefreshSession).where(RefreshSession.id == session_id).with_for_update()
        model = await self._session.scalar(statement)
        return self._to_refresh_session(model) if model else None

    async def revoke_refresh_session(self, session_id: UUID, revoked_at: datetime) -> None:
        """Mark an active refresh session as unusable without deleting audit history."""
        model = await self._session.get(RefreshSession, session_id)
        if model and model.revoked_at is None:
            model.revoked_at = revoked_at
            await self._session.flush()

    @staticmethod
    def _to_auth_user(model: User) -> AuthUser:
        return AuthUser(
            id=model.id,
            email=model.email,
            display_name=model.display_name,
            password_hash=model.password_hash,
            is_active=model.is_active,
            created_at=SqlAlchemyAuthRepository._as_utc(model.created_at),
        )

    @staticmethod
    def _to_refresh_session(model: RefreshSession) -> RefreshSessionRecord:
        return RefreshSessionRecord(
            id=model.id,
            user_id=model.user_id,
            expires_at=SqlAlchemyAuthRepository._as_utc(model.expires_at),
            revoked_at=(
                SqlAlchemyAuthRepository._as_utc(model.revoked_at) if model.revoked_at else None
            ),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)
