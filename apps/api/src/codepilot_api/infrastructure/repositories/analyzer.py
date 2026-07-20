"""Bounded, deterministic repository source intelligence analyzer."""

from __future__ import annotations

import json
import os
import re
import tomllib
from collections import Counter
from pathlib import Path

from codepilot_api.config.settings import Settings
from codepilot_api.domain.repositories.entities import RepositoryAnalysisPayload
from codepilot_api.domain.repositories.errors import RepositoryAnalysisError

ANALYSIS_VERSION = 1

LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C",
    ".h": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".sql": "SQL",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
}

SKIPPED_DIRECTORIES = {
    ".git",
    ".next",
    ".nuxt",
    ".venv",
    "__pycache__",
    "bower_components",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "venv",
}

BINARY_SUFFIXES = {
    ".7z",
    ".a",
    ".bin",
    ".class",
    ".dll",
    ".dylib",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lock",
    ".mp3",
    ".mp4",
    ".o",
    ".otf",
    ".pdf",
    ".png",
    ".so",
    ".sqlite",
    ".tar",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}

FRAMEWORK_DEPENDENCIES = {
    "@angular/core": "Angular",
    "django": "Django",
    "express": "Express",
    "fastapi": "FastAPI",
    "fastify": "Fastify",
    "flask": "Flask",
    "laravel/framework": "Laravel",
    "nestjs": "NestJS",
    "next": "Next.js",
    "nuxt": "Nuxt",
    "react": "React",
    "react-native": "React Native",
    "rails": "Ruby on Rails",
    "spring-boot-starter": "Spring Boot",
    "svelte": "Svelte",
    "vue": "Vue",
}

SOURCE_FRAMEWORK_MARKERS = {
    "from fastapi": "FastAPI",
    "import fastapi": "FastAPI",
    "from django": "Django",
    "import django": "Django",
    "from flask": "Flask",
    "require('express')": "Express",
    'from "express"': "Express",
    "from 'express'": "Express",
    'from "react"': "React",
    "from 'react'": "React",
    'from "vue"': "Vue",
    "from 'vue'": "Vue",
}

DATABASE_DEPENDENCIES = {
    "asyncpg",
    "django",
    "drizzle-orm",
    "mongoose",
    "mysql",
    "mysql2",
    "pg",
    "prisma",
    "psycopg",
    "pymongo",
    "redis",
    "sqlalchemy",
    "typeorm",
}

PYTHON_CLASS_PATTERN = re.compile(r"^[ \t]*class\s+([A-Za-z_]\w*)", re.MULTILINE)
PYTHON_FUNCTION_PATTERN = re.compile(r"^[ \t]*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE)
JAVASCRIPT_CLASS_PATTERN = re.compile(
    r"^[ \t]*(?:export\s+(?:default\s+)?)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE
)
JAVASCRIPT_FUNCTION_PATTERNS = (
    re.compile(
        r"^[ \t]*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+"
        r"([A-Za-z_$][\w$]*)\s*\(",
        re.MULTILINE,
    ),
    re.compile(
        r"^[ \t]*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
        r"(?:async\s*)?(?:\([^\n]*?\)|[A-Za-z_$][\w$]*)\s*=>",
        re.MULTILINE,
    ),
)
JAVA_CLASS_PATTERN = re.compile(r"^[ \t]*(?:public\s+)?class\s+([A-Za-z_]\w*)", re.MULTILINE)
JAVA_FUNCTION_PATTERN = re.compile(
    r"^[ \t]*(?:public|private|protected)?\s*(?:static\s+)?[A-Za-z_<>,?\[\]]+\s+"
    r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
    re.MULTILINE,
)
REQUIREMENT_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[^\]]+\])?\s*([<>=!~].*)?$")


