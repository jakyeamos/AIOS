from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict


class SessionActivitySnapshot(TypedDict):
    session_id: str
    project_id: str | None
    project_name: str | None
    run_id: str | None
    invocation_id: str | None
    status: str
    started_at: str | None
    ended_at: str | None
    cwd: str | None
    objective: str | None
    prompt_count: int
    artifact_count: int
    tool_event_count: int
    bug_count: int
    reusable_prompt_count: int
    rtk_tokens_saved: int
    handoff_present: bool
    summary_present: bool
    run_linked: bool


def ensure_session_effectiveness_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_effectiveness_receipts (
          id TEXT PRIMARY KEY,
          session_id TEXT NOT NULL REFERENCES sessions(id),
          project_id TEXT REFERENCES projects(id),
          run_id TEXT REFERENCES orchestration_runs(id),
          score REAL NOT NULL,
          rating TEXT NOT NULL,
          prompt_count INTEGER NOT NULL,
          artifact_count INTEGER NOT NULL,
          tool_event_count INTEGER NOT NULL,
          bug_count INTEGER NOT NULL,
          reusable_prompt_count INTEGER NOT NULL,
          rtk_tokens_saved INTEGER NOT NULL,
          activity_lights_json TEXT NOT NULL DEFAULT '{}',
          blockers_json TEXT NOT NULL DEFAULT '[]',
          warnings_json TEXT NOT NULL DEFAULT '[]',
          receipt_json TEXT NOT NULL,
          receipt_path TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_effectiveness_session
        ON session_effectiveness_receipts(session_id, created_at DESC)
        """
    )


def load_activity_snapshot(
    conn: sqlite3.Connection,
    session_id: str,
) -> SessionActivitySnapshot | None:
    row = conn.execute(
        """
        SELECT s.id, s.project_id, p.name, s.run_id, s.invocation_id, s.status,
               s.started_at, s.ended_at, s.cwd, s.objective,
               s.handoff_path, s.summary_candidate_path
        FROM sessions s
        LEFT JOIN projects p ON p.id = s.project_id
        WHERE s.id = ?
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return None

    def count(query: str) -> int:
        value = conn.execute(query, (session_id,)).fetchone()[0]
        return int(value or 0)

    tokens_saved = 0
    try:
        tokens_saved = count(
            """
            SELECT COALESCE(SUM(MAX(estimated_raw_tokens - estimated_compressed_tokens, 0)), 0)
            FROM rtk_compression_events
            WHERE session_id = ?
            """
        )
    except sqlite3.OperationalError:
        tokens_saved = 0

    return {
        "session_id": str(row[0]),
        "project_id": row[1],
        "project_name": row[2],
        "run_id": row[3],
        "invocation_id": row[4],
        "status": str(row[5]),
        "started_at": row[6],
        "ended_at": row[7],
        "cwd": row[8],
        "objective": row[9],
        "prompt_count": count("SELECT COUNT(*) FROM prompts_used WHERE session_id = ?"),
        "artifact_count": count("SELECT COUNT(*) FROM artifacts WHERE session_id = ?"),
        "tool_event_count": count("SELECT COUNT(*) FROM tool_events WHERE session_id = ?"),
        "bug_count": count("SELECT COUNT(*) FROM bug_log WHERE session_id = ?"),
        "reusable_prompt_count": count(
            """
            SELECT COUNT(*)
            FROM prompts_used
            WHERE session_id = ? AND reusable_candidate = 1
            """
        ),
        "rtk_tokens_saved": tokens_saved,
        "handoff_present": bool(row[10]),
        "summary_present": bool(row[11]),
        "run_linked": bool(row[3] or row[4]),
    }


def _light(state: str, label: str, reason: str) -> dict[str, str]:
    return {"state": state, "label": label, "reason": reason}


def build_session_effectiveness_receipt(
    snapshot: SessionActivitySnapshot,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(UTC).isoformat()
    blockers: list[str] = []
    warnings: list[str] = []
    score = 100

    if snapshot["prompt_count"] == 0:
        blockers.append("No prompts were captured for the session.")
        score -= 25
    if snapshot["tool_event_count"] == 0:
        blockers.append("No tool activity was captured for the session.")
        score -= 20
    if not snapshot["run_linked"]:
        warnings.append("Session is not linked to a governed run or invocation.")
        score -= 12
    if snapshot["artifact_count"] == 0:
        warnings.append("No durable artifacts were captured.")
        score -= 8
    if snapshot["bug_count"] > 0:
        warnings.append(f"{snapshot['bug_count']} failure signal(s) were captured.")
        score -= min(snapshot["bug_count"] * 10, 25)
    if not snapshot["summary_present"]:
        warnings.append("Summary receipt path is not present yet.")
        score -= 5
    if not snapshot["handoff_present"]:
        warnings.append("No session handoff was found.")
        score -= 5

    score = max(0, min(score, 100))
    rating = "working" if score >= 80 else "mixed" if score >= 55 else "needs_attention"

    activity_lights = {
        "capture": _light(
            "green" if snapshot["tool_event_count"] > 0 else "red",
            "capture",
            f"{snapshot['tool_event_count']} tool event(s) captured.",
        ),
        "prompts": _light(
            "green" if snapshot["prompt_count"] > 0 else "red",
            "prompts",
            f"{snapshot['prompt_count']} prompt(s) captured.",
        ),
        "work": _light(
            "green" if snapshot["artifact_count"] > 0 else "yellow",
            "work",
            f"{snapshot['artifact_count']} artifact(s) captured.",
        ),
        "quality": _light(
            "green" if snapshot["bug_count"] == 0 else "red",
            "quality",
            f"{snapshot['bug_count']} failure signal(s) captured.",
        ),
        "governance": _light(
            "green" if snapshot["run_linked"] else "yellow",
            "governance",
            "Run linkage present." if snapshot["run_linked"] else "Run linkage missing.",
        ),
        "receipts": _light(
            "green" if snapshot["summary_present"] else "yellow",
            "receipts",
            "Summary receipt present." if snapshot["summary_present"] else "Summary receipt pending.",
        ),
    }

    return {
        "receipt_type": "session_effectiveness",
        "session_id": snapshot["session_id"],
        "project_id": snapshot["project_id"],
        "project_name": snapshot["project_name"],
        "run_id": snapshot["run_id"],
        "invocation_id": snapshot["invocation_id"],
        "score": score,
        "rating": rating,
        "activity_lights": activity_lights,
        "measures": {
            "prompt_count": snapshot["prompt_count"],
            "artifact_count": snapshot["artifact_count"],
            "tool_event_count": snapshot["tool_event_count"],
            "bug_count": snapshot["bug_count"],
            "reusable_prompt_count": snapshot["reusable_prompt_count"],
            "rtk_tokens_saved": snapshot["rtk_tokens_saved"],
            "run_linked": snapshot["run_linked"],
            "handoff_present": snapshot["handoff_present"],
            "summary_present": snapshot["summary_present"],
        },
        "blockers": blockers,
        "warnings": warnings,
        "generated_at": generated_at,
    }


def write_session_effectiveness_receipt(
    conn: sqlite3.Connection,
    session_id: str,
    *,
    receipt_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    ensure_session_effectiveness_schema(conn)
    snapshot = load_activity_snapshot(conn, session_id)
    if not snapshot:
        return None

    receipt = build_session_effectiveness_receipt(snapshot)
    base_dir = Path(receipt_dir or os.path.expanduser("~/AIOS/logs/session-effectiveness"))
    base_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = base_dir / f"{session_id}.json"
    receipt["receipt_path"] = str(receipt_path)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    conn.execute(
        """
        INSERT INTO session_effectiveness_receipts (
            id, session_id, project_id, run_id, score, rating, prompt_count,
            artifact_count, tool_event_count, bug_count, reusable_prompt_count,
            rtk_tokens_saved, activity_lights_json, blockers_json, warnings_json,
            receipt_json, receipt_path, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            session_id,
            receipt["project_id"],
            receipt["run_id"],
            float(receipt["score"]),
            receipt["rating"],
            snapshot["prompt_count"],
            snapshot["artifact_count"],
            snapshot["tool_event_count"],
            snapshot["bug_count"],
            snapshot["reusable_prompt_count"],
            snapshot["rtk_tokens_saved"],
            json.dumps(receipt["activity_lights"]),
            json.dumps(receipt["blockers"]),
            json.dumps(receipt["warnings"]),
            json.dumps(receipt),
            str(receipt_path),
            receipt["generated_at"],
        ),
    )
    return receipt


def latest_effectiveness_receipt(
    conn: sqlite3.Connection,
    session_id: str,
) -> dict[str, Any] | None:
    ensure_session_effectiveness_schema(conn)
    row = conn.execute(
        """
        SELECT receipt_json
        FROM session_effectiveness_receipts
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(str(row[0]))
    except json.JSONDecodeError:
        return None
