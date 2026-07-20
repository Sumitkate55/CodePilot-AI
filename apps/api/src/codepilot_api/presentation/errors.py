"""HTTP-safe application error types and exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from codepilot_api.config.settings import Settings

logger = logging.getLogger(__name__)


class AppError(Exception):
    """A known application failure suitable for a stable API response."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers


def error_body(
    request: Request,
    code: str,
    message: str,
    details: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Produce the standard public error envelope."""
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    """Register consistent JSON errors for known and unexpected failures."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content=error_body(request, error.code, error.message, error.details),
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
            for item in error.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_body(request, "validation_error", "Request validation failed.", details),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException) -> JSONResponse:
        message = error.detail if isinstance(error.detail, str) else "Request failed."
        return JSONResponse(
            status_code=error.status_code,
            content=error_body(request, "http_error", message),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        details = {"type": type(error).__name__} if settings.debug else None
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body(request, "internal_error", "An unexpected error occurred.", details),
        )