class SecureRepositoryAnalyzer:
    """Inspect source metadata without executing source code or reading secret values."""

    def __init__(self, settings: Settings) -> None:
        self._max_file_bytes = settings.repository_analysis_max_file_bytes
        self._max_symbols = settings.repository_analysis_max_symbols
        self._max_folders = settings.repository_analysis_max_folders

    def analyze(self, source_root: Path) -> RepositoryAnalysisPayload:
        """Create a JSON-safe profile from a checked-out or extracted source tree."""
        if not source_root.is_dir():
            raise RepositoryAnalysisError(
                "The stored repository source is unavailable for analysis."
            )

        language_files: Counter[str] = Counter()
        language_lines: Counter[str] = Counter()
        folder_files: Counter[str] = Counter({".": 0})
        dependencies: dict[tuple[str, str], dict[str, str | None]] = {}
        frameworks: set[str] = set()
        environment_files: list[str] = []
        docker_files: list[str] = []
        classes: list[dict[str, object]] = []
        functions: list[dict[str, object]] = []
        services: list[dict[str, object]] = []
        database_artifacts: list[dict[str, str]] = []
        seen_service_paths: set[str] = set()
        seen_database_artifacts: set[tuple[str, str]] = set()
        total_files = 0
        total_bytes = 0
        total_lines = 0
        class_count = 0
        function_count = 0

        for file_path in self._iter_files(source_root):
            relative_path = file_path.relative_to(source_root).as_posix()
            name = file_path.name
            lowered_name = name.casefold()
            try:
                size_bytes = file_path.stat().st_size
            except OSError:
                continue

            total_files += 1
            total_bytes += size_bytes
            self._count_folders(folder_files, relative_path)
            language = self._language_for(file_path)
            if language:
                language_files[language] += 1
            if self._is_environment_file(lowered_name):
                environment_files.append(relative_path)
                # Environment files are catalogued by path only; their values are never read.
                continue
            if self._is_docker_file(lowered_name):
                docker_files.append(relative_path)
            if self._is_service_path(relative_path):
                self._append_service(services, seen_service_paths, relative_path, name, "file")
            if self._is_database_path(relative_path):
                self._append_database_artifact(
                    database_artifacts, seen_database_artifacts, relative_path, "repository_path"
                )
            if file_path.suffix.casefold() == ".sql":
                self._append_database_artifact(
                    database_artifacts, seen_database_artifacts, relative_path, "sql_file"
                )

            text, line_count = self._read_text_sample(file_path)
            if text is None:
                continue
            total_lines += line_count
            if language:
                language_lines[language] += line_count
            self._collect_dependencies(relative_path, text, dependencies)
            self._detect_source_frameworks(text, frameworks)
            class_matches, function_matches = self._symbol_matches(language, text)
            class_count += len(class_matches)
            function_count += len(function_matches)
            self._append_symbols(classes, class_matches, relative_path, language, "class")
            self._append_symbols(functions, function_matches, relative_path, language, "function")
            for name_value, line in class_matches:
                if name_value.casefold().endswith("service"):
                    self._append_service(
                        services, seen_service_paths, relative_path, name_value, "class", line
                    )

        for dependency in dependencies.values():
            normalized_name = dependency["name"].casefold()
            framework = FRAMEWORK_DEPENDENCIES.get(normalized_name)
            if framework:
                frameworks.add(framework)
            if normalized_name in DATABASE_DEPENDENCIES:
                self._append_database_artifact(
                    database_artifacts,
                    seen_database_artifacts,
                    dependency["name"],
                    "dependency",
                )

        results: dict[str, object] = {
            "statistics": {
                "total_files": total_files,
                "total_bytes": total_bytes,
                "total_lines": total_lines,
                "class_count": class_count,
                "function_count": function_count,
                "service_count": len(services),
                "database_artifact_count": len(database_artifacts),
            },
            "languages": [
                {
                    "name": language,
                    "files": language_files[language],
                    "lines": language_lines[language],
                }
                for language in sorted(
                    language_files, key=lambda item: (-language_files[item], item)
                )
            ],
            "frameworks": sorted(frameworks),
            "dependencies": sorted(
                dependencies.values(),
                key=lambda dependency: (dependency["ecosystem"], dependency["name"]),
            ),
            "folder_structure": self._folder_structure(folder_files),
            "environment_files": sorted(environment_files),
            "docker_files": sorted(docker_files),
            "symbols": {"classes": classes, "functions": functions},
            "services": services,
            "database_artifacts": database_artifacts,
        }
        return RepositoryAnalysisPayload(
            analysis_version=ANALYSIS_VERSION,
            results=results,
            file_count=total_files,
            line_count=total_lines,
        )

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
    def _language_for(file_path: Path) -> str | None:
        if file_path.name.casefold() == "dockerfile":
            return "Dockerfile"
        return LANGUAGE_BY_SUFFIX.get(file_path.suffix.casefold())

    def _read_text_sample(self, file_path: Path) -> tuple[str | None, int]:
        if file_path.suffix.casefold() in BINARY_SUFFIXES:
            return None, 0
        sample = bytearray()
        newline_count = 0
        has_content = False
        ends_with_newline = False
        try:
            with file_path.open("rb") as source:
                while chunk := source.read(64 * 1024):
                    if b"\x00" in chunk:
                        return None, 0
                    has_content = True
                    newline_count += chunk.count(b"\n")
                    ends_with_newline = chunk.endswith(b"\n")
                    if len(sample) < self._max_file_bytes:
                        sample.extend(chunk[: self._max_file_bytes - len(sample)])
        except OSError:
            return None, 0
        line_count = newline_count + int(has_content and not ends_with_newline)
        return sample.decode("utf-8", errors="replace"), line_count

    @staticmethod
    def _count_folders(folder_files: Counter[str], relative_path: str) -> None:
        folder_files["."] += 1
        parts = relative_path.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            folder_files["/".join(parts[:index])] += 1

    def _collect_dependencies(
        self,
        relative_path: str,
        text: str,
        dependencies: dict[tuple[str, str], dict[str, str | None]],
    ) -> None:
        file_name = Path(relative_path).name.casefold()
        if file_name == "package.json":
            self._collect_package_json(text, dependencies)
        elif file_name == "pyproject.toml":
            self._collect_pyproject(text, dependencies)
        elif file_name.startswith("requirements") and file_name.endswith(".txt"):
            self._collect_requirements(text, dependencies)
        elif file_name == "composer.json":
            self._collect_composer_json(text, dependencies)
        elif file_name == "cargo.toml":
            self._collect_cargo_toml(text, dependencies)

    def _collect_package_json(
        self, text: str, dependencies: dict[tuple[str, str], dict[str, str | None]]
    ) -> None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return
        for section in (
            "dependencies",
            "devDependencies",
            "peerDependencies",
            "optionalDependencies",
        ):
            values = payload.get(section, {})
            if isinstance(values, dict):
                for name, version in values.items():
                    if isinstance(name, str) and isinstance(version, str):
                        self._add_dependency(dependencies, name, version, "npm")

    def _collect_pyproject(
        self, text: str, dependencies: dict[tuple[str, str], dict[str, str | None]]
    ) -> None:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return
        project = payload.get("project", {})
        if isinstance(project, dict):
            project_dependencies = project.get("dependencies", [])
            if isinstance(project_dependencies, list):
                self._add_python_dependency_strings(project_dependencies, dependencies)
        tool = payload.get("tool", {})
        poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
        poetry_dependencies = poetry.get("dependencies", {}) if isinstance(poetry, dict) else {}
        if isinstance(poetry_dependencies, dict):
            for name, version in poetry_dependencies.items():
                if isinstance(name, str) and name.casefold() != "python":
                    self._add_dependency(dependencies, name, str(version), "python")

    def _collect_requirements(
        self, text: str, dependencies: dict[tuple[str, str], dict[str, str | None]]
    ) -> None:
        self._add_python_dependency_strings(text.splitlines(), dependencies)

    def _collect_composer_json(
        self, text: str, dependencies: dict[tuple[str, str], dict[str, str | None]]
    ) -> None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return
        for section in ("require", "require-dev"):
            values = payload.get(section, {})
            if isinstance(values, dict):
                for name, version in values.items():
                    if isinstance(name, str) and isinstance(version, str):
                        self._add_dependency(dependencies, name, version, "composer")

    def _collect_cargo_toml(
        self, text: str, dependencies: dict[tuple[str, str], dict[str, str | None]]
    ) -> None:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return
        values = payload.get("dependencies", {})
        if isinstance(values, dict):
            for name, version in values.items():
                if isinstance(name, str):
                    self._add_dependency(dependencies, name, str(version), "cargo")

    def _add_python_dependency_strings(
        self,
        values: list[object] | list[str],
        dependencies: dict[tuple[str, str], dict[str, str | None]],
    ) -> None:
        for value in values:
            if not isinstance(value, str):
                continue
            candidate = value.split("#", maxsplit=1)[0].strip()
            if not candidate or candidate.startswith(("-", ".", "http:")):
                continue
            match = REQUIREMENT_PATTERN.match(candidate)
            if match:
                self._add_dependency(
                    dependencies,
                    match.group(1),
                    match.group(2).strip() if match.group(2) else None,
                    "python",
                )

    @staticmethod
    def _add_dependency(
        dependencies: dict[tuple[str, str], dict[str, str | None]],
        name: str,
        version: str | None,
        ecosystem: str,
    ) -> None:
        normalized_name = name.casefold()
        dependencies[(ecosystem, normalized_name)] = {
            "name": name,
            "version": version,
            "ecosystem": ecosystem,
        }

    @staticmethod
    def _detect_source_frameworks(text: str, frameworks: set[str]) -> None:
        lowered_text = text.casefold()
        for marker, framework in SOURCE_FRAMEWORK_MARKERS.items():
            if marker in lowered_text:
                frameworks.add(framework)

    @staticmethod
    def _symbol_matches(
        language: str | None, text: str
    ) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
        if language == "Python":
            return (
                SecureRepositoryAnalyzer._matches(PYTHON_CLASS_PATTERN, text),
                SecureRepositoryAnalyzer._matches(PYTHON_FUNCTION_PATTERN, text),
            )
        if language in {"JavaScript", "TypeScript", "Vue", "Svelte"}:
            functions = []
            for pattern in JAVASCRIPT_FUNCTION_PATTERNS:
                functions.extend(SecureRepositoryAnalyzer._matches(pattern, text))
            return SecureRepositoryAnalyzer._matches(JAVASCRIPT_CLASS_PATTERN, text), functions
        if language in {"Java", "Kotlin"}:
            return (
                SecureRepositoryAnalyzer._matches(JAVA_CLASS_PATTERN, text),
                SecureRepositoryAnalyzer._matches(JAVA_FUNCTION_PATTERN, text),
            )
        return [], []

    @staticmethod
    def _matches(pattern: re.Pattern[str], text: str) -> list[tuple[str, int]]:
        return [
            (match.group(1), text.count("\n", 0, match.start()) + 1)
            for match in pattern.finditer(text)
        ]

    def _append_symbols(
        self,
        target: list[dict[str, object]],
        matches: list[tuple[str, int]],
        path: str,
        language: str | None,
        kind: str,
    ) -> None:
        for name, line in matches:
            if len(target) >= self._max_symbols:
                return
            target.append(
                {"name": name, "path": path, "line": line, "language": language, "kind": kind}
            )

    @staticmethod
    def _is_environment_file(name: str) -> bool:
        return name.startswith(".env") or name == ".envrc"

    @staticmethod
    def _is_docker_file(name: str) -> bool:
        return name.startswith("dockerfile") or name in {
            "compose.yaml",
            "compose.yml",
            "docker-compose.yaml",
            "docker-compose.yml",
        }

    @staticmethod
    def _is_service_path(path: str) -> bool:
        parts = [part.casefold() for part in path.split("/")]
        return any("service" in part for part in parts)

    @staticmethod
    def _is_database_path(path: str) -> bool:
        path_parts = [part.casefold() for part in path.split("/")]
        database_terms = ("database", "migration", "model", "orm", "prisma", "schema", "seed")
        return any(any(term in part for term in database_terms) for part in path_parts)

    @staticmethod
    def _append_service(
        services: list[dict[str, object]],
        seen_paths: set[str],
        path: str,
        name: str,
        kind: str,
        line: int | None = None,
    ) -> None:
        key = f"{path}:{kind}:{name}:{line or 0}"
        if key not in seen_paths:
            item: dict[str, object] = {"name": name, "path": path, "kind": kind}
            if line is not None:
                item["line"] = line
            services.append(item)
            seen_paths.add(key)

    @staticmethod
    def _append_database_artifact(
        artifacts: list[dict[str, str]],
        seen_artifacts: set[tuple[str, str]],
        path: str,
        reason: str,
    ) -> None:
        key = (path, reason)
        if key not in seen_artifacts:
            artifacts.append({"path": path, "reason": reason})
            seen_artifacts.add(key)

    def _folder_structure(self, folder_files: Counter[str]) -> list[dict[str, object]]:
        folders = sorted(folder_files, key=lambda path: (path.count("/"), path))[
            : self._max_folders
        ]
        return [
            {
                "path": path,
                "file_count": folder_files[path],
                "depth": 0 if path == "." else path.count("/") + 1,
            }
            for path in folders
        ]
