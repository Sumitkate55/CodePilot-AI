"""Safe, deterministic source chunking for repository retrieval."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from codepilot_api.config.settings import Settings
from codepilot_api.domain.chat.entities import RepositoryChunk
from codepilot_api.domain.chat.errors import RepositoryChatIndexingError
from codepilot_api.infrastructure.repositories.analyzer import BINARY_SUFFIXES, SKIPPED_DIRECTORIES

SENSITIVE_NAMES = {
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secrets.json",
}
SENSITIVE_SUFFIXES = {".cer", ".crt", ".key", ".p12", ".pfx", ".pem"}


class SafeRepositoryChunker:
    """Read only bounded, non-secret, UTF-8 repository text without executing source."""

    def __init__(self, settings: Settings) -> None:
        self._max_file_bytes = settings.repository_rag_max_file_bytes
        self._max_chunks = settings.repository_rag_max_chunks
        self._chunk_characters = settings.repository_rag_chunk_characters
        self._overlap_lines = settings.repository_rag_chunk_overlap_lines

    def chunk(self, source_root: Path, repository_version_id: UUID) -> tuple[RepositoryChunk, ...]:
        """Return stable, line-addressable chunks for files safe to embed."""
        if not source_root.is_dir():
            raise RepositoryChatIndexingError(
                "The stored repository source is unavailable for chat."
            )
        chunks: list[RepositoryChunk] = []
        for file_path in self._iter_files(source_root):
            if self._is_sensitive(file_path):
                continue
            text = self._read_text(file_path)
            if text is None:
                continue
            relative_path = file_path.relative_to(source_root).as_posix()
            for start_line, end_line, content in self._split_lines(text):
                chunk_id = uuid5(
                    NAMESPACE_URL,
                    f"{repository_version_id}:{relative_path}:{start_line}:{end_line}:"
                    f"{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
                )
                chunks.append(
                    RepositoryChunk(
                        id=chunk_id,
                        repository_version_id=repository_version_id,
                        path=relative_path,
                        start_line=start_line,
                        end_line=end_line,
                        content=(
                            f"Path: {relative_path}\nLines: {start_line}-{end_line}\n\n{content}"
                        ),
                    )
                )
                if len(chunks) >= self._max_chunks:
                    return tuple(chunks)
        return tuple(chunks)

    def _iter_files(self, source_root: Path):
        for directory, directory_names, filenames in os.walk(source_root, followlinks=False):
            directory_names[:] = sorted(
                name
                for name in directory_names
                if name.casefold() not in SKIPPED_DIRECTORIES
                and not (Path(directory) / name).is_symlink()
            )
            for filename in sorted(filenames):
                file_path = Path(directory) / filename
                if file_path.is_file() and not file_path.is_symlink():
                    yield file_path

    @staticmethod
    def _is_sensitive(file_path: Path) -> bool:
        name = file_path.name.casefold()
        return (
            name.startswith(".env")
            or name in SENSITIVE_NAMES
            or file_path.suffix.casefold() in SENSITIVE_SUFFIXES
            or "secret" in name
            or "credential" in name
        )

    def _read_text(self, file_path: Path) -> str | None:
        if file_path.suffix.casefold() in BINARY_SUFFIXES:
            return None
        try:
            if file_path.stat().st_size > self._max_file_bytes:
                return None
            raw = file_path.read_bytes()
        except OSError:
            return None
        if b"\x00" in raw:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def _split_lines(self, text: str) -> tuple[tuple[int, int, str], ...]:
        lines = text.splitlines()
        if not lines:
            return ()
        chunks: list[tuple[int, int, str]] = []
        start = 0
        while start < len(lines):
            end = start
            size = 0
            while end < len(lines):
                next_size = size + len(lines[end]) + 1
                if end > start and next_size > self._chunk_characters:
                    break
                size = next_size
                end += 1
            content = "\n".join(lines[start:end]).strip()
            if content:
                chunks.append((start + 1, end, content))
            if end >= len(lines):
                break
            start = max(start + 1, end - self._overlap_lines)
        return tuple(chunks)
