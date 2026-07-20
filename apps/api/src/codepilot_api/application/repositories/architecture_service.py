"""Deterministic architecture graph and source-preview use cases."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from uuid import UUID

from codepilot_api.application.repositories.contracts import (
    RepositoryAnalysisStore,
    RepositoryCatalog,
    RepositoryStorage,
)
from codepilot_api.domain.repositories.architecture import (
    ArchitectureGraphEdge,
    ArchitectureGraphNode,
    ArchitectureNodeKind,
    RepositoryArchitectureGraph,
    RepositorySourceFile,
)
from codepilot_api.domain.repositories.errors import (
    RepositoryAnalysisError,
    RepositoryAnalysisNotFound,
    RepositoryNotFound,
)

MAX_GRAPH_COMPONENTS = 16
MAX_SOURCE_PREVIEW_BYTES = 256 * 1024
SENSITIVE_FILE_PARTS = ("credential", "secret", "private", "id_rsa")
FRONTEND_PATH_MARKERS = ("client", "frontend", "ui", "web")
BACKEND_PATH_MARKERS = ("api", "backend", "server")


class RepositoryArchitectureService:
    """Build a traceable graph from saved intelligence and open safe source files."""

    def __init__(
        self,
        repository_catalog: RepositoryCatalog,
        analysis_store: RepositoryAnalysisStore,
        storage: RepositoryStorage,
    ) -> None:
        self._repository_catalog = repository_catalog
        self._analysis_store = analysis_store
        self._storage = storage

    async def get_latest_graph(
        self, owner_id: UUID, repository_id: UUID
    ) -> RepositoryArchitectureGraph:
        """Create a bounded architecture graph from the latest saved analysis record."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        analysis = await self._analysis_store.get_by_version(version.id)
        if analysis is None:
            raise RepositoryAnalysisNotFound
        return self._build_graph(
            repository.name, version.id, analysis.analysis_version, analysis.results
        )

    async def read_latest_file(
        self, owner_id: UUID, repository_id: UUID, requested_path: str
    ) -> RepositorySourceFile:
        """Return a bounded UTF-8 source preview for the latest owned repository version."""
        repository = await self._get_repository(owner_id, repository_id)
        version = self._latest_version(repository)
        relative_path = self._safe_relative_path(requested_path)
        if self._is_sensitive(relative_path):
            raise RepositoryAnalysisError("This file cannot be opened in CodePilot.")
        source_root = self._storage.resolve_storage_key(version.storage_key)
        file_path = (source_root / relative_path).resolve()
        try:
            file_path.relative_to(source_root.resolve())
        except ValueError as error:
            raise RepositoryAnalysisError("The requested file path is invalid.") from error
        if not file_path.is_file() or file_path.is_symlink():
            raise RepositoryAnalysisError("The requested source file is unavailable.")
        try:
            content = file_path.read_bytes()
        except OSError as error:
            raise RepositoryAnalysisError("The requested source file could not be read.") from error
        if len(content) > MAX_SOURCE_PREVIEW_BYTES:
            raise RepositoryAnalysisError("This file is too large to open in CodePilot.")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RepositoryAnalysisError("This file is not UTF-8 text.") from error
        return RepositorySourceFile(
            repository_version_id=version.id,
            path=relative_path.as_posix(),
            content=text,
            language=self._language_for(relative_path),
        )

    async def _get_repository(self, owner_id: UUID, repository_id: UUID):
        repository = await self._repository_catalog.get_by_owner(owner_id, repository_id)
        if repository is None:
            raise RepositoryNotFound
        return repository

    @staticmethod
    def _latest_version(repository):
        if not repository.versions:
            raise RepositoryAnalysisNotFound
        return repository.versions[0]

    @staticmethod
    def _safe_relative_path(value: str) -> PurePosixPath:
        path = PurePosixPath(value)
        if path.is_absolute() or not path.parts or ".." in path.parts or path.name in {"", "."}:
            raise RepositoryAnalysisError("The requested file path is invalid.")
        return path

    @staticmethod
    def _is_sensitive(path: PurePosixPath) -> bool:
        parts = [part.casefold() for part in path.parts]
        return any(part.startswith(".env") for part in parts) or any(
            sensitive in part for part in parts for sensitive in SENSITIVE_FILE_PARTS
        )

    @staticmethod
    def _language_for(path: PurePosixPath) -> str | None:
        suffixes = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".java": "Java",
            ".sql": "SQL",
            ".json": "JSON",
            ".yml": "YAML",
            ".yaml": "YAML",
        }
        return suffixes.get(path.suffix.casefold())

    @staticmethod
    def _build_graph(
        repository_name: str,
        repository_version_id: UUID,
        analysis_version: int,
        results: dict[str, object],
    ) -> RepositoryArchitectureGraph:
        nodes: list[ArchitectureGraphNode] = [
            ArchitectureGraphNode(
                id="repository",
                kind=ArchitectureNodeKind.REPOSITORY,
                label=repository_name,
                description="Latest analyzed repository version",
            )
        ]
        edges: list[ArchitectureGraphEdge] = []

        folders = results.get("folder_structure", [])
        folder_items = folders if isinstance(folders, list) else []
        top_folders = [
            item
            for item in folder_items
            if isinstance(item, dict)
            and isinstance(item.get("path"), str)
            and item["path"] != "."
            and int(item.get("depth", 0)) == 1
        ][:MAX_GRAPH_COMPONENTS]
        frameworks = results.get("frameworks", [])
        framework_names = {value for value in frameworks if isinstance(value, str)}
        frontend = [
            item
            for item in top_folders
            if RepositoryArchitectureService._matches_path(item, FRONTEND_PATH_MARKERS)
            or (
                str(item["path"]) == "src"
                and bool({"Angular", "React", "Svelte", "Vue"} & framework_names)
            )
        ]
        backend = [
            item
            for item in top_folders
            if RepositoryArchitectureService._matches_path(item, BACKEND_PATH_MARKERS)
        ]
        classified = {str(item["path"]) for item in [*frontend, *backend]}
        if frontend:
            RepositoryArchitectureService._append_group_node(
                nodes, edges, "frontend", ArchitectureNodeKind.FRONTEND, "Frontend", frontend
            )
        if backend:
            RepositoryArchitectureService._append_group_node(
                nodes, edges, "backend", ArchitectureNodeKind.BACKEND, "Backend", backend
            )
        for item in top_folders:
            path = str(item["path"])
            if path not in classified:
                node_id = f"source:{path}"
                nodes.append(
                    ArchitectureGraphNode(
                        id=node_id,
                        kind=ArchitectureNodeKind.SOURCE,
                        label=path,
                        description=f"{int(item.get('file_count', 0))} analyzed files",
                    )
                )
                edges.append(ArchitectureGraphEdge(f"repository->{node_id}", "repository", node_id))

        services = results.get("services", [])
        service_items = services if isinstance(services, list) else []
        for index, item in enumerate(service_items[:MAX_GRAPH_COMPONENTS]):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            path = str(item["path"])
            name = str(item.get("name") or Path(path).stem)
            node_id = f"service:{index}:{path}"
            nodes.append(
                ArchitectureGraphNode(
                    id=node_id,
                    kind=ArchitectureNodeKind.SERVICE,
                    label=name,
                    description=f"Service discovered in {path}",
                    file_path=path,
                    line=RepositoryArchitectureService._optional_int(item.get("line")),
                )
            )
            parent = "backend" if backend else "repository"
            edges.append(ArchitectureGraphEdge(f"{parent}->{node_id}", parent, node_id, "contains"))

        artifacts = results.get("database_artifacts", [])
        artifact_items = artifacts if isinstance(artifacts, list) else []
        for index, item in enumerate(artifact_items[:MAX_GRAPH_COMPONENTS]):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            path = str(item["path"])
            if "/" not in path and Path(path).suffix == "":
                continue
            node_id = f"database:{index}:{path}"
            nodes.append(
                ArchitectureGraphNode(
                    id=node_id,
                    kind=ArchitectureNodeKind.DATABASE,
                    label=Path(path).name,
                    description=f"Database artifact: {item.get('reason', 'detected')}",
                    file_path=path,
                )
            )
            parent = "backend" if backend else "repository"
            edges.append(ArchitectureGraphEdge(f"{parent}->{node_id}", parent, node_id, "data"))

        docker_files = results.get("docker_files", [])
        docker_items = docker_files if isinstance(docker_files, list) else []
        for index, value in enumerate(docker_items[:MAX_GRAPH_COMPONENTS]):
            if not isinstance(value, str):
                continue
            node_id = f"infrastructure:{index}:{value}"
            nodes.append(
                ArchitectureGraphNode(
                    id=node_id,
                    kind=ArchitectureNodeKind.INFRASTRUCTURE,
                    label=Path(value).name,
                    description="Container or deployment configuration",
                    file_path=value,
                )
            )
            edges.append(
                ArchitectureGraphEdge(f"repository->{node_id}", "repository", node_id, "deploys")
            )

        return RepositoryArchitectureGraph(
            repository_version_id=repository_version_id,
            analysis_version=analysis_version,
            nodes=tuple(nodes),
            edges=tuple(edges),
        )

    @staticmethod
    def _matches_path(item: dict[str, object], markers: tuple[str, ...]) -> bool:
        path = str(item["path"]).casefold()
        return any(marker in path for marker in markers)

    @staticmethod
    def _append_group_node(
        nodes: list[ArchitectureGraphNode],
        edges: list[ArchitectureGraphEdge],
        node_id: str,
        kind: ArchitectureNodeKind,
        label: str,
        folders: list[dict[str, object]],
    ) -> None:
        file_count = sum(int(item.get("file_count", 0)) for item in folders)
        nodes.append(
            ArchitectureGraphNode(
                id=node_id,
                kind=kind,
                label=label,
                description=f"{file_count} analyzed files across {len(folders)} top-level folders",
            )
        )
        edges.append(ArchitectureGraphEdge(f"repository->{node_id}", "repository", node_id))

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return value if isinstance(value, int) else None
