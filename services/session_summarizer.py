from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any, cast

from services.session_providers.base import NormalizedSession, SessionStatus
from services.session_redaction import redact_session


@dataclass(frozen=True)
class SessionSummary:
    what_i_was_trying_to_do: str
    project_repo_involved: str
    important_context_used: list[str]
    decisions_made: list[str]
    files_modules_touched: list[str]
    commands_tools_used: list[str]
    bugs_failures_encountered: list[str]
    successful_fixes: list[str]
    unresolved_follow_ups: list[str]
    reusable_patterns: list[str]
    candidate_skills_to_extract: list[str]
    should_create_obsidian_note: bool
    confidence: float
    source_provenance: dict[str, Any]
    writeback_proposal_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_session(session_id: str, conn: sqlite3.Connection) -> SessionSummary:
    """Load a normalized session, redact it, and derive structured summary fields."""

    normalized = load_normalized_session(conn, session_id)
    redacted = redact_session(normalized)
    if redacted.redaction_incomplete:
        return SessionSummary(
            what_i_was_trying_to_do=_primary_goal(redacted),
            project_repo_involved=_project_repo(redacted),
            important_context_used=[],
            decisions_made=[],
            files_modules_touched=[],
            commands_tools_used=[],
            bugs_failures_encountered=[],
            successful_fixes=[],
            unresolved_follow_ups=["Session held because redaction is incomplete."],
            reusable_patterns=[],
            candidate_skills_to_extract=[],
            should_create_obsidian_note=False,
            confidence=min(redacted.confidence, 0.2),
            source_provenance=_source_provenance(redacted),
            writeback_proposal_status="held_redaction_incomplete",
        )

    commands = _dedupe(redacted.commands_run + _extract_values(redacted.tool_calls, "command"))
    files = _extract_files(redacted)
    decisions = _dedupe(redacted.decisions_extracted + _extract_decisions(redacted.messages))
    errors = _dedupe(redacted.errors_extracted + _extract_errors(redacted.messages))
    follow_ups = _dedupe(redacted.todos_extracted + _extract_follow_ups(redacted.messages))
    fixes = _extract_successes(redacted.messages)
    patterns = _derive_reusable_patterns(commands, decisions)
    confidence = _confidence(redacted, commands, files, decisions, errors)

    should_note = confidence >= 0.6 and bool(_primary_goal(redacted))

    return SessionSummary(
        what_i_was_trying_to_do=_primary_goal(redacted),
        project_repo_involved=_project_repo(redacted),
        important_context_used=_extract_context_refs(redacted.messages),
        decisions_made=decisions,
        files_modules_touched=files,
        commands_tools_used=commands,
        bugs_failures_encountered=errors,
        successful_fixes=fixes,
        unresolved_follow_ups=follow_ups,
        reusable_patterns=patterns,
        candidate_skills_to_extract=_skill_candidates(patterns),
        should_create_obsidian_note=should_note,
        confidence=confidence,
        source_provenance=_source_provenance(redacted),
        writeback_proposal_status="pending",
    )


def load_normalized_session(conn: sqlite3.Connection, session_id: str) -> NormalizedSession:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM session_imports WHERE stable_session_id = ?",
        (session_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown session import: {session_id}")
    return NormalizedSession(
        provider=str(row["provider_id"]),
        stable_session_id=str(row["stable_session_id"]),
        provider_session_id=str(row["provider_session_id"]),
        workspace_path=row["workspace_path"],
        workspace_id=row["workspace_id"],
        project_id=row["project_id"],
        started_at=row["started_at"],
        updated_at=row["updated_at"],
        imported_at=str(row["imported_at"]),
        source_files=_json_list(row["source_files_json"]),
        source_file_mtimes=_json_dict_float(row["source_file_mtimes_json"]),
        content_hash=str(row["content_hash"]),
        title=str(row["title"]),
        participants=_json_list(row["participants_json"]),
        messages=_json_object_list(row["messages_json"]),
        tool_calls=_json_object_list(row["tool_calls_json"]),
        file_edits=_json_object_list(row["file_edits_json"]),
        commands_run=_json_list(row["commands_run_json"]),
        decisions_extracted=_json_list(row["decisions_extracted_json"]),
        todos_extracted=_json_list(row["todos_extracted_json"]),
        errors_extracted=_json_list(row["errors_extracted_json"]),
        summary_status=_session_status(row["summary_status"]),
        writeback_status=_session_status(row["writeback_status"]),
        confidence=float(row["confidence"]),
        provider_metadata=_json_object(row["provider_metadata_json"]),
        redaction_incomplete=bool(row["redaction_incomplete"]),
    )


def _json_list(raw: object) -> list[str]:
    try:
        data = json.loads(str(raw or "[]"))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in data] if isinstance(data, list) else []


