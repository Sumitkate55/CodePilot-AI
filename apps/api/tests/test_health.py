"""Health endpoint tests."""

from httpx import AsyncClient


async def test_health_reports_live_service_and_correlation_id(client: AsyncClient) -> None:
    """The liveness probe must be independent from external dependencies."""
    response = await client.get("/api/v1/health", headers={"X-Request-ID": "request-test-123"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "CodePilot AI API",
        "version": "0.1.0",
    }
    assert response.headers["x-request-id"] == "request-test-123"
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_readiness_checks_database(client: AsyncClient) -> None:
    """The readiness probe verifies that the configured database is reachable."""
    response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "dependencies": [{"name": "database", "status": "healthy"}],
    }
