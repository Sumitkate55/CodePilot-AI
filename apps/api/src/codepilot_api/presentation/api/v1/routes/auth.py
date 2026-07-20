"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from codepilot_api.application.auth.service import AuthenticationService
from codepilot_api.domain.auth.entities import AuthUser
from codepilot_api.domain.auth.errors import AuthenticationFailed, UserAlreadyExists
from codepilot_api.presentation.api.v1.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    auth_response,
    user_response,
)
from codepilot_api.presentation.dependencies import (
    get_authentication_service,
    get_current_user,
    get_db_session,
)
from codepilot_api.presentation.errors import AppError

router = APIRouter(prefix="/auth")

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
AuthService = Annotated[AuthenticationService, Depends(get_authentication_service)]


def set_refresh_cookie(response: Response, request: Request, refresh_token: str) -> None:
    """Store the opaque refresh JWT only in a scoped HTTP-only cookie."""
    settings = request.app.state.settings
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


def clear_refresh_cookie(response: Response, request: Request) -> None:
    """Clear the browser cookie using the same scope that set it."""
    settings = request.app.state.settings
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


async def commit_or_conflict(session: AsyncSession) -> None:
    """Commit a user/session mutation and normalize unique-email races."""
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise AppError(
            code="email_already_registered",
            message="An account with this email already exists.",
            status_code=status.HTTP_409_CONFLICT,
        ) from error


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    service: AuthService,
    session: DatabaseSession,
) -> AuthResponse:
    """Register an account, issue an access token, and set a refresh cookie."""
    try:
        result = await service.register(payload.email, payload.display_name, payload.password)
    except UserAlreadyExists as error:
        raise AppError(
            code="email_already_registered",
            message="An account with this email already exists.",
            status_code=status.HTTP_409_CONFLICT,
        ) from error

    await commit_or_conflict(session)
    set_refresh_cookie(response, request, result.tokens.refresh_token)
    return auth_response(result)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService,
    session: DatabaseSession,
) -> AuthResponse:
    """Authenticate credentials, then issue an access token and refresh cookie."""
    try:
        result = await service.login(payload.email, payload.password)
    except AuthenticationFailed as error:
        raise AppError(
            code="invalid_credentials",
            message="Email or password is incorrect.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        ) from error

    await commit_or_conflict(session)
    set_refresh_cookie(response, request, result.tokens.refresh_token)
    return auth_response(result)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    service: AuthService,
    session: DatabaseSession,
) -> AuthResponse:
    """Rotate the HTTP-only refresh cookie and return a new access token."""
    settings = request.app.state.settings
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    try:
        result = await service.refresh(refresh_token or "")
    except AuthenticationFailed as error:
        clear_refresh_cookie(response, request)
        raise AppError(
            code="invalid_refresh_token",
            message="Your session has expired. Please sign in again.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"Set-Cookie": response.headers["set-cookie"]},
        ) from error

    await commit_or_conflict(session)
    set_refresh_cookie(response, request, result.tokens.refresh_token)
    return auth_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: AuthService,
    session: DatabaseSession,
) -> None:
    """Revoke the current refresh session and clear its browser cookie."""
    settings = request.app.state.settings
    await service.logout(request.cookies.get(settings.refresh_cookie_name))
    await commit_or_conflict(session)
    clear_refresh_cookie(response, request)


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[AuthUser, Depends(get_current_user)]) -> UserResponse:
    """Return the user represented by the supplied bearer access token."""
    return user_response(user)
