"""Utilities for discovering and caching dbt doc blocks.

Doc blocks can be placed in:
1. Profile-specific docs folders (preferred):
   - `.sqlbot/profiles/{profile}/docs/`
   - `profiles/{profile}/docs/`
2. Project root docs folder:
   - `docs/` (standard dbt location)
3. Embedded in model/macro files:
   - Any `.sql`, `.md`, `.yml`, or `.yaml` file in `models/` or `macros/` directories

Doc blocks are defined using: {% docs name %}...content...{% enddocs %}
And referenced in schema.yml using: {{ doc('name') }}
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Set

import yaml

DOC_BLOCK_PATTERN = re.compile(
    r"{%\s*docs\s+([\w\-.]+)\s*%}(.*?){%\s*enddocs\s*%}",
    re.IGNORECASE | re.DOTALL,
)
DOC_FILE_EXTENSIONS = {".md", ".sql", ".txt", ".yml", ".yaml"}
SUBDIRECTORIES_TO_SCAN = ("docs", "models", "macros")
DOC_REFERENCE_PATTERN = re.compile(r"{{\s*doc\(\s*['\"]([\w\-.]+)['\"]\s*\)\s*}}")


@dataclass
class DocBlock:
    """Representation of a single dbt doc block."""

    name: str
    content: str
    file_path: str
    hash: str


@dataclass
class DocBlockCacheEntry:
    """Cached doc block information and file metadata."""

    blocks: Dict[str, DocBlock]
    file_mtimes: Dict[str, float]
    timestamp: float

    def is_stale(self) -> bool:
        """Detect if any contributing file is missing or has changed."""
        for path, previous_mtime in self.file_mtimes.items():
            try:
                current_mtime = Path(path).stat().st_mtime
            except OSError:
                return True

            if abs(current_mtime - previous_mtime) > 1e-6:
                return True

        return False


class DocBlockCache:
    """Simple profile-scoped cache for doc blocks."""

    _entries: Dict[str, DocBlockCacheEntry] = {}

    @classmethod
    def get_or_load(cls, profile_name: str, force_refresh: bool = False) -> Dict[str, DocBlock]:
        entry = cls._entries.get(profile_name)

        if entry and not force_refresh and not entry.is_stale():
            return entry.blocks

        blocks, file_mtimes = discover_doc_blocks(profile_name)
        cls._entries[profile_name] = DocBlockCacheEntry(
            blocks=blocks,
            file_mtimes=file_mtimes,
            timestamp=time.time(),
        )
        return blocks

    @classmethod
    def invalidate(cls, profile_name: str | None = None) -> None:
        if profile_name is None:
            cls._entries.clear()
        else:
            cls._entries.pop(profile_name, None)


def get_project_root() -> Path:
    """Return project root relative to this module."""
    current_file = Path(__file__).resolve()
    if len(current_file.parents) >= 3:
        return current_file.parents[2]
    return Path(os.getcwd())


def get_doc_search_paths(profile_name: str) -> List[Path]:
    """Build prioritized list of directories to scan for doc blocks."""
    project_root = get_project_root()

    priority_bases = [
        project_root / ".sqlbot" / "profiles" / profile_name,
        project_root / "profiles" / profile_name,
        project_root,
    ]

    search_paths: List[Path] = []
    seen = set()

    for base in priority_bases:
        for subdir in SUBDIRECTORIES_TO_SCAN:
            candidate = base / subdir if base != project_root else base / subdir
            try:
                resolved = candidate.resolve()
            except FileNotFoundError:
                continue

            if resolved.exists() and resolved not in seen:
                seen.add(resolved)
                search_paths.append(resolved)

    return search_paths


def iter_doc_files(paths: Iterable[Path]) -> Iterable[Path]:
    """Yield candidate files that may contain doc blocks."""
    seen: set[Path] = set()

    for base in paths:
        if not base.is_dir():
            continue

        for extension in DOC_FILE_EXTENSIONS:
            for file_path in base.rglob(f"*{extension}"):
                resolved = file_path.resolve()
                if resolved in seen or not resolved.is_file():
                    continue
                seen.add(resolved)
                yield resolved


def normalize_doc_text(raw_text: str) -> str:
    """Normalize whitespace so caching/hashing remains stable."""
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def parse_doc_blocks_from_file(file_path: Path) -> List[DocBlock]:
    """Parse doc blocks from a single file, returning structured entries."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    blocks: List[DocBlock] = []

    for match in DOC_BLOCK_PATTERN.finditer(content):
        name = match.group(1).strip()
        raw_body = match.group(2)
        normalized = normalize_doc_text(raw_body)
        block_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        blocks.append(
            DocBlock(
                name=name,
                content=normalized,
                file_path=str(file_path),
                hash=block_hash,
            )
        )

    return blocks


