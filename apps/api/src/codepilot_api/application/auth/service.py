"""Authentication application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from codepilot_api.application.auth.contracts import AuthRepository, PasswordManager, TokenIssuer
from codepilot_api.domain.auth.entities import AuthenticationResult, AuthUser
from codepilot_api.domain.auth.errors import AuthenticationFailed, UserAlreadyExists


class AuthenticationService:
    """Coordinates credentials, user persistence, tokens, and refresh-session rotation."""

    def __init__(
        self,
        repository: AuthRepository,
        password_manager: PasswordManager,
        token_issuer: TokenIssuer,
        refresh_token_expire_days: int,
    ) -> None:
        self._repository = repository
        self._password_manager = password_manager
        self._token_issuer = token_issuer
        self._refresh_token_expire_days = refresh_token_expire_days

    async def register(self, email: str, display_name: str, password: str) -> AuthenticationResult:
        """Create a user and an initial session after enforcing unique normalized email."""
        normalized_email = self._normalize_email(email)
        if await self._repository.find_user_by_email(normalized_email):
            raise UserAlreadyExists

        user = await self._repository.create_user(
            email=normalized_email,
            display_name=display_name.strip(),
            password_hash=self._password_manager.hash(password),
        )
        return await self._create_authenticated_session(user)

    async def login(self, email: str, password: str) -> AuthenticationResult:
        """Verify credentials without revealing whether an account exists."""
        user = await self._repository.find_user_by_email(self._normalize_email(email))
        if user is None or not user.is_active:
            raise AuthenticationFailed
        if not self._password_manager.verify(password, user.password_hash):
            raise AuthenticationFailed
        return await self._create_authenticated_session(user)

    async def refresh(self, refresh_token: str) -> AuthenticationResult:
        """Rotate a valid refresh session, invalidating the session used to refresh it."""
        try:
            user_id, session_id = self._token_issuer.decode_refresh_token(refresh_token)
        except ValueError as error:
            raise AuthenticationFailed from error

        session = await self._repository.find_refresh_session(session_id)
        now = datetime.now(UTC)
        if (
            session is None
            or session.user_id != user_id
            or session.revoked_at is not None
            or session.expires_at <= now
        ):
            raise AuthenticationFailed

        user = await self._repository.find_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationFailed

        await self._repository.revoke_refresh_session(session_id, now)
        return await self._create_authenticated_session(user)

    async def current_user(self, access_token: str) -> AuthUser:
        """Resolve the active user attached to a valid bearer access token."""
        try:
            user_id = self._token_issuer.decode_access_token(access_token)
        except ValueError as error:
            raise AuthenticationFailed from error

        user = await self._repository.find_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationFailed
        return user

    async def logout(self, refresh_token: str | None) -> None:
        """Revoke the supplied refresh session when it is valid; always allow local logout."""
        if not refresh_token:
            return
        try:
            _, session_id = self._token_issuer.decode_refresh_token(refresh_token)
        except ValueError:
            return

        session = await self._repository.find_refresh_session(session_id)
        if session and session.revoked_at is None:
            await self._repository.revoke_refresh_session(session_id, datetime.now(UTC))

    async def _create_authenticated_session(self, user: AuthUser) -> AuthenticationResult:
        expires_at = datetime.now(UTC) + timedelta(days=self._refresh_token_expire_days)
        refresh_session = await self._repository.create_refresh_session(user.id, expires_at)
        tokens = self._token_issuer.issue_tokens(user, refresh_session.id)
        return AuthenticationResult(user=user, tokens=tokens)

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().casefold()
