"""Configuration validation tests."""

import pytest
from pydantic import SecretStr, ValidationError

from codepilot_api.config.settings import (
    DEFAULT_DEVELOPMENT_JWT_SECRET,
    AppEnvironment,
    Settings,
)


def test_settings_reject_unsupported_database_driver() -> None:
    """Only async drivers used by this application should be accepted."""
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(database_url="mysql://localhost/codepilot")


def test_settings_accepts_comma_separated_hosts() -> None:
    """List-valued settings remain ergonomic when passed from process environments."""
    settings = Settings(trusted_hosts="localhost, api.codepilot.example")

    assert settings.trusted_hosts == ["localhost", "api.codepilot.example"]


def test_production_settings_reject_development_jwt_secret() -> None:
    """Production must never start with the built-in development JWT secret."""
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            jwt_secret_key=SecretStr(DEFAULT_DEVELOPMENT_JWT_SECRET),
        )
