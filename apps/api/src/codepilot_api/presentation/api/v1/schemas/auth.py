"""Authentication HTTP request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from codepilot_api.domain.auth.entities import AuthenticationResult, AuthUser


class PasswordPayload(BaseModel):
    """Shared validation rules for credentials accepted by the API."""

    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        """Require a practical baseline against trivial credential guessing."""
        if not any(character.islower() for character in password):
            raise ValueError("Password must contain a lowercase letter.")
        if not any(character.isupper() for character in password):
            raise ValueError("Password must contain an uppercase letter.")
        if not any(character.isdigit() for character in password):
            raise ValueError("Password must contain a number.")
        return password


class RegisterRequest(PasswordPayload):
    """New account registration payload."""

    model_config = ConfigDict(str_strip_whitespace=True)

    display_name: str = Field(min_length=2, max_length=100)
    email: EmailStr


class LoginRequest(PasswordPayload):
    """Credential payload for an existing account."""

    email: EmailStr


class UserResponse(BaseModel):
    """Safe public representation of an authenticated user."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    email: EmailStr
    display_name: str
    created_at: datetime


class AuthResponse(BaseModel):
    """Access token response; refresh tokens are intentionally cookie-only."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


def user_response(user: AuthUser) -> UserResponse:
    """Map a domain user to a safe HTTP response."""
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
    )


def auth_response(result: AuthenticationResult) -> AuthResponse:
    """Map an authentication result while excluding the raw refresh token."""
    return AuthResponse(
        access_token=result.tokens.access_token,
        expires_in=result.tokens.access_token_expires_in,
        user=user_response(result.user),
    )
