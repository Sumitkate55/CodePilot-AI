"""Repository source and display-name validation."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from codepilot_api.domain.repositories.errors import InvalidRepositorySource

GITHUB_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
REPOSITORY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,119}$")


def normalize_github_url(value: str) -> tuple[str, str]:
    """Return a canonical public GitHub clone URL and its repository name."""
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.hostname.casefold() != "github.com"
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
    ):
        raise InvalidRepositorySource("Use a public HTTPS GitHub repository URL.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise InvalidRepositorySource("GitHub URLs must identify an owner and repository.")
    owner, repository = parts
    repository = repository.removesuffix(".git")
    if not repository or not all(
        GITHUB_SEGMENT_PATTERN.fullmatch(part) for part in (owner, repository)
    ):
        raise InvalidRepositorySource("The GitHub repository identifier is invalid.")
    return f"https://github.com/{owner}/{repository}.git", repository


def normalize_repository_name(value: str) -> str:
    """Validate a human-readable repository name safe for display and storage metadata."""
    name = value.strip()
    if not REPOSITORY_NAME_PATTERN.fullmatch(name):
        raise InvalidRepositorySource(
            "Repository names must start with a letter or number and contain only spaces, "
            "dots, dashes, or underscores."
        )
    return name


def repository_name_from_filename(filename: str | None) -> str:
    """Derive a valid display name from an uploaded ZIP filename."""
    if not filename:
        raise InvalidRepositorySource("Upload a ZIP file with a filename.")
    stem = Path(filename).stem
    return normalize_repository_name(stem)
