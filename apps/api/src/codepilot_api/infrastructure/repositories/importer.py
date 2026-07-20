"""Secure GitHub clone and ZIP extraction adapter."""

from __future__ import annotations

import asyncio
import shutil
import stat
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, ZipInfo

from fastapi import UploadFile

from codepilot_api.config.settings import Settings
from codepilot_api.domain.repositories.entities import ImportedWorkspace
from codepilot_api.domain.repositories.errors import InvalidRepositorySource, RepositoryImportError


class SecureWorkspaceImporter:
    """Create source workspaces while enforcing file, size, and path safety limits."""

    def __init__(self, settings: Settings) -> None:
        self._upload_max_bytes = settings.repository_upload_max_bytes
        self._extracted_max_bytes = settings.repository_extracted_max_bytes
        self._max_files = settings.repository_max_files
        self._max_compression_ratio = settings.repository_max_compression_ratio
        self._git_timeout_seconds = settings.git_clone_timeout_seconds

    async def save_upload(self, upload: UploadFile, destination: Path) -> Path:
        """Stream a ZIP upload to staging without loading it all into application memory."""
        filename = upload.filename or ""
        if Path(filename).suffix.casefold() != ".zip":
            raise InvalidRepositorySource("Only .zip repository uploads are supported.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            with destination.open("wb") as file_handle:
                while chunk := await upload.read(1024 * 1024):
                    written += len(chunk)
                    if written > self._upload_max_bytes:
                        raise InvalidRepositorySource(
                            "The ZIP upload exceeds the configured size limit."
                        )
                    file_handle.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()
        return destination

    async def clone_github(self, source_url: str, destination: Path) -> ImportedWorkspace:
        """Shallow-clone a validated GitHub URL and exclude Git metadata from stored source."""
        await self._run_git(
            "clone",
            "--depth=1",
            "--no-tags",
            "--filter=blob:none",
            source_url,
            str(destination),
        )
        commit_sha = (await self._run_git("-C", str(destination), "rev-parse", "HEAD")).strip()
        shutil.rmtree(destination / ".git", ignore_errors=True)
        source_root = self._unwrap_root(destination)
        workspace = self._inspect_workspace(source_root)
        return ImportedWorkspace(
            source_root=str(source_root),
            file_count=workspace.file_count,
            size_bytes=workspace.size_bytes,
            commit_sha=commit_sha,
        )

    def extract_zip(self, archive_path: Path, destination: Path) -> ImportedWorkspace:
        """Extract a ZIP archive only after validating every path and compression constraint."""
        if not archive_path.is_file():
            raise InvalidRepositorySource("The uploaded archive is unavailable.")
        destination.mkdir(parents=True, exist_ok=True)
        try:
            with ZipFile(archive_path) as archive:
                entries = [entry for entry in archive.infolist() if not entry.is_dir()]
                self._validate_archive_entries(entries)
                for entry in entries:
                    target = self._safe_archive_target(destination, entry)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry, "r") as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
        except BadZipFile as error:
            raise InvalidRepositorySource(
                "The uploaded file is not a valid ZIP archive."
            ) from error

        source_root = self._unwrap_root(destination)
        workspace = self._inspect_workspace(source_root)
        return ImportedWorkspace(
            source_root=str(source_root),
            file_count=workspace.file_count,
            size_bytes=workspace.size_bytes,
            commit_sha=None,
        )

    async def _run_git(self, *arguments: str) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                *arguments,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as error:
            raise RepositoryImportError("Git is not available on this server.") from error
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=self._git_timeout_seconds
            )
        except TimeoutError as error:
            process.kill()
            await process.communicate()
            raise RepositoryImportError(
                "The GitHub clone exceeded the configured timeout."
            ) from error
        if process.returncode != 0:
            raise RepositoryImportError("CodePilot could not clone the GitHub repository.")
        return stdout.decode("utf-8", errors="replace")

    def _validate_archive_entries(self, entries: list[ZipInfo]) -> None:
        if not entries:
            raise InvalidRepositorySource("The ZIP archive contains no source files.")
        if len(entries) > self._max_files:
            raise InvalidRepositorySource("The ZIP archive contains too many files.")
        extracted_size = 0
        for entry in entries:
            self._safe_archive_parts(entry)
            if self._is_symlink(entry):
                raise InvalidRepositorySource(
                    "ZIP archives containing symbolic links are not supported."
                )
            if entry.file_size > 0 and (
                entry.compress_size == 0
                or entry.file_size / max(entry.compress_size, 1) > self._max_compression_ratio
            ):
                raise InvalidRepositorySource(
                    "The ZIP archive exceeds the allowed compression ratio."
                )
            extracted_size += entry.file_size
            if extracted_size > self._extracted_max_bytes:
                raise InvalidRepositorySource(
                    "The extracted repository exceeds the configured size limit."
                )

    def _inspect_workspace(self, source_root: Path) -> ImportedWorkspace:
        if not source_root.is_dir():
            raise RepositoryImportError("The imported source tree is empty.")
        file_count = 0
        size_bytes = 0
        for entry in source_root.rglob("*"):
            if entry.is_symlink():
                raise InvalidRepositorySource(
                    "Source trees containing symbolic links are not supported."
                )
            if entry.is_file():
                file_count += 1
                if file_count > self._max_files:
                    raise InvalidRepositorySource("The repository contains too many files.")
                size_bytes += entry.stat().st_size
                if size_bytes > self._extracted_max_bytes:
                    raise InvalidRepositorySource(
                        "The repository exceeds the configured size limit."
                    )
        if file_count == 0:
            raise RepositoryImportError("The imported source tree contains no files.")
        return ImportedWorkspace(str(source_root), file_count, size_bytes, None)

    @staticmethod
    def _unwrap_root(destination: Path) -> Path:
        entries = [entry for entry in destination.iterdir() if entry.name != "__MACOSX"]
        if len(entries) == 1 and entries[0].is_dir():
            return entries[0]
        return destination

    @staticmethod
    def _is_symlink(entry: ZipInfo) -> bool:
        return stat.S_ISLNK(entry.external_attr >> 16)

    def _safe_archive_target(self, destination: Path, entry: ZipInfo) -> Path:
        return destination.joinpath(*self._safe_archive_parts(entry))

    @staticmethod
    def _safe_archive_parts(entry: ZipInfo) -> tuple[str, ...]:
        path = PurePosixPath(entry.filename.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise InvalidRepositorySource("The ZIP archive contains an unsafe file path.")
        return path.parts
