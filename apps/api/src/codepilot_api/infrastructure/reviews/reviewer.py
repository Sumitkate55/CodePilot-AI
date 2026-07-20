"""Bounded static repository code reviewer that never executes source code."""

from __future__ import annotations

import ast
import hashlib
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from codepilot_api.config.settings import Settings
from codepilot_api.domain.reviews.entities import (
    CodeReviewCategory,
    CodeReviewFinding,
    CodeReviewSeverity,
    RepositoryCodeReviewPayload,
)
from codepilot_api.domain.reviews.errors import RepositoryCodeReviewError
from codepilot_api.infrastructure.repositories.analyzer import BINARY_SUFFIXES, SKIPPED_DIRECTORIES

REVIEW_VERSION = 1
MAX_REVIEW_FINDINGS = 250
MAX_REVIEW_FILES = 10_000
LONG_FUNCTION_LINES = 80
SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".cs",
}
SENSITIVE_FILE_PARTS = ("credential", "secret", "private", "id_rsa")
SECURITY_RULES = (
    (
        re.compile(r"\b(?:eval|exec)\s*\("),
        "Dynamic code execution",
        "Dynamic evaluation can execute untrusted input when data reaches this call.",
        "Avoid dynamic execution. Use a strict parser or an explicit allowlist instead.",
        CodeReviewSeverity.HIGH,
        96,
    ),
    (
        re.compile(r"\bsubprocess\.(?:run|call|Popen|check_output)\s*\([^\n]*shell\s*=\s*True"),
        "Shell command interpolation risk",
        "A command is executed through a shell, which can permit command injection.",
        "Pass an argument list with shell disabled and validate every external input.",
        CodeReviewSeverity.HIGH,
        93,
    ),
    (
        re.compile(r"\bos\.system\s*\("),
        "Shell command interpolation risk",
        "A command is executed through a shell, which can permit command injection.",
        "Use subprocess with an argument list, shell disabled, and validated external input.",
        CodeReviewSeverity.HIGH,
        91,
    ),
    (
        re.compile(r"\bpickle\.loads?\s*\("),
        "Unsafe deserialization",
        "Pickle data can execute code while it is deserialized.",
        "Use a data-only format such as JSON for untrusted input.",
        CodeReviewSeverity.HIGH,
        95,
    ),
    (
        re.compile(r"\byaml\.load\s*\("),
        "Potential unsafe YAML loading",
        "YAML loading without an explicit safe loader may construct arbitrary objects.",
        "Use safe_load or explicitly provide a safe loader.",
        CodeReviewSeverity.MEDIUM,
        82,
    ),
    (
        re.compile(r"\b(?:execute|query)\s*\(\s*f[\"']"),
        "Interpolated database query",
        "String interpolation in a database call can create an injection path.",
        "Use parameterized queries and bind values separately from SQL text.",
        CodeReviewSeverity.HIGH,
        86,
    ),
)
HARDCODED_CREDENTIAL_PATTERN = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*[\"'][^\"']{8,}"
)


