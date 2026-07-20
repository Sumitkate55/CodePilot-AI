"""Correlation IDs, timing, and baseline browser security headers."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from codepilot_api.infrastructure.logging.configuration import request_id_context

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request identifier and emit one completion log per request."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started_at = time.perf_counter()
        try:
            response = await call_next(request)  # type: ignore[operator]
        finally:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": elapsed_ms,
                },
            )
            request_id_context.reset(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