def discover_doc_blocks(profile_name: str) -> Tuple[Dict[str, DocBlock], Dict[str, float]]:
    """Return doc blocks and contributing file mtimes for caching."""
    doc_blocks: Dict[str, DocBlock] = {}
    file_mtimes: Dict[str, float] = {}
    search_paths = get_doc_search_paths(profile_name)

    for path in search_paths:
        for file_path in iter_doc_files([path]):
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                continue

            # Track mtime for ALL scanned files, not just those with new blocks
            # This ensures cache detects changes even if file has no blocks or only duplicates
            file_mtimes[str(file_path)] = mtime

            for block in parse_doc_blocks_from_file(file_path):
                if block.name not in doc_blocks:
                    doc_blocks[block.name] = block

    return doc_blocks, file_mtimes


def load_doc_blocks(profile_name: str) -> Dict[str, DocBlock]:
    """Convenience wrapper returning just the doc block mapping."""
    blocks, _ = discover_doc_blocks(profile_name)
    return blocks


def build_doc_block_digest(schema_text: str, doc_blocks: Dict[str, DocBlock]) -> str:
    """
    Build a human-friendly digest of doc block content referenced in schema descriptions.
    """
    if not schema_text:
        return ""

    try:
        schema_data = yaml.safe_load(schema_text) or {}
    except yaml.YAMLError:
        return ""

    resolved_lines: List[str] = []
    missing_lines: List[str] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    sources = schema_data.get('sources', []) if isinstance(schema_data, dict) else []

    for source in sources:
        if not isinstance(source, dict):
            continue
        source_name = source.get('name', 'unknown_source')

        for table in source.get('tables', []) or []:
            if not isinstance(table, dict):
                continue

            table_name = table.get('name', 'unknown_table')
            table_context = f"{source_name}.{table_name}"
            _collect_doc_entries(
                table.get('description'),
                table_context,
                doc_blocks,
                resolved_lines,
                missing_lines,
                seen_pairs,
            )

            for column in table.get('columns', []) or []:
                if not isinstance(column, dict):
                    continue
                column_name = column.get('name', 'unknown_column')
                column_context = f"{table_context}.{column_name}"
                _collect_doc_entries(
                    column.get('description'),
                    column_context,
                    doc_blocks,
                    resolved_lines,
                    missing_lines,
                    seen_pairs,
                )

    if not resolved_lines and not missing_lines:
        return ""

    lines = ["Resolved documentation from dbt doc blocks:"]
    lines.extend(resolved_lines)

    if missing_lines:
        lines.append("")
        lines.append("Missing doc blocks referenced in schema:")
        lines.extend(missing_lines)

    return "\n".join(lines)


def _collect_doc_entries(
    description: object,
    context: str,
    doc_blocks: Dict[str, DocBlock],
    resolved_lines: List[str],
    missing_lines: List[str],
    seen_pairs: Set[Tuple[str, str]],
) -> None:
    if not isinstance(description, str):
        return

    doc_names = extract_doc_references(description)

    for doc_name in doc_names:
        key = (context, doc_name)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        block = doc_blocks.get(doc_name)

        if block:
            summary = summarize_doc_text(block.content)
            indented_summary = "\n  ".join(summary.splitlines()) if summary else "(empty doc block)"
            resolved_lines.append(
                f"- {context} (doc '{doc_name}'):\n  {indented_summary}"
            )
        else:
            missing_lines.append(
                f"- {context} references doc('{doc_name}') but no doc block was found."
            )


def extract_doc_references(text: str) -> List[str]:
    """Return all doc('name') references inside a text string."""
    return DOC_REFERENCE_PATTERN.findall(text) if isinstance(text, str) else []


def summarize_doc_text(text: str, limit: int = 600) -> str:
    """Summarize doc block content for prompt inclusion."""
    if not isinstance(text, str):
        return ""

    normalized = text.strip()
    if not normalized:
        return ""

    if limit and len(normalized) > limit:
        return normalized[:limit].rstrip() + "..."
    return normalized