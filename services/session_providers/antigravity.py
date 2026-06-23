from __future__ import annotations

import hashlib
import json
import platform
import sqlite3
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from services.session_providers.base import (
    HealthStatus,
    JsonObject,
    NormalizedSession,
    ProviderCursor,
    RawSession,
    SessionProvider,
    SourcePath,
    SummaryResult,
    WritebackCandidate,
)

DetectedFormat = Literal[
    "json",
    "jsonl",
    "sqlite",
    "markdown",
    "text",
    "unknown_binary",
]

AIOS_DB_PATH = Path.home() / "AIOS" / "data" / "aios.db"
SQLITE_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".vscdb"}
TEXT_EXTENSIONS = {
    ".cfg",
    ".conf",
    ".ini",
    ".log",
    ".out",
    ".prompt",
    ".txt",
    ".yaml",
    ".yml",
}
SESSION_NAME_PARTS = (
    "cache",
    "config",
    "conversation",
    "history",
    "log",
    "session",
    "transcript",
)
REASONING_NAME_PARTS = (
    "chain-of-thought",
    "chain_of_thought",
    "cot",
    "internal-monologue",
    "internal_monologue",
    "reasoning",
    "scratchpad",
    "thought",
)
COMMAND_KEYS = {"cmd", "command", "shell", "terminal_command"}
FILE_KEYS = {"file", "files", "path", "paths", "target_file"}
FILE_DETAIL_KEYS = {"action", "file", "name", "path", "target_file"}
TASK_KEYS = {"goal", "objective", "prompt", "task", "title"}
WORKSPACE_KEYS = {"cwd", "repo", "repository", "workspace", "workspace_path"}
DECISION_KEYS = {"decision", "decisions", "resolution"}
ERROR_KEYS = {"error", "errors", "exception", "failure", "failures"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _iso_from_mtime(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, UTC).isoformat()


def _short_text(value: object, *, limit: int = 240) -> str:
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _append_unique(target: list[str], value: object, *, limit: int = 240) -> None:
    text = _short_text(value, limit=limit)
    if text and text not in target:
        target.append(text)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_stat(path: Path) -> JsonObject:
    stat = path.stat()
    return {
        "path": str(path),
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "content_hash": _sha256_file(path),
    }


def _is_probably_text(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _first_line(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return handle.readline()
    except OSError:
        return ""


def _detect_file_format(path: Path) -> DetectedFormat:
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return "text" if _is_probably_text(path) else "unknown_binary"
        return "json"
    if suffix == ".jsonl":
        first_line = _first_line(path).strip()
        if first_line:
            try:
                json.loads(first_line)
            except json.JSONDecodeError:
                return "text" if _is_probably_text(path) else "unknown_binary"
        return "jsonl"
    if suffix in SQLITE_EXTENSIONS:
        try:
            if path.read_bytes()[:16] == b"SQLite format 3\x00":
                return "sqlite"
        except OSError:
            return "unknown_binary"
        return "unknown_binary"
    if suffix == ".md":
        return "markdown"
    if suffix in TEXT_EXTENSIONS or _is_probably_text(path):
        return "text"
    return "unknown_binary"


def _looks_like_reasoning_trace(path: Path) -> bool:
    lowered = path.name.lower()
    return any(part in lowered for part in REASONING_NAME_PARTS)


def _candidate_file(path: Path) -> bool:
    lowered = path.name.lower()
    if any(part in lowered for part in SESSION_NAME_PARTS):
        return True
    if path.suffix.lower() in {
        ".db",
        ".json",
        ".jsonl",
        ".log",
        ".md",
        ".sqlite",
        ".sqlite3",
        ".txt",
        ".vscdb",
    }:
        return True
    return path.name == "GEMINI.md"


def _scan_files(root: Path, *, filtered: bool) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if filtered and not _candidate_file(path):
            continue
        yield path


def _source_type_for(path: Path, detected_format: DetectedFormat) -> str:
    return f"antigravity_{detected_format}"


def _source_metadata(path: Path, detected_format: DetectedFormat) -> JsonObject:
    stat = path.stat()
    return {
        "format": detected_format,
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "reasoning_trace_candidate": _looks_like_reasoning_trace(path),
    }


def _read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _read_jsonl(path: Path) -> list[object]:
    rows: list[object] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    rows.append(json.loads(stripped))
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeDecodeError):
        return rows
    return rows


def _extract_from_text_line(line: str, facts: dict[str, list[str]]) -> None:
    stripped = line.strip()
    if not stripped:
        return
    lowered = stripped.lower()
    if lowered.startswith(("task:", "goal:", "objective:", "prompt:")):
        _append_unique(facts["tasks"], stripped.split(":", 1)[1])
    elif lowered.startswith(("repo:", "repository:", "workspace:", "cwd:")):
        _append_unique(facts["workspaces"], stripped.split(":", 1)[1])
    elif lowered.startswith(("command:", "cmd:", "$ ")):
        command = stripped[2:] if lowered.startswith("$ ") else stripped.split(":", 1)[1]
        _append_unique(facts["commands"], command)
    elif lowered.startswith(("file:", "modified:", "created:", "deleted:")):
        _append_unique(facts["files"], stripped)
    elif lowered.startswith(("decision:", "decided:", "resolution:")):
        _append_unique(facts["decisions"], stripped.split(":", 1)[-1])
    elif "error" in lowered or "exception" in lowered or "failed" in lowered:
        _append_unique(facts["errors"], stripped)
    elif lowered.startswith(("outcome:", "result:", "resolved:")):
        _append_unique(facts["outcomes"], stripped.split(":", 1)[-1])


def _extract_from_mapping(mapping: dict[object, object], facts: dict[str, list[str]]) -> None:
    for key, value in mapping.items():
        key_text = str(key).lower()
        if value is None:
            continue
        if any(part in key_text for part in REASONING_NAME_PARTS):
            continue
        if key_text in COMMAND_KEYS:
            _extract_command_values(value, facts["commands"])
        elif key_text in FILE_KEYS:
            _extract_file_values(value, facts["files"])
        elif key_text in TASK_KEYS:
            _extract_values(value, facts["tasks"], limit=180)
        elif key_text in WORKSPACE_KEYS:
            _extract_values(value, facts["workspaces"])
        elif key_text in DECISION_KEYS:
            _extract_values(value, facts["decisions"])
        elif key_text in ERROR_KEYS:
            _extract_values(value, facts["errors"])
        elif key_text in {"outcome", "result", "status"}:
            _extract_values(value, facts["outcomes"])
        elif isinstance(value, dict):
            _extract_from_mapping(value, facts)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _extract_from_mapping(item, facts)


def _extract_values(value: object, target: list[str], *, limit: int = 240) -> None:
    if isinstance(value, str | int | float | bool):
        _append_unique(target, value, limit=limit)
    elif isinstance(value, list):
        for item in value:
            _extract_values(item, target, limit=limit)
    elif isinstance(value, dict):
        for nested in value.values():
            _extract_values(nested, target, limit=limit)


def _extract_command_values(value: object, target: list[str]) -> None:
    if isinstance(value, str):
        _append_unique(target, value)
    elif isinstance(value, list):
        for item in value:
            _extract_command_values(item, target)
    elif isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in COMMAND_KEYS:
                _extract_command_values(nested, target)


def _extract_file_values(value: object, target: list[str]) -> None:
    if isinstance(value, str):
        _append_unique(target, value)
    elif isinstance(value, list):
        for item in value:
            _extract_file_values(item, target)
    elif isinstance(value, dict):
        parts: list[str] = []
        for key, nested in value.items():
            key_text = str(key).lower()
            if key_text not in FILE_DETAIL_KEYS:
                continue
            if isinstance(nested, str | int | float | bool):
                parts.append(f"{key_text}={_short_text(nested, limit=120)}")
        if parts:
            _append_unique(target, ", ".join(parts))


def _empty_facts() -> dict[str, list[str]]:
    return {
        "commands": [],
        "decisions": [],
        "errors": [],
        "files": [],
        "outcomes": [],
        "tasks": [],
        "workspaces": [],
    }


class AntigravityProvider(SessionProvider):
    """Metadata-safe provider for local Antigravity and Gemini session artifacts."""

    provider_id = "antigravity"

    def __init__(
        self,
        *,
        gemini_root: Path | None = None,
        antigravity_config_root: Path | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.gemini_root = gemini_root or Path.home() / ".gemini"
        self.antigravity_config_root = (
            antigravity_config_root or Path.home() / ".config" / "Antigravity"
        )
        self.db_path = db_path or AIOS_DB_PATH

    def discover_sources(self) -> list[SourcePath]:
        sources: list[SourcePath] = []
        seen: set[Path] = set()

        brain_root = self.gemini_root / "antigravity-cli" / "brain"
        plugins_root = self.gemini_root / "antigravity-cli" / "plugins"
        gemini_md = self.gemini_root / "GEMINI.md"

        for directory in self._numeric_brain_dirs(brain_root):
            self._add_source(sources, seen, directory, "antigravity_brain_session_dir", {})

        for path in _scan_files(brain_root, filtered=False):
            self._add_file_source(sources, seen, path)
        for path in _scan_files(plugins_root, filtered=False):
            self._add_file_source(sources, seen, path)
        if gemini_md.exists():
            self._add_file_source(sources, seen, gemini_md)

        for root in self._secondary_roots():
            for path in _scan_files(root, filtered=True):
                self._add_file_source(sources, seen, path)

        return sources

    def scan_since(self, last_cursor: ProviderCursor) -> list[SourcePath]:
        changed: list[SourcePath] = []
        for source in self.discover_sources():
            stat = source.path.stat()
            if (
                str(source.path) == last_cursor.source_path
                and last_cursor.last_mtime is not None
                and stat.st_mtime <= last_cursor.last_mtime
                and stat.st_size == last_cursor.last_size
            ):
                continue
            changed.append(source)
        return changed

    def extract_raw_session(self, source: SourcePath) -> RawSession:
        payload = (
            self._extract_directory(source) if source.path.is_dir() else self._extract_file(source)
        )
        return RawSession(provider=self.provider_id, source=source, payload=payload, raw_text=None)

    def normalize_session(self, raw: RawSession) -> NormalizedSession:
        provider_session_id = self._provider_session_id(raw)
        files = self._payload_files(raw.payload)
        source_files = [
            str(item.get("path")) for item in files if isinstance(item.get("path"), str)
        ]
        if not source_files:
            source_files = [str(raw.source.path)]
        source_file_mtimes = self._source_file_mtimes(files, raw.source.path)
        content_hash = self.compute_fingerprint_from_payload(raw.payload)
        facts = raw.payload.get("facts")
        facts_map = facts if isinstance(facts, dict) else {}
        tasks = self._strings_from(facts_map.get("tasks"))
        workspaces = self._strings_from(facts_map.get("workspaces"))
        commands = self._strings_from(facts_map.get("commands"))
        files_touched = self._strings_from(facts_map.get("files"))
        decisions = self._strings_from(facts_map.get("decisions"))
        errors = self._strings_from(facts_map.get("errors"))
        outcomes = self._strings_from(facts_map.get("outcomes"))
        started_at, updated_at = self._session_bounds(source_file_mtimes)
        title = tasks[0] if tasks else f"Antigravity session {provider_session_id}"

        return NormalizedSession(
            provider=self.provider_id,
            stable_session_id=f"{self.provider_id}:{provider_session_id}",
            provider_session_id=provider_session_id,
            workspace_path=workspaces[0] if workspaces else None,
            workspace_id=None,
            project_id=None,
            started_at=started_at,
            updated_at=updated_at,
            imported_at=_now(),
            source_files=source_files,
            source_file_mtimes=source_file_mtimes,
            content_hash=content_hash,
            title=title,
            participants=[],
            messages=self._metadata_messages(tasks, outcomes),
            tool_calls=[],
            file_edits=[{"path": item} for item in files_touched],
            commands_run=commands,
            decisions_extracted=decisions,
            todos_extracted=[],
            errors_extracted=errors,
            summary_status="pending",
            writeback_status="pending",
            confidence=0.5
            if any((tasks, commands, files_touched, decisions, errors, outcomes))
            else 0.2,
            provider_metadata=self._provider_metadata(raw.payload),
        )

    def compute_fingerprint(self, normalized: NormalizedSession) -> str:
        payload = {
            "commands_run": normalized.commands_run,
            "content_hash": normalized.content_hash,
            "decisions_extracted": normalized.decisions_extracted,
            "errors_extracted": normalized.errors_extracted,
            "provider": normalized.provider,
            "provider_session_id": normalized.provider_session_id,
            "source_files": normalized.source_files,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def compute_fingerprint_from_payload(self, payload: JsonObject) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def upsert_session(self, normalized: NormalizedSession) -> str:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    id, project_id, tool, started_at, ended_at, objective,
                    runtime_metadata_json, status, cwd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    objective = excluded.objective,
                    runtime_metadata_json = excluded.runtime_metadata_json,
                    cwd = excluded.cwd
                """,
                (
                    normalized.stable_session_id,
                    normalized.project_id or "project-aios",
                    "antigravity",
                    normalized.started_at or normalized.imported_at,
                    normalized.updated_at,
                    normalized.title,
                    json.dumps(normalized.provider_metadata, sort_keys=True, default=str),
                    "closed",
                    normalized.workspace_path,
                ),
            )
        return normalized.stable_session_id

    def summarize_session(self, session_id: str) -> SummaryResult:
        return SummaryResult(session_id=session_id, status="pending", summary={}, confidence=0.0)

    def emit_writeback_candidates(self, session_id: str) -> list[WritebackCandidate]:
        return []

    def health_check(self) -> HealthStatus:
        sources = self.discover_sources()
        counts: Counter[str] = Counter()
        warnings: list[str] = []
        errors: list[str] = []
        unknown_paths: list[str] = []
        session_candidates = 0

        for source in sources:
            try:
                if source.path.is_dir():
                    counts["directory"] += 1
                    session_candidates += 1
                    continue
                detected_format = str(
                    source.metadata.get("format") or _detect_file_format(source.path)
                )
                counts[detected_format] += 1
                if detected_format == "unknown_binary":
                    unknown_paths.append(str(source.path))
            except OSError as exc:
                errors.append(f"{source.path}: {exc}")

        for root in (self.gemini_root, self.antigravity_config_root):
            if not root.exists():
                warnings.append(f"Missing source root: {root}")

        for path in unknown_paths:
            warnings.append(f"Unknown binary Antigravity source stored as metadata only: {path}")

        counts["session_candidates"] = session_candidates
        counts["unknown_binary_paths"] = len(unknown_paths)
        return HealthStatus(
            provider_id=self.provider_id,
            ok=not errors,
            source_counts=dict(counts),
            warnings=warnings,
            errors=errors,
        )

    def _secondary_roots(self) -> list[Path]:
        roots = [self.gemini_root, self.antigravity_config_root]
        system = platform.system()
        if system == "Darwin":
            roots.extend(
                [
                    Path.home() / "Library" / "Application Support" / "Antigravity",
                    Path.home() / "Library" / "Logs" / "Antigravity",
                    Path.home() / "Library" / "Caches" / "Antigravity",
                ]
            )
        elif system == "Linux":
            roots.extend(
                [
                    Path.home() / ".local" / "share" / "Antigravity",
                    Path.home() / ".cache" / "Antigravity",
                ]
            )
        return roots

    def _numeric_brain_dirs(self, brain_root: Path) -> list[Path]:
        if not brain_root.exists():
            return []
        return sorted(
            path for path in brain_root.iterdir() if path.is_dir() and path.name.isdigit()
        )

    def _add_file_source(self, sources: list[SourcePath], seen: set[Path], path: Path) -> None:
        try:
            detected_format = _detect_file_format(path)
            metadata = _source_metadata(path, detected_format)
        except OSError:
            return
        self._add_source(sources, seen, path, _source_type_for(path, detected_format), metadata)

    def _add_source(
        self,
        sources: list[SourcePath],
        seen: set[Path],
        path: Path,
        source_type: str,
        metadata: JsonObject,
    ) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        sources.append(SourcePath(path=path, source_type=source_type, metadata=metadata))

    def _extract_directory(self, source: SourcePath) -> JsonObject:
        files: list[JsonObject] = []
        facts = _empty_facts()
        read_errors: list[str] = []
        for path in _scan_files(source.path, filtered=False):
            file_source = SourcePath(
                path=path,
                source_type=source.source_type,
                metadata={"provider_session_id": source.path.name},
            )
            try:
                extracted = self._extract_file(file_source)
            except OSError as exc:
                read_errors.append(f"{path}: {exc}")
                continue
            files.extend(self._payload_files(extracted))
            extracted_facts = extracted.get("facts")
            if isinstance(extracted_facts, dict):
                for key, values in extracted_facts.items():
                    for value in self._strings_from(values):
                        _append_unique(facts.setdefault(str(key), []), value)
        return {
            "provider_session_id": source.path.name,
            "source_kind": "directory",
            "files": files,
            "facts": facts,
            "read_errors": read_errors,
        }

    def _extract_file(self, source: SourcePath) -> JsonObject:
        path = source.path
        detected_format = str(source.metadata.get("format") or _detect_file_format(path))
        pointer = {
            **_safe_stat(path),
            "format": detected_format,
            "extraction_status": "pointer_only"
            if _looks_like_reasoning_trace(path)
            else "metadata_only",
        }
        facts = _empty_facts()
        file_record: JsonObject = dict(pointer)

        if _looks_like_reasoning_trace(path):
            file_record["reasoning_trace_candidate"] = True
            return {"files": [file_record], "facts": facts}

        if detected_format == "json":
            loaded = _read_json(path)
            if isinstance(loaded, dict):
                _extract_from_mapping(loaded, facts)
                file_record["safe_metadata_keys"] = sorted(str(key) for key in loaded)
            elif isinstance(loaded, list):
                for item in loaded:
                    if isinstance(item, dict):
                        _extract_from_mapping(item, facts)
                file_record["safe_metadata_items"] = len(loaded)
            file_record["extraction_status"] = "operational_metadata"
        elif detected_format == "jsonl":
            rows = _read_jsonl(path)
            for row in rows:
                if isinstance(row, dict):
                    _extract_from_mapping(row, facts)
            file_record["safe_metadata_items"] = len(rows)
            file_record["extraction_status"] = "operational_metadata"
        elif detected_format in {"markdown", "text"}:
            self._extract_text_file(path, facts)
            file_record["extraction_status"] = "operational_metadata"
        elif detected_format == "sqlite":
            file_record["sqlite"] = self._sqlite_metadata(path)
            file_record["extraction_status"] = "metadata_only"
        elif detected_format == "unknown_binary":
            file_record["health_warning"] = "unknown_binary_metadata_only"

        return {"files": [file_record], "facts": facts}

    def _extract_text_file(self, path: Path, facts: dict[str, list[str]]) -> None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                for index, line in enumerate(handle):
                    if index >= 1000:
                        break
                    _extract_from_text_line(line, facts)
        except (OSError, UnicodeDecodeError):
            return

    def _sqlite_metadata(self, path: Path) -> JsonObject:
        tables: list[JsonObject] = []
        try:
            uri = f"file:{path}?mode=ro"
            with sqlite3.connect(uri, uri=True) as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
                ).fetchall()
                for (table_name,) in rows:
                    if not isinstance(table_name, str):
                        continue
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM {self._quote_identifier(table_name)}"
                    ).fetchone()
                    tables.append({"name": table_name, "row_count": int(count[0]) if count else 0})
        except sqlite3.DatabaseError as exc:
            return {"read_error": str(exc)}
        return {"tables": tables}

    def _quote_identifier(self, value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    def _provider_session_id(self, raw: RawSession) -> str:
        raw_id = raw.payload.get("provider_session_id") or raw.source.metadata.get(
            "provider_session_id"
        )
        if isinstance(raw_id, str) and raw_id:
            return raw_id
        for parent in [raw.source.path, *raw.source.path.parents]:
            if parent.name.isdigit() and parent.parent.name == "brain":
                return parent.name
        if raw.source.path.is_dir():
            return raw.source.path.name
        return raw.source.path.stem

    def _payload_files(self, payload: JsonObject) -> list[JsonObject]:
        files = payload.get("files")
        if not isinstance(files, list):
            return []
        return [item for item in files if isinstance(item, dict)]

    def _source_file_mtimes(self, files: list[JsonObject], fallback: Path) -> dict[str, float]:
        mtimes: dict[str, float] = {}
        for item in files:
            path = item.get("path")
            mtime = item.get("mtime")
            if isinstance(path, str) and isinstance(mtime, int | float):
                mtimes[path] = float(mtime)
        if not mtimes:
            stat = fallback.stat()
            mtimes[str(fallback)] = stat.st_mtime
        return mtimes

    def _session_bounds(
        self, source_file_mtimes: dict[str, float]
    ) -> tuple[str | None, str | None]:
        if not source_file_mtimes:
            return None, None
        mtimes = list(source_file_mtimes.values())
        return _iso_from_mtime(min(mtimes)), _iso_from_mtime(max(mtimes))

    def _metadata_messages(self, tasks: list[str], outcomes: list[str]) -> list[JsonObject]:
        messages: list[JsonObject] = []
        if tasks:
            messages.append({"role": "user", "phase": "operational_metadata", "text": tasks[0]})
        if outcomes:
            messages.append(
                {"role": "assistant", "phase": "operational_metadata", "text": outcomes[0]}
            )
        return messages

    def _provider_metadata(self, payload: JsonObject) -> JsonObject:
        files = self._payload_files(payload)
        return {
            "source_kind": payload.get("source_kind") or "file",
            "files": files,
            "read_errors": payload.get("read_errors") or [],
            "privacy": {
                "raw_content_stored": False,
                "reasoning_traces": "pointer_only",
                "unknown_binary": "metadata_only",
            },
        }

    def _strings_from(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]
