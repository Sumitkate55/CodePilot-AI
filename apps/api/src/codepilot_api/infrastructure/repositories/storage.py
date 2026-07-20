"""Scoped local filesystem storage for repository source trees."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from uuid import UUID

from codepilot_api.domain.repositories.errors import RepositoryImportError


class LocalRepositoryStorage:
    """Store source trees under a strict owner/repository/version hierarchy."""

    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()
        self._staging_root = self._root / ".staging"

    @contextmanager
    def staging_directory(self) -> Iterator[Path]:
        """Provide an automatically cleaned, private staging directory for one import."""
        self._staging_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="import-", dir=self._staging_root) as directory:
            yield Path(directory)

    def persist(
        self, source_root: Path, owner_id: UUID, repository_id: UUID, version_id: UUID
    ) -> str:
        """Copy a validated workspace into immutable version-specific storage."""
        if not source_root.is_dir():
            raise RepositoryImportError("The imported source directory is unavailable.")
        destination = self._version_path(owner_id, repository_id, version_id)
        if destination.exists():
            raise RepositoryImportError("The target repository version already exists.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_root, destination, symlinks=False)
        return destination.relative_to(self._root).as_posix()

    def resolve_storage_key(self, storage_key: str) -> Path:
        """Resolve a database storage key without allowing it to escape repository storage."""
        key = PurePosixPath(storage_key)
        if key.is_absolute() or not key.parts or ".." in key.parts:
            raise RepositoryImportError("The stored repository source path is invalid.")
        return self._safe_path(*key.parts)

    def delete_version(self, owner_id: UUID, repository_id: UUID, version_id: UUID) -> None:
        """Remove only one newly created immutable version after a failed transaction."""
        target = self._version_path(owner_id, repository_id, version_id)
        if target.exists():
            shutil.rmtree(target)

    def delete_repository(self, owner_id: UUID, repository_id: UUID) -> None:
        """Remove all source versions for one explicitly scoped repository."""
        target = self._repository_path(owner_id, repository_id)
        if target.exists():
            shutil.rmtree(target)

    def _repository_path(self, owner_id: UUID, repository_id: UUID) -> Path:
        return self._safe_path(str(owner_id), str(repository_id))

    def _version_path(self, owner_id: UUID, repository_id: UUID, version_id: UUID) -> Path:
        return self._safe_path(str(owner_id), str(repository_id), str(version_id))

    def _safe_path(self, *parts: str) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        path = (self._root.joinpath(*parts)).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as error:
            raise RepositoryImportError(
                "Repository storage path escaped its configured root."
            ) from error
        return path
