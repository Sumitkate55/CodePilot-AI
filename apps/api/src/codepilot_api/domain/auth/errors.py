"""Authentication business errors."""


class AuthenticationFailed(Exception):
    """Credentials, token, or session validation failed."""


class UserAlreadyExists(Exception):
    """A registration attempted to reuse an existing email address."""
