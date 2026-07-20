"""End-to-end authentication endpoint tests."""

from httpx import AsyncClient
from pydantic import SecretStr

from codepilot_api.config.settings import AppEnvironment

VALID_PASSWORD = "SecureCodePilot9"


async def register_user(client: AsyncClient) -> dict[str, object]:
    """Register one valid test user and return its decoded response."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Ada Lovelace",
            "email": "ada@example.com",
            "password": VALID_PASSWORD,
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_registration_issues_access_token_and_refresh_cookie(client: AsyncClient) -> None:
    """Registration must establish a usable session without exposing the refresh token in JSON."""
    body = await register_user(client)

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == "ada@example.com"
    assert "refresh_token" not in body
    assert client.cookies.get("codepilot_refresh")


async def test_production_refresh_cookie_supports_vercel_to_api_requests(
    client: AsyncClient, settings
) -> None:
    """A cross-origin Vercel UI needs a secure SameSite=None API cookie to refresh sessions."""
    settings.app_env = AppEnvironment.PRODUCTION
    settings.jwt_secret_key = SecretStr("a" * 32)

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Production Ada",
            "email": "production-ada@example.com",
            "password": VALID_PASSWORD,
        },
    )

    cookie = response.headers["set-cookie"].lower()
    assert response.status_code == 201
    assert "secure" in cookie
    assert "samesite=none" in cookie


async def test_duplicate_registration_and_invalid_password_return_safe_errors(
    client: AsyncClient,
) -> None:
    """Credential failures must have stable, public-safe error envelopes."""
    await register_user(client)

    duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Another Ada",
            "email": "ADA@example.com",
            "password": VALID_PASSWORD,
        },
    )
    invalid_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "WrongPassword9"},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_already_registered"
    assert invalid_login.status_code == 401
    assert invalid_login.json()["error"]["code"] == "invalid_credentials"


async def test_login_me_and_refresh_rotation(client: AsyncClient) -> None:
    """A refresh token is rotated once and cannot be reused after rotation."""
    await register_user(client)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": VALID_PASSWORD},
    )
    assert login.status_code == 200
    old_refresh_token = login.cookies["codepilot_refresh"]
    access_token = login.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    refreshed = await client.post("/api/v1/auth/refresh")
    reused = await client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": f"codepilot_refresh={old_refresh_token}"},
    )

    assert me.status_code == 200
    assert me.json()["display_name"] == "Ada Lovelace"
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != access_token
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "invalid_refresh_token"


async def test_logout_revokes_refresh_session(client: AsyncClient) -> None:
    """Logout must make the browser refresh cookie unusable immediately."""
    await register_user(client)

    logout_response = await client.post("/api/v1/auth/logout")
    refresh_response = await client.post("/api/v1/auth/refresh")

    assert logout_response.status_code == 204
    assert refresh_response.status_code == 401