def _json_object_list(raw: object) -> list[dict[str, object]]:
    try:
        data = json.loads(str(raw or "[]"))
    except json.JSONDecodeError:
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def _json_object(raw: object) -> dict[str, object]:
    try:
        data = json.loads(str(raw or "{}"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _json_dict_float(raw: object) -> dict[str, float]:
    parsed = _json_object(raw)
    values: dict[str, float] = {}
    for key, value in parsed.items():
        if not isinstance(value, (str, int, float)):
            continue
        try:
            values[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return values


def _session_status(raw: object) -> SessionStatus:
    value = str(raw or "pending")
    allowed: set[SessionStatus] = {
        "pending",
        "imported",
        "summarized",
        "writeback_pending",
        "redaction_incomplete",
        "failed",
    }
    if value in allowed:
        return cast(SessionStatus, value)
    return "pending"


def _primary_goal(session: NormalizedSession) -> str:
    if session.title and session.title != session.provider_session_id:
        return session.title
    for message in session.messages:
        if str(message.get("role") or "").lower() == "user":
            text = str(message.get("text") or message.get("content") or "").strip()
            if text:
                return text[:240]
    return session.title or session.provider_session_id


def _project_repo(session: NormalizedSession) -> str:
    return session.workspace_path or session.workspace_id or session.project_id or "unknown"


def _source_provenance(session: NormalizedSession) -> dict[str, Any]:
    return {
        "provider": session.provider,
        "session_id": session.stable_session_id,
        "provider_session_id": session.provider_session_id,
        "source_files": session.source_files,
        "imported_at": session.imported_at,
    }


def _extract_values(items: list[dict[str, object]], key: str) -> list[str]:
    values: list[str] = []
    for item in items:
        value = item.get(key)
        if value:
            values.append(str(value))
    return values


def _extract_files(session: NormalizedSession) -> list[str]:
    values = _extract_values(session.file_edits, "path")
    values.extend(_extract_values(session.file_edits, "file"))
    values.extend(_extract_values(session.tool_calls, "path"))
    return _dedupe(values)


def _extract_decisions(messages: list[dict[str, object]]) -> list[str]:
    return _matching_lines(messages, ("decided", "decision:", "we will", "approach:"))


def _extract_errors(messages: list[dict[str, object]]) -> list[str]:
    return _matching_lines(messages, ("error", "failed", "traceback", "exception", "blocked"))


def _extract_follow_ups(messages: list[dict[str, object]]) -> list[str]:
    return _matching_lines(messages, ("todo", "follow up", "next step", "remaining"))


def _extract_successes(messages: list[dict[str, object]]) -> list[str]:
    return _matching_lines(messages, ("fixed", "resolved", "passed", "implemented"))


def _extract_context_refs(messages: list[dict[str, object]]) -> list[str]:
    refs: list[str] = []
    for message in messages:
        text = str(message.get("text") or message.get("content") or "")
        for token in text.split():
            if "/" in token and (
                token.endswith(".py") or token.endswith(".md") or token.endswith(".ts")
            ):
                refs.append(token.strip("`.,:;()[]"))
    return _dedupe(refs)[:20]


def _matching_lines(messages: list[dict[str, object]], needles: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for message in messages:
        text = str(message.get("text") or message.get("content") or "")
        for line in text.splitlines():
            normalized = line.strip()
            if normalized and any(needle in normalized.lower() for needle in needles):
                matches.append(normalized[:240])
    return _dedupe(matches)[:20]


def _derive_reusable_patterns(commands: list[str], decisions: list[str]) -> list[str]:
    patterns: list[str] = []
    if len(commands) >= 2:
        patterns.append("Repeated command/tool sequence")
    if decisions:
        patterns.append("Explicit implementation decision pattern")
    return patterns


def _skill_candidates(patterns: list[str]) -> list[str]:
    return [f"Skill candidate: {pattern}" for pattern in patterns]


def _confidence(
    session: NormalizedSession,
    commands: list[str],
    files: list[str],
    decisions: list[str],
    errors: list[str],
) -> float:
    score = min(max(session.confidence, 0.0), 1.0)
    if not session.messages:
        score = min(score, 0.3)
    if commands or files:
        score += 0.1
    if decisions:
        score += 0.1
    if errors:
        score += 0.05
    return min(score, 1.0)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output
