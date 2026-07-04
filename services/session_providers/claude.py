from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from services.session_providers.base import (
    HealthStatus,
    NormalizedSession,
    ProviderCursor,
    RawSession,
    SessionProvider,
    SourcePath,
    SummaryResult,
    WritebackCandidate,
)

AIOS_ROOT = Path(__file__).resolve().parents[2]
IMPORT_AI_HISTORY_PATH = AIOS_ROOT / "bin" / "import_ai_history.py"


def _load_import_ai_history() -> ModuleType:
    spec = importlib.util.spec_from_file_location("aios_import_ai_history", IMPORT_AI_HISTORY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {IMPORT_AI_HISTORY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_claude_jsonl_events(path: Path) -> list[dict[str, Any]]:
    events = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def _minimal_session_from_events(
    path: Path, project_dir_name: str, events: list[dict[str, Any]]
) -> dict[str, object]:
    first_timestamp = next(
        (str(event.get("timestamp")) for event in events if event.get("timestamp")), ""
    )
    cwd = next((str(event.get("cwd")) for event in events if event.get("cwd")), "")
    model = "claude-code"
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        maybe_model = message.get("model")
        if isinstance(maybe_model, str) and maybe_model.strip():
            model = maybe_model.strip()
            break
    return {
        "session_id": path.stem,
        "created_at": first_timestamp,
        "cwd": cwd,
        "model": model,
        "project_dir": project_dir_name,
        "messages": [],
    }


def _extract_claude_tool_signals(
    events: list[object],
) -> tuple[list[dict[str, object]], list[str], list[str]]:
    tool_calls: list[dict[str, object]] = []
    commands_run: list[str] = []
    errors_extracted: list[str] = []
    seen_commands: set[str] = set()
    for event in events:
        if not isinstance(event, dict) or event.get("isMeta"):
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        blocks = content if isinstance(content, list) else []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "tool_use":
                tool_call = _claude_tool_call(block)
                if tool_call:
                    tool_calls.append(tool_call)
                    command = str(tool_call.get("command") or "")
                    if command and command not in seen_commands:
                        seen_commands.add(command)
                        commands_run.append(command)
            elif block_type == "tool_result":
                error = _claude_tool_result_error(block)
                if error:
                    errors_extracted.append(error)
    return tool_calls, commands_run, errors_extracted


def _claude_tool_call(block: dict[str, object]) -> dict[str, object] | None:
    tool_name = str(block.get("name") or "")
    tool_input = block.get("input")
    input_dict = tool_input if isinstance(tool_input, dict) else {}
    command = input_dict.get("command")
    description = input_dict.get("description")
    call_id = block.get("id")
    if not tool_name and not command:
        return None
    return {
        "tool": tool_name,
        "id": str(call_id or ""),
        "command": str(command or ""),
        "description": str(description or ""),
    }


def _claude_tool_result_error(block: dict[str, object]) -> str | None:
    text = _claude_tool_result_text(block.get("content"))
    if not text:
        return None
    lowered = text.lower()
    is_error = bool(block.get("is_error")) or any(
        marker in lowered
        for marker in (
            "process exited with code 1",
            "exit code 1",
            "error:",
            "failed",
            "exception",
            "traceback",
        )
    )
    if not is_error:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    if lines[0].lower().startswith("process exited with code") and len(lines) > 1:
        return f"{lines[0]}: {' '.join(lines[1:])}"[:500]
    return " ".join(lines)[:500]


def _claude_tool_result_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(str(item["text"]).strip())
        return "\n".join(part for part in parts if part)
    return ""


class ClaudeProvider(SessionProvider):
    """Adapter over the existing Claude Code JSONL import logic."""

    provider_id = "claude"

    def __init__(
        self,
        *,
        source_root: Path | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.source_root = source_root or Path.home() / ".claude" / "projects"
        self.db_path = db_path or Path.home() / "AIOS" / "data" / "aios.db"
        self._import_ai_history = _load_import_ai_history()

    def discover_sources(self) -> list[SourcePath]:
        if not self.source_root.exists():
            return []
        return [
            SourcePath(path=path, source_type="claude_code_jsonl")
            for path in sorted(self.source_root.glob("**/*.jsonl"))
            if "--claude-mem" not in str(path)
        ]

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
        project_dir_name = source.path.parent.name
        events = _read_claude_jsonl_events(source.path)
        session = self._import_ai_history.load_claude_code_session(source.path, project_dir_name)
        if session is None:
            session = _minimal_session_from_events(source.path, project_dir_name, events)
        session["_events"] = events
        return RawSession(provider=self.provider_id, source=source, payload=session)

    def normalize_session(self, raw: RawSession) -> NormalizedSession:
        session_id = str(raw.payload.get("session_id") or raw.source.path.stem)
        raw_messages = raw.payload.get("messages")
        messages: list[dict[str, object]] = []
        if isinstance(raw_messages, list):
            for message in raw_messages:
                if not isinstance(message, dict):
                    continue
                messages.append(
                    {
                        "role": str(message.get("role") or ""),
                        "text": str(message.get("text") or ""),
                        "time": message.get("time") or 0,
                    }
                )
        events = raw.payload.get("_events")
        event_list = events if isinstance(events, list) else []
        tool_calls, commands_run, errors_extracted = _extract_claude_tool_signals(event_list)
        content_hash = self.compute_fingerprint_from_payload(raw.payload)
        source_path = str(raw.source.path)
        stat = raw.source.path.stat()
        return NormalizedSession(
            provider=self.provider_id,
            stable_session_id=f"{self.provider_id}:{session_id}",
            provider_session_id=session_id,
            workspace_path=str(raw.payload.get("cwd") or "") or None,
            workspace_id=str(raw.payload.get("project_dir") or "") or None,
            project_id=None,
            started_at=str(raw.payload.get("created_at") or "") or None,
            updated_at=str(raw.payload.get("created_at") or "") or None,
            imported_at=_now(),
            source_files=[source_path],
            source_file_mtimes={source_path: stat.st_mtime},
            content_hash=content_hash,
            title=session_id,
            participants=["user", "assistant"],
            messages=messages,
            tool_calls=tool_calls,
            file_edits=[],
            commands_run=commands_run,
            decisions_extracted=[],
            todos_extracted=[],
            errors_extracted=errors_extracted,
            summary_status="pending",
            writeback_status="pending",
            confidence=0.6 if messages else 0.0,
            provider_metadata={
                "model": raw.payload.get("model"),
                "tool_call_count": len(tool_calls),
            },
        )

    def compute_fingerprint(self, normalized: NormalizedSession) -> str:
        payload = {
            "provider": normalized.provider,
            "provider_session_id": normalized.provider_session_id,
            "messages": normalized.messages,
            "source_files": normalized.source_files,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def compute_fingerprint_from_payload(self, payload: dict[str, object]) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

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
                    objective = excluded.objective,
                    cwd = excluded.cwd
                """,
                (
                    normalized.stable_session_id,
                    normalized.project_id or "project-aios",
                    "claude-code",
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
        sources = self.discover_sources()
        warnings = [] if self.source_root.exists() else [f"Missing source root: {self.source_root}"]
        return HealthStatus(
            provider_id=self.provider_id,
            ok=self.source_root.exists(),
            source_counts={"claude_code_jsonl": len(sources)},
            warnings=warnings,
        )
