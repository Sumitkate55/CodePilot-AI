"""Version 1 API router assembly."""

from fastapi import APIRouter

from codepilot_api.presentation.api.v1.routes.auth import router as auth_router
from codepilot_api.presentation.api.v1.routes.health import router as health_router
from codepilot_api.presentation.api.v1.routes.repositories import router as repositories_router

api_router = APIRouter()
api_router.include_router(auth_router, tags=["authentication"])
api_router.include_router(repositories_router, tags=["repositories"])
api_router.include_router(health_router, tags=["health"])
