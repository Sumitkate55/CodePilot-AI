"""Argon2 password-hashing adapter."""

from pwdlib import PasswordHash


class Argon2PasswordManager:
    """Hash and verify passwords using pwdlib's recommended Argon2 configuration."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        """Return an Argon2 hash for a validated password."""
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """Return false rather than leaking malformed-hash details to callers."""
        try:
            return self._password_hash.verify(password, password_hash)
        except Exception:
            return False
