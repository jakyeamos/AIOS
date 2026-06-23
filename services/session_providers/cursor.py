from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sqlite3
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

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

CURSOR_KEY_TERMS = ("chat", "composer", "aichat", "agent", "conversation")
KNOWN_CURSOR_KEYS = ("aiService.prompts",)
MESSAGE_KEYS = ("messages", "conversation", "turns", "entries", "prompts", "responses")
TOOL_KEYS = ("toolCalls", "tool_calls", "tools", "functionCalls")
EDIT_KEYS = ("fileEdits", "file_edits", "edits", "patches", "diffs")


@dataclass(frozen=True)
class _CursorSessionCandidate:
    provider_session_id: str
    title: str
    workspace_id: str | None
    workspace_path: str | None
    started_at: str | None
    updated_at: str | None
    messages: list[JsonObject]
    tool_calls: list[JsonObject]
    file_edits: list[JsonObject]
    commands_run: list[str]
    provider_metadata: JsonObject


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json_hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _source_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _safe_json(value: object) -> object | None:
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    if isinstance(value, dict | list):
        return value
    return None


def _as_object(value: object) -> JsonObject | None:
    return value if isinstance(value, dict) else None


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_string(payload: JsonObject, keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        try:
            return datetime.fromtimestamp(seconds, UTC).isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    text = str(value).strip()
    return text or None


def _role_from_message(message: JsonObject) -> str:
    for key in ("role", "author", "speaker", "participant", "type"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            lowered = value.strip().lower()
            if lowered in {"human", "user"}:
                return "user"
            if lowered in {"assistant", "ai", "agent", "bot"}:
                return "assistant"
            if lowered in {"system", "tool"}:
                return lowered
            return value.strip()
    return ""


def _text_from_message(message: JsonObject) -> str:
    for key in ("text", "content", "message", "body", "value", "prompt", "response"):
        value = message.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = [
                str(item.get("text") or item.get("content"))
                for item in value
                if isinstance(item, dict) and (item.get("text") or item.get("content"))
            ]
            if parts:
                return "\n".join(parts)
    return ""


def _timestamp_from_message(message: JsonObject) -> str | None:
    for key in ("timestamp", "time", "createdAt", "created_at", "date", "ts"):
        normalized = _normalize_timestamp(message.get(key))
        if normalized:
            return normalized
    return None


def _message_from_object(value: JsonObject) -> JsonObject | None:
    text = _text_from_message(value)
    role = _role_from_message(value)
    if not text and not role:
        return None
    return {
        "role": role,
        "text": text,
        "time": _timestamp_from_message(value),
    }


def _walk_objects(value: object) -> Iterable[JsonObject]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_objects(nested)


def _collect_messages(value: object) -> list[JsonObject]:
    messages: list[JsonObject] = []
    seen: set[str] = set()
    for item in _walk_objects(value):
        direct = _message_from_object(item)
        if direct is not None:
            key = _json_hash(direct)
            if key not in seen:
                seen.add(key)
                messages.append(direct)
            continue
        for message_key in MESSAGE_KEYS:
            for nested in _as_list(item.get(message_key)):
                nested_object = _as_object(nested)
                if nested_object is None:
                    continue
                parsed = _message_from_object(nested_object)
                if parsed is None:
                    continue
                key = _json_hash(parsed)
                if key not in seen:
                    seen.add(key)
                    messages.append(parsed)
    return messages


def _collect_named_objects(value: object, keys: Iterable[str]) -> list[JsonObject]:
    collected: list[JsonObject] = []
    seen: set[str] = set()
    for item in _walk_objects(value):
        for key in keys:
            nested = item.get(key)
            candidates = nested if isinstance(nested, list) else [nested]
            for candidate in candidates:
                candidate_object = _as_object(candidate)
                if candidate_object is None:
                    continue
                marker = _json_hash(candidate_object)
                if marker in seen:
                    continue
                seen.add(marker)
                collected.append(candidate_object)
    return collected


def _collect_commands(value: object) -> list[str]:
    commands: list[str] = []
    seen: set[str] = set()
    for item in _walk_objects(value):
        for key in ("command", "commandLine", "shellCommand", "terminalCommand"):
            command = item.get(key)
            if isinstance(command, str) and command.strip() and command not in seen:
                seen.add(command)
                commands.append(command)
    return commands


def _resolve_file_uri(value: str) -> str:
    if value.startswith("file://"):
        parsed = urlparse(value)
        return unquote(parsed.path)
    return value


class CursorProvider(SessionProvider):
    """Session provider for local Cursor workspace databases and agent transcripts."""

    provider_id = "cursor"

    def __init__(
        self,
        *,
        home: Path | None = None,
        db_path: Path | None = None,
        snapshot_root: Path | None = None,
    ) -> None:
        self.home = home or Path.home()
        self.db_path = db_path or self.home / "AIOS" / "data" / "aios.db"
        self.snapshot_root = snapshot_root or self.home / "AIOS" / "staging" / "cursor-snapshots"
        self._read_errors: list[str] = []

    def discover_sources(self) -> list[SourcePath]:
        sources: list[SourcePath] = []
        workspace_roots, global_db, transcript_roots = self._cursor_paths()

        for workspace_root in workspace_roots:
            if not workspace_root.exists():
                continue
            for db_file in sorted(workspace_root.glob("**/state.vscdb")):
                workspace_id = db_file.parent.name
                workspace_path, orphaned = self._resolve_workspace(db_file)
                sources.append(
                    SourcePath(
                        path=db_file,
                        source_type="cursor_workspace_vscdb",
                        metadata={
                            "workspace_id": workspace_id,
                            "workspace_path": workspace_path,
                            "workspace_orphaned": orphaned,
                        },
                    )
                )

        if global_db.exists():
            sources.append(SourcePath(path=global_db, source_type="cursor_global_vscdb"))

        for transcript_root in transcript_roots:
            if not transcript_root.exists():
                continue
            for transcript in sorted(transcript_root.glob("**/agent-transcripts/*.jsonl")):
                sources.append(
                    SourcePath(
                        path=transcript,
                        source_type="cursor_agent_transcript_jsonl",
                        metadata=self._transcript_metadata(transcript, transcript_root),
                    )
                )

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
        sessions = self.extract_raw_sessions(source)
        if not sessions:
            return RawSession(provider=self.provider_id, source=source, payload={})
        if len(sessions) == 1:
            return sessions[0]
        return RawSession(
            provider=self.provider_id,
            source=source,
            payload={
                "session_id": f"{source.source_type}:{_json_hash(str(source.path))[:12]}",
                "title": source.path.name,
                "sessions": [session.payload for session in sessions],
                "source_type": source.source_type,
            },
        )

    def extract_raw_sessions(self, source: SourcePath) -> list[RawSession]:
        if source.source_type.endswith("_vscdb"):
            return self._extract_sqlite_sessions(source)
        if source.source_type == "cursor_agent_transcript_jsonl":
            candidate = self._candidate_from_jsonl(source)
            return self._raw_sessions_from_candidates(source, [candidate] if candidate else [])
        return []

    def normalize_session(self, raw: RawSession) -> NormalizedSession:
        sessions = raw.payload.get("sessions")
        if isinstance(sessions, list):
            normalized = [
                self.normalize_session(
                    RawSession(provider=self.provider_id, source=raw.source, payload=session)
                )
                for session in sessions
                if isinstance(session, dict)
            ]
            if normalized:
                return self._merge_normalized(normalized)

        payload = raw.payload
        session_id = str(payload.get("session_id") or raw.source.path.stem)
        source_path = str(raw.source.path)
        source_mtime = _source_mtime(raw.source.path)
        messages = [
            message for message in _as_list(payload.get("messages")) if isinstance(message, dict)
        ]
        tool_calls = [
            call for call in _as_list(payload.get("tool_calls")) if isinstance(call, dict)
        ]
        file_edits = [
            edit for edit in _as_list(payload.get("file_edits")) if isinstance(edit, dict)
        ]
        commands_run = [str(command) for command in _as_list(payload.get("commands_run"))]
        provider_metadata = _as_object(payload.get("provider_metadata")) or {}
        workspace_path = _string_or_none(payload.get("workspace_path"))
        workspace_id = _string_or_none(payload.get("workspace_id"))

        return NormalizedSession(
            provider=self.provider_id,
            stable_session_id=f"{self.provider_id}:{session_id}",
            provider_session_id=session_id,
            workspace_path=workspace_path,
            workspace_id=workspace_id,
            project_id=None,
            started_at=_string_or_none(payload.get("started_at")),
            updated_at=_string_or_none(payload.get("updated_at")),
            imported_at=_now(),
            source_files=[source_path],
            source_file_mtimes={source_path: source_mtime},
            content_hash=self.compute_fingerprint_from_payload(payload),
            title=str(payload.get("title") or session_id),
            participants=self._participants(messages),
            messages=messages,
            tool_calls=tool_calls,
            file_edits=file_edits,
            commands_run=commands_run,
            decisions_extracted=[],
            todos_extracted=[],
            errors_extracted=[],
            summary_status="pending",
            writeback_status="pending",
            confidence=0.7 if messages else 0.3,
            provider_metadata=provider_metadata,
        )

    def normalize_sessions(self, raws: Iterable[RawSession]) -> list[NormalizedSession]:
        normalized = [self.normalize_session(raw) for raw in raws if raw.payload]
        return self._deduplicate_sessions(normalized)

    def compute_fingerprint(self, normalized: NormalizedSession) -> str:
        payload = {
            "provider": normalized.provider,
            "provider_session_id": normalized.provider_session_id,
            "workspace_id": normalized.workspace_id,
            "workspace_path": normalized.workspace_path,
            "messages": normalized.messages,
            "tool_calls": normalized.tool_calls,
            "file_edits": normalized.file_edits,
        }
        return _json_hash(payload)

    def compute_fingerprint_from_payload(self, payload: JsonObject) -> str:
        return _json_hash(payload)

    def upsert_session(self, normalized: NormalizedSession) -> str:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    id, project_id, tool, started_at, ended_at, objective, status, cwd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    objective = excluded.objective,
                    cwd = excluded.cwd
                """,
                (
                    normalized.stable_session_id,
                    normalized.project_id or "project-aios",
                    "cursor",
                    normalized.started_at or normalized.imported_at,
                    normalized.updated_at,
                    normalized.title,
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
        self._read_errors = []
        sources = self.discover_sources()
        source_counts: dict[str, int] = {
            "cursor_workspace_vscdb": 0,
            "cursor_global_vscdb": 0,
            "cursor_agent_transcript_jsonl": 0,
        }
        session_counts: dict[str, int] = {}
        for source in sources:
            source_counts[source.source_type] = source_counts.get(source.source_type, 0) + 1
            try:
                session_counts[str(source.path)] = len(self.extract_raw_sessions(source))
            except (OSError, sqlite3.Error, UnicodeDecodeError) as error:
                self._read_errors.append(f"{source.path}: {error}")
                session_counts[str(source.path)] = 0

        warnings = self._platform_warnings()
        if self._read_errors:
            warnings.extend(
                f"Unreadable Cursor source skipped: {error}" for error in self._read_errors
            )
        readable_sources = len(sources) - len(self._read_errors)
        missing_roots = self._missing_source_roots()
        warnings.extend(f"Missing source root: {root}" for root in missing_roots)
        if session_counts:
            source_counts["sources_with_sessions"] = sum(
                1 for count in session_counts.values() if count > 0
            )
            source_counts["sessions_total"] = sum(session_counts.values())
            for source_path, count in session_counts.items():
                source_counts[f"sessions:{source_path}"] = count
        return HealthStatus(
            provider_id=self.provider_id,
            ok=readable_sources > 0 or not sources,
            source_counts=source_counts,
            warnings=warnings,
            errors=[] if readable_sources > 0 else self._read_errors.copy(),
        )

    def _cursor_paths(self) -> tuple[list[Path], Path, list[Path]]:
        system = platform.system()
        if system == "Darwin":
            user_root = self.home / "Library" / "Application Support" / "Cursor" / "User"
        elif system == "Linux":
            user_root = self.home / ".config" / "Cursor" / "User"
        else:
            user_root = self.home / "AppData" / "Roaming" / "Cursor" / "User"
        return (
            [user_root / "workspaceStorage"],
            user_root / "globalStorage" / "state.vscdb",
            [self.home / ".cursor" / "projects"],
        )

    def _platform_warnings(self) -> list[str]:
        system = platform.system()
        if system == "Darwin":
            return []
        if system == "Linux":
            return ["Using Linux Cursor paths; macOS paths are the primary supported target."]
        return [f"Cursor source discovery for {system} is best-effort."]

    def _missing_source_roots(self) -> list[Path]:
        workspace_roots, global_db, transcript_roots = self._cursor_paths()
        roots: list[Path] = [
            root for root in workspace_roots + transcript_roots if not root.exists()
        ]
        if not global_db.exists():
            roots.append(global_db)
        return roots

    def _resolve_workspace(self, db_file: Path) -> tuple[str | None, bool]:
        workspace_file = db_file.parent / "workspace.json"
        if not workspace_file.exists():
            return None, True
        try:
            workspace_data = json.loads(workspace_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, True

        path_value = None
        if isinstance(workspace_data, dict):
            folder = workspace_data.get("folder")
            if isinstance(folder, str):
                path_value = folder
            workspace = workspace_data.get("workspace")
            if path_value is None and isinstance(workspace, str):
                path_value = workspace
            if path_value is None and isinstance(workspace, dict):
                config_path = workspace.get("configPath")
                if isinstance(config_path, str):
                    path_value = config_path

        if path_value is None:
            return None, True
        resolved = _resolve_file_uri(path_value)
        if not Path(resolved).exists():
            return None, True
        return resolved, False

    def _transcript_metadata(self, transcript: Path, transcript_root: Path) -> JsonObject:
        try:
            relative = transcript.relative_to(transcript_root)
            project_id = relative.parts[0] if relative.parts else transcript.parent.parent.name
        except ValueError:
            project_id = transcript.parent.parent.name
        return {
            "project_id": project_id,
            "workspace_id": project_id,
            "workspace_path": None,
        }

    def _extract_sqlite_sessions(self, source: SourcePath) -> list[RawSession]:
        rows = self._read_item_table(source.path)
        candidates: list[_CursorSessionCandidate] = []
        for key, value in rows:
            if not self._is_candidate_key(key):
                continue
            parsed = _safe_json(value)
            if parsed is None:
                continue
            candidates.extend(self._candidates_from_item_value(source, key, parsed))
        return self._raw_sessions_from_candidates(source, candidates)

    def _read_item_table(self, db_file: Path) -> list[tuple[str, object]]:
        try:
            return self._read_item_table_direct(db_file)
        except sqlite3.OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            return self._read_item_table_snapshot(db_file)

    def _read_item_table_direct(self, db_file: Path) -> list[tuple[str, object]]:
        uri = f"file:{db_file}?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            conn.execute("PRAGMA query_only = ON")
            return list(conn.execute("SELECT key, value FROM ItemTable"))

    def _read_item_table_snapshot(self, db_file: Path) -> list[tuple[str, object]]:
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshot_root / f"{db_file.stem}-{_json_hash(str(db_file))[:12]}.vscdb"
        try:
            shutil.copy2(db_file, snapshot)
            return self._read_item_table_direct(snapshot)
        finally:
            with suppress(FileNotFoundError):
                snapshot.unlink()

    def _is_candidate_key(self, key: str) -> bool:
        lowered = key.lower()
        return any(term in lowered for term in CURSOR_KEY_TERMS) or key in KNOWN_CURSOR_KEYS

    def _candidates_from_item_value(
        self, source: SourcePath, item_key: str, value: object
    ) -> list[_CursorSessionCandidate]:
        candidate_values = self._session_like_values(value)
        if not candidate_values:
            candidate_values = [value]

        candidates: list[_CursorSessionCandidate] = []
        for index, candidate_value in enumerate(candidate_values):
            candidate_object = _as_object(candidate_value)
            if candidate_object is None:
                candidate_object = {"value": candidate_value}
            messages = _collect_messages(candidate_object)
            if not messages:
                continue
            session_id = self._session_id(candidate_object, f"{source.path}:{item_key}:{index}")
            title = (
                _first_string(candidate_object, ("title", "name", "label", "summary")) or session_id
            )
            started_at, updated_at = self._session_times(candidate_object, messages)
            provider_metadata: JsonObject = {
                "source_type": source.source_type,
                "item_key": item_key,
                "workspace_orphaned": source.metadata.get("workspace_orphaned", False),
            }
            candidates.append(
                _CursorSessionCandidate(
                    provider_session_id=session_id,
                    title=title,
                    workspace_id=_string_or_none(source.metadata.get("workspace_id")),
                    workspace_path=_string_or_none(source.metadata.get("workspace_path")),
                    started_at=started_at,
                    updated_at=updated_at,
                    messages=messages,
                    tool_calls=_collect_named_objects(candidate_object, TOOL_KEYS),
                    file_edits=_collect_named_objects(candidate_object, EDIT_KEYS),
                    commands_run=_collect_commands(candidate_object),
                    provider_metadata=provider_metadata,
                )
            )
        return candidates

    def _session_like_values(self, value: object) -> list[object]:
        values: list[object] = []
        for item in _walk_objects(value):
            for key in ("sessions", "chats", "conversations", "composers", "threads"):
                nested = item.get(key)
                if isinstance(nested, list):
                    values.extend(nested)
                elif isinstance(nested, dict):
                    values.extend(nested.values())
        return values

    def _candidate_from_jsonl(self, source: SourcePath) -> _CursorSessionCandidate | None:
        events: list[JsonObject] = []
        with source.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                parsed = _safe_json(line.strip())
                if isinstance(parsed, dict):
                    events.append(parsed)
        if not events:
            return None

        first_event = events[0]
        last_event = events[-1]
        messages = _collect_messages(events)
        session_id = (
            self._session_id(first_event, str(source.path))
            or self._session_id(last_event, str(source.path))
            or source.path.stem
        )
        workspace_id = _first_string(first_event, ("workspaceId", "workspace_id", "projectId"))
        workspace_path = _first_string(first_event, ("workspacePath", "workspace_path", "cwd"))
        workspace_id = workspace_id or _string_or_none(source.metadata.get("workspace_id"))
        workspace_path = workspace_path or _string_or_none(source.metadata.get("workspace_path"))
        started_at, updated_at = self._event_times(events, messages)
        return _CursorSessionCandidate(
            provider_session_id=session_id,
            title=_first_string(first_event, ("title", "summary", "name")) or source.path.stem,
            workspace_id=workspace_id,
            workspace_path=workspace_path,
            started_at=started_at,
            updated_at=updated_at,
            messages=messages,
            tool_calls=_collect_named_objects(events, TOOL_KEYS),
            file_edits=_collect_named_objects(events, EDIT_KEYS),
            commands_run=_collect_commands(events),
            provider_metadata={
                "source_type": source.source_type,
                "event_count": len(events),
                "project_id": source.metadata.get("project_id"),
            },
        )

    def _raw_sessions_from_candidates(
        self, source: SourcePath, candidates: Iterable[_CursorSessionCandidate]
    ) -> list[RawSession]:
        return [
            RawSession(
                provider=self.provider_id,
                source=source,
                payload={
                    "session_id": candidate.provider_session_id,
                    "title": candidate.title,
                    "workspace_id": candidate.workspace_id,
                    "workspace_path": candidate.workspace_path,
                    "started_at": candidate.started_at,
                    "updated_at": candidate.updated_at,
                    "messages": candidate.messages,
                    "tool_calls": candidate.tool_calls,
                    "file_edits": candidate.file_edits,
                    "commands_run": candidate.commands_run,
                    "provider_metadata": candidate.provider_metadata,
                },
            )
            for candidate in candidates
        ]

    def _session_id(self, payload: JsonObject, fallback: str) -> str:
        value = _first_string(
            payload,
            (
                "sessionId",
                "session_id",
                "conversationId",
                "conversation_id",
                "chatId",
                "chat_id",
                "composerId",
                "id",
            ),
        )
        return value or _json_hash(fallback)[:16]

    def _session_times(
        self, payload: JsonObject, messages: list[JsonObject]
    ) -> tuple[str | None, str | None]:
        started_at = None
        updated_at = None
        for key in ("createdAt", "created_at", "startedAt", "startTime", "timestamp"):
            started_at = _normalize_timestamp(payload.get(key))
            if started_at:
                break
        for key in ("updatedAt", "updated_at", "endedAt", "lastUpdatedAt", "timestamp"):
            updated_at = _normalize_timestamp(payload.get(key))
            if updated_at:
                break
        message_times = [
            str(message.get("time"))
            for message in messages
            if isinstance(message.get("time"), str) and message.get("time")
        ]
        return started_at or (message_times[0] if message_times else None), updated_at or (
            message_times[-1] if message_times else None
        )

    def _event_times(
        self, events: list[JsonObject], messages: list[JsonObject]
    ) -> tuple[str | None, str | None]:
        event_times = [
            timestamp
            for event in events
            for timestamp in (
                _normalize_timestamp(event.get("timestamp")),
                _normalize_timestamp(event.get("time")),
                _normalize_timestamp(event.get("createdAt")),
            )
            if timestamp
        ]
        message_times = [
            str(message.get("time"))
            for message in messages
            if isinstance(message.get("time"), str) and message.get("time")
        ]
        all_times = event_times + message_times
        return (all_times[0], all_times[-1]) if all_times else (None, None)

    def _participants(self, messages: list[JsonObject]) -> list[str]:
        participants = sorted(
            {
                str(message.get("role"))
                for message in messages
                if isinstance(message.get("role"), str) and message.get("role")
            }
        )
        return participants or ["user", "assistant"]

    def _deduplicate_sessions(
        self, sessions: Iterable[NormalizedSession]
    ) -> list[NormalizedSession]:
        merged: dict[str, NormalizedSession] = {}
        for session in sessions:
            key = self._dedup_key(session)
            existing = merged.get(key)
            merged[key] = (
                session if existing is None else self._merge_normalized([existing, session])
            )
        return list(merged.values())

    def _dedup_key(self, session: NormalizedSession) -> str:
        if session.provider_session_id:
            return session.provider_session_id
        if session.started_at and session.workspace_id:
            return f"{session.started_at}:{session.workspace_id}"
        return f"{session.started_at}:{session.workspace_path}:{session.title}"

    def _merge_normalized(self, sessions: list[NormalizedSession]) -> NormalizedSession:
        base = max(sessions, key=lambda session: (len(session.messages), len(session.source_files)))
        source_files: list[str] = []
        source_mtimes: dict[str, float] = {}
        messages: list[JsonObject] = []
        tool_calls: list[JsonObject] = []
        file_edits: list[JsonObject] = []
        commands: list[str] = []
        metadata: JsonObject = {}

        for session in sessions:
            source_files.extend(path for path in session.source_files if path not in source_files)
            source_mtimes.update(session.source_file_mtimes)
            messages = self._merge_json_objects(messages, session.messages)
            tool_calls = self._merge_json_objects(tool_calls, session.tool_calls)
            file_edits = self._merge_json_objects(file_edits, session.file_edits)
            commands.extend(command for command in session.commands_run if command not in commands)
            metadata.update(session.provider_metadata)

        payload = {
            "provider_session_id": base.provider_session_id,
            "messages": messages,
            "tool_calls": tool_calls,
            "file_edits": file_edits,
            "commands_run": commands,
            "source_files": source_files,
        }
        return NormalizedSession(
            provider=base.provider,
            stable_session_id=base.stable_session_id,
            provider_session_id=base.provider_session_id,
            workspace_path=base.workspace_path
            or next(
                (session.workspace_path for session in sessions if session.workspace_path),
                None,
            ),
            workspace_id=base.workspace_id
            or next(
                (session.workspace_id for session in sessions if session.workspace_id),
                None,
            ),
            project_id=base.project_id,
            started_at=base.started_at
            or next(
                (session.started_at for session in sessions if session.started_at),
                None,
            ),
            updated_at=base.updated_at
            or next(
                (session.updated_at for session in reversed(sessions) if session.updated_at),
                None,
            ),
            imported_at=base.imported_at,
            source_files=source_files,
            source_file_mtimes=source_mtimes,
            content_hash=_json_hash(payload),
            title=base.title,
            participants=self._participants(messages),
            messages=messages,
            tool_calls=tool_calls,
            file_edits=file_edits,
            commands_run=commands,
            decisions_extracted=[],
            todos_extracted=[],
            errors_extracted=[],
            summary_status=base.summary_status,
            writeback_status=base.writeback_status,
            confidence=max(session.confidence for session in sessions),
            provider_metadata=metadata,
        )

    def _merge_json_objects(
        self, left: list[JsonObject], right: list[JsonObject]
    ) -> list[JsonObject]:
        merged = list(left)
        seen = {_json_hash(item) for item in merged}
        for item in right:
            marker = _json_hash(item)
            if marker in seen:
                continue
            seen.add(marker)
            merged.append(item)
        return merged