class SecureRepositoryCodeReviewer:
    """Find high-signal source risks while keeping review work bounded and deterministic."""

    def __init__(self, settings: Settings) -> None:
        self._max_file_bytes = settings.repository_analysis_max_file_bytes

    def review(self, source_root: Path) -> RepositoryCodeReviewPayload:
        """Review safe source files without reading environment or credential-like files."""
        if not source_root.is_dir():
            raise RepositoryCodeReviewError(
                "The stored repository source is unavailable for review."
            )

        findings: list[CodeReviewFinding] = []
        duplicate_blocks: dict[str, list[tuple[str, int]]] = defaultdict(list)
        scanned_file_count = 0
        for file_path in self._iter_files(source_root):
            if scanned_file_count >= MAX_REVIEW_FILES:
                break
            relative_path = file_path.relative_to(source_root).as_posix()
            if not self._is_reviewable(relative_path, file_path):
                continue
            text = self._read_text(file_path)
            if text is None:
                continue
            scanned_file_count += 1
            self._scan_security(findings, relative_path, text)
            self._scan_code_smells(findings, relative_path, text)
            self._scan_performance(findings, relative_path, text)
            self._scan_python_functions(findings, relative_path, text)
            self._collect_duplicate_blocks(duplicate_blocks, relative_path, text)

        self._append_duplicate_findings(findings, duplicate_blocks)
        findings.sort(key=self._sort_key)
        return RepositoryCodeReviewPayload(
            review_version=REVIEW_VERSION,
            findings=tuple(findings[:MAX_REVIEW_FINDINGS]),
            scanned_file_count=scanned_file_count,
        )

    @staticmethod
    def _iter_files(source_root: Path):
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
    def _is_reviewable(relative_path: str, file_path: Path) -> bool:
        parts = [part.casefold() for part in relative_path.split("/")]
        if file_path.suffix.casefold() not in SOURCE_SUFFIXES:
            return False
        if file_path.suffix.casefold() in BINARY_SUFFIXES:
            return False
        if any(part.startswith(".env") for part in parts):
            return False
        return not any(term in part for part in parts for term in SENSITIVE_FILE_PARTS)

    def _read_text(self, file_path: Path) -> str | None:
        try:
            if file_path.stat().st_size > self._max_file_bytes:
                return None
            content = file_path.read_bytes()
        except OSError:
            return None
        if b"\x00" in content:
            return None
        return content.decode("utf-8", errors="replace")

    def _scan_security(self, findings: list[CodeReviewFinding], path: str, text: str) -> None:
        for pattern, title, description, recommendation, severity, confidence in SECURITY_RULES:
            for match in pattern.finditer(text):
                self._add(
                    findings,
                    CodeReviewCategory.SECURITY,
                    severity,
                    confidence,
                    title,
                    description,
                    recommendation,
                    path,
                    self._line_number(text, match.start()),
                )
        for match in HARDCODED_CREDENTIAL_PATTERN.finditer(text):
            self._add(
                findings,
                CodeReviewCategory.SECURITY,
                CodeReviewSeverity.HIGH,
                78,
                "Potential hard-coded credential",
                "A credential-like variable is assigned a literal value in source code.",
                "Move the value to a managed secret or environment variable and rotate it if real.",
                path,
                self._line_number(text, match.start()),
            )

    def _scan_code_smells(self, findings: list[CodeReviewFinding], path: str, text: str) -> None:
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped == "except:":
                self._add(
                    findings,
                    CodeReviewCategory.CODE_SMELL,
                    CodeReviewSeverity.MEDIUM,
                    92,
                    "Bare exception handler",
                    (
                        "This handler catches every exception, including interrupts and "
                        "programming errors."
                    ),
                    "Catch the expected exception types and handle each failure explicitly.",
                    path,
                    line_number,
                )
            elif re.match(r"except\s+Exception\b", stripped):
                self._add(
                    findings,
                    CodeReviewCategory.CODE_SMELL,
                    CodeReviewSeverity.LOW,
                    84,
                    "Broad exception handler",
                    "Catching Exception can hide unexpected failures and reduce observability.",
                    (
                        "Catch the narrowest expected exception types and add context before "
                        "re-raising."
                    ),
                    path,
                    line_number,
                )
            if re.search(r"\b(?:TODO|FIXME)\b", stripped, flags=re.IGNORECASE):
                self._add(
                    findings,
                    CodeReviewCategory.CODE_SMELL,
                    CodeReviewSeverity.LOW,
                    76,
                    "Unresolved maintenance marker",
                    "A TODO or FIXME indicates unfinished behavior in a tracked source file.",
                    "Track the work in an issue or complete it before the next release.",
                    path,
                    line_number,
                )
            if re.search(r"\bconsole\.log\s*\(", stripped):
                self._add(
                    findings,
                    CodeReviewCategory.CODE_SMELL,
                    CodeReviewSeverity.LOW,
                    88,
                    "Debug console output",
                    (
                        "Console output can leak implementation details and bypass "
                        "application logging."
                    ),
                    "Remove the statement or replace it with the project's structured logger.",
                    path,
                    line_number,
                )

    def _scan_performance(self, findings: list[CodeReviewFinding], path: str, text: str) -> None:
        lines = text.splitlines()
        loop_lines: list[tuple[int, int]] = []
        for line_number, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            indentation = len(line) - len(stripped)
            if re.match(r"(?:async\s+)?for\s+", stripped) or re.match(r"for\s*\(", stripped):
                loop_lines.append((line_number, indentation))
            if re.search(r"\bfor\s+\w+\s+in\s+[^#\n]*\.all\s*\(\)", line):
                self._add(
                    findings,
                    CodeReviewCategory.PERFORMANCE,
                    CodeReviewSeverity.MEDIUM,
                    78,
                    "Unbounded collection inside a loop",
                    (
                        "Loading every record as part of loop work can grow memory and query "
                        "cost quickly."
                    ),
                    "Paginate or filter the query and batch work where possible.",
                    path,
                    line_number,
                )
            if re.search(r"\brange\s*\(\s*len\s*\(", line):
                self._add(
                    findings,
                    CodeReviewCategory.PERFORMANCE,
                    CodeReviewSeverity.LOW,
                    70,
                    "Index-based collection iteration",
                    "Index iteration is harder to read and can add unnecessary lookups.",
                    "Iterate directly over items or use enumerate when an index is required.",
                    path,
                    line_number,
                )
        for outer_line, outer_indent in loop_lines:
            if any(
                inner_line > outer_line
                and inner_line <= outer_line + 40
                and inner_indent > outer_indent
                for inner_line, inner_indent in loop_lines
            ):
                self._add(
                    findings,
                    CodeReviewCategory.PERFORMANCE,
                    CodeReviewSeverity.MEDIUM,
                    61,
                    "Nested loop may grow quadratically",
                    "A loop contains another loop, which may become expensive as input sizes grow.",
                    (
                        "Measure the hot path and consider indexing, batching, or a more "
                        "direct algorithm."
                    ),
                    path,
                    outer_line,
                )

    def _scan_python_functions(
        self, findings: list[CodeReviewFinding], path: str, text: str
    ) -> None:
        if not path.endswith(".py"):
            return
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return
        name_counts = Counter(re.findall(r"\b[A-Za-z_]\w*\b", text))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end_line = getattr(node, "end_lineno", node.lineno)
            line_count = end_line - node.lineno + 1
            if line_count > LONG_FUNCTION_LINES:
                self._add(
                    findings,
                    CodeReviewCategory.LONG_FUNCTION,
                    CodeReviewSeverity.MEDIUM,
                    97,
                    "Long function",
                    (
                        f"This function spans {line_count} lines, which makes it harder to "
                        "test and change safely."
                    ),
                    "Extract cohesive steps into smaller functions with focused responsibilities.",
                    path,
                    node.lineno,
                    end_line,
                )
            if not node.name.startswith("__") and not re.fullmatch(r"[a-z_][a-z0-9_]*", node.name):
                self._add(
                    findings,
                    CodeReviewCategory.NAMING,
                    CodeReviewSeverity.LOW,
                    96,
                    "Python function name is not snake_case",
                    f"{node.name} does not follow the conventional Python function naming style.",
                    "Rename the function to a clear snake_case verb phrase and update its callers.",
                    path,
                    node.lineno,
                )
            if (
                node.name.startswith("_")
                and not node.name.startswith("__")
                and name_counts.get(node.name, 0) == 1
            ):
                self._add(
                    findings,
                    CodeReviewCategory.DEAD_CODE,
                    CodeReviewSeverity.LOW,
                    48,
                    "Possibly unused private function",
                    (
                        "This private function appears only at its declaration in the scanned "
                        "source tree."
                    ),
                    (
                        "Confirm it is not called dynamically or imported externally, then "
                        "remove it or add a caller."
                    ),
                    path,
                    node.lineno,
                )

    @staticmethod
    def _collect_duplicate_blocks(
        blocks: dict[str, list[tuple[str, int]]], path: str, text: str
    ) -> None:
        if Path(path).suffix.casefold() not in SOURCE_SUFFIXES:
            return
        meaningful_lines = [
            (line_number, SecureRepositoryCodeReviewer._normalize_line(line))
            for line_number, line in enumerate(text.splitlines(), start=1)
            if SecureRepositoryCodeReviewer._normalize_line(line)
        ]
        for index in range(len(meaningful_lines) - 5):
            block = meaningful_lines[index : index + 6]
            normalized = "\n".join(line for _, line in block)
            if len(normalized) < 70:
                continue
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            location = (path, block[0][0])
            if not blocks[digest] or blocks[digest][-1] != location:
                blocks[digest].append(location)

    @staticmethod
    def _append_duplicate_findings(
        findings: list[CodeReviewFinding], blocks: dict[str, list[tuple[str, int]]]
    ) -> None:
        for locations in blocks.values():
            unique_locations = list(dict.fromkeys(locations))
            if len(unique_locations) < 2:
                continue
            original_path, original_line = unique_locations[0]
            for path, line in unique_locations[1:3]:
                SecureRepositoryCodeReviewer._add(
                    findings,
                    CodeReviewCategory.DUPLICATE_CODE,
                    CodeReviewSeverity.LOW,
                    87,
                    "Duplicated source block",
                    (
                        f"A matching multi-line block also appears in {original_path} at line "
                        f"{original_line}."
                    ),
                    "Extract the shared behavior into a named function or shared module.",
                    path,
                    line,
                    line + 5,
                )

    @staticmethod
    def _normalize_line(line: str) -> str:
        without_comment = re.split(r"(?:#|//)", line, maxsplit=1)[0]
        normalized = re.sub(r"\s+", " ", without_comment).strip()
        return normalized

    @staticmethod
    def _line_number(text: str, index: int) -> int:
        return text.count("\n", 0, index) + 1

    @staticmethod
    def _add(
        findings: list[CodeReviewFinding],
        category: CodeReviewCategory,
        severity: CodeReviewSeverity,
        confidence: int,
        title: str,
        description: str,
        recommendation: str,
        path: str,
        start_line: int,
        end_line: int | None = None,
    ) -> None:
        line_end = end_line or start_line
        key_source = f"{category}:{title}:{path}:{start_line}:{line_end}"
        key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:16]
        if any(finding.key == key for finding in findings):
            return
        findings.append(
            CodeReviewFinding(
                key=key,
                category=category,
                severity=severity,
                confidence=max(0, min(confidence, 100)),
                title=title,
                description=description,
                recommendation=recommendation,
                path=path,
                start_line=start_line,
                end_line=line_end,
            )
        )

    @staticmethod
    def _sort_key(finding: CodeReviewFinding) -> tuple[int, str, int, str]:
        order = {
            CodeReviewSeverity.CRITICAL: 0,
            CodeReviewSeverity.HIGH: 1,
            CodeReviewSeverity.MEDIUM: 2,
            CodeReviewSeverity.LOW: 3,
        }
        return order[finding.severity], finding.path, finding.start_line, finding.title
