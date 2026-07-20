"""PyJWT token issuer adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError

from codepilot_api.config.settings import Settings
from codepilot_api.domain.auth.entities import AuthUser, TokenPair


class JwtTokenIssuer:
    """Issue signed access/refresh tokens with explicit token-purpose claims."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret_key.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._access_token_expires_in = settings.access_token_expire_minutes * 60
        self._access_token_expiry = timedelta(minutes=settings.access_token_expire_minutes)
        self._refresh_token_expiry = timedelta(days=settings.refresh_token_expire_days)

    def issue_tokens(self, user: AuthUser, refresh_session_id: UUID) -> TokenPair:
        """Issue a short bearer token and a long-lived session-bound refresh token."""
        now = datetime.now(UTC)
        access_token = self._encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "jti": str(uuid4()),
                "type": "access",
                "iat": now,
                "exp": now + self._access_token_expiry,
            }
        )
        refresh_token = self._encode(
            {
                "sub": str(user.id),
                "sid": str(refresh_session_id),
                "jti": str(uuid4()),
                "type": "refresh",
                "iat": now,
                "exp": now + self._refresh_token_expiry,
            }
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_in=self._access_token_expires_in,
        )

    def decode_access_token(self, token: str) -> UUID:
        """Validate a bearer token and return its subject."""
        claims = self._decode(token, expected_type="access")
        return self._as_uuid(claims.get("sub"))

    def decode_refresh_token(self, token: str) -> tuple[UUID, UUID]:
        """Validate a refresh token and return its user/session claims."""
        claims = self._decode(token, expected_type="refresh")
        return self._as_uuid(claims.get("sub")), self._as_uuid(claims.get("sid"))

    def _encode(self, claims: dict[str, object]) -> str:
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)

    def _decode(self, token: str, expected_type: str) -> dict[str, object]:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except InvalidTokenError as error:
            raise ValueError("Invalid token.") from error
        if claims.get("type") != expected_type:
            raise ValueError("Invalid token purpose.")
        return claims

    @staticmethod
    def _as_uuid(value: object) -> UUID:
        if not isinstance(value, str):
            raise ValueError("Invalid token subject.")
        try:
            return UUID(value)
        except ValueError as error:
            raise ValueError("Invalid token subject.") from error
