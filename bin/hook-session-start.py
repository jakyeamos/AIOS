#!/usr/bin/env python3
"""
AIOS hook: SessionStart
Creates a session row in SQLite on session open.
Generates a compact context packet and injects it into the session.
Claude Code passes JSON via stdin.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aios_orchestration_runtime import (  # noqa: E402
    ensure_runtime_schema,
    link_session_runtime,
    load_resume_snapshot,
    store_resume_snapshot,
    transition_run,
    update_invocation,
)
from aios_paths import get_vault_root  # noqa: E402
from hook_lifecycle import (  # noqa: E402
    get_or_create_project,
    load_hook_payload,
    resolve_session_cwd,
)

from services.agent_rules import agent_rules_context  # noqa: E402
from services.rtk_integration import ensure_rtk_schema, load_compression_rules  # noqa: E402

DB = os.environ.get("AIOS_DB", os.path.expanduser("~/AIOS/data/aios.db"))
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")
VAULT = str(get_vault_root())
VAULT_SEARCH = os.path.expanduser("~/AIOS/bin/vault-search.py")
PACKET_DIR = os.path.expanduser("~/AIOS/logs")
MAX_PACKET_CHARS = 1800  # ~400 tokens

USER_STORY_LOOP_TERMS = {
    "app",
    "application",
    "feature",
    "features",
    "frontend",
    "screen",
    "screens",
    "ui",
    "ux",
    "user-facing",
    "user story",
    "user stories",
    "verification",
    "verify",
}


def preview_applicable_criteria(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from services.success_criteria import (
        preview_applicable_criteria as preview_applicable_criteria_impl,  # noqa: PLC0415
    )

    return preview_applicable_criteria_impl(*args, **kwargs)


def resolve_task_standards(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from services.success_criteria import (
        resolve_task_standards as resolve_task_standards_impl,  # noqa: PLC0415
    )

    return resolve_task_standards_impl(*args, **kwargs)


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [session-start] {msg}\n")
    except Exception:
        pass


def get_project_name(conn: sqlite3.Connection, project_id: str) -> str:
    cur = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
    row = cur.fetchone()
    return row[0] if row else ""


def vault_search(args: list[str]) -> dict:
    """Call vault-search.py and return parsed JSON result."""
    try:
        result = subprocess.run(
            ["python3", VAULT_SEARCH] + args,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except Exception:
        pass
    return {"results": [], "count": 0}


def get_active_rules(conn: sqlite3.Connection, max_rules: int = 3) -> list[str]:
    """Return top N human-approved rules by confidence for session context."""
    try:
        cur = conn.execute(
            "SELECT title, body, domain, confidence FROM active_rules ORDER BY confidence DESC LIMIT ?",
            (max_rules,),
        )
        rules = []
        for title, body, domain, _confidence in cur.fetchall():
            text = body.strip() if body else title
            rules.append(f"- [{domain}] {text}")
        return rules
    except Exception:
        return []


def get_review_queue_hint(conn: sqlite3.Connection) -> str | None:
    """Return a one-line hint if patterns are awaiting human approval."""
    try:
        count = conn.execute("SELECT COUNT(*) FROM patterns WHERE state='knowledge'").fetchone()[0]
        if count > 0:
            return f"{count} pattern(s) in review queue — run: approve-pattern --list"
        return None
    except Exception:
        return None


def get_open_bug(conn: sqlite3.Connection, project_id: str) -> str | None:
    """Return a one-line summary of the most recent open bug for this project."""
    cur = conn.execute(
        "SELECT symptom, root_cause FROM bug_log WHERE project_id = ? AND status = 'open' ORDER BY created_at DESC LIMIT 1",
        (project_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    symptom, root_cause = row
    if root_cause:
        return f"{symptom} (root cause: {root_cause})"
    return symptom


def extract_open_actions(handoff_excerpt: str) -> list[str]:
    """Extract unchecked action items from a handoff excerpt."""
    actions = []
    for line in handoff_excerpt.splitlines():
        line = line.strip()
        if line.startswith("- [ ]") and len(line) > 5:
            actions.append(line[5:].strip())
    return actions[:5]  # Cap at 5


def get_cts_context(cwd: str, objective: str) -> str | None:
    repo_root = Path(cwd).expanduser().resolve()
    try:
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from services.cts import get_minimal_context  # noqa: PLC0415
    except Exception as e:
        log(f"cts unavailable: {e}")
        return None
    try:
        payload = get_minimal_context(
            repo_path=str(repo_root),
            task=objective or "session startup context",
            changed_files=[],
            max_tokens=240,
        )
    except Exception as e:
        log(f"cts context lookup failed: {e}")
        return None
    if payload.get("index_status") != "current":
        return None
    nodes = payload.get("directly_relevant_nodes", [])[:6]
    node_text = "\n".join(f"- `{node}`" for node in nodes) if nodes else "- (none)"
    confidence_note = payload.get("confidence_note") or "No confidence caveats."
    return (
        "**Code Topology (CTS):**\n"
        f"- Architecture: {payload.get('architecture_summary', '')}\n"
        f"- Estimated blast radius: {payload.get('estimated_blast_radius', 0)} files\n"
        f"- Confidence: {confidence_note}\n"
        f"- Relevant nodes:\n{node_text}"
    )


def user_story_verification_loop_context(objective: str) -> str | None:
    normalized = objective.lower()
    if not any(term in normalized for term in USER_STORY_LOOP_TERMS):
        return None
    return (
        "**User-story verification loop:**\n"
        "- For broad app, UI, UX, or feature verification, keep one canonical spreadsheet at "
        "`.planning/user-story-verification.csv`.\n"
        "- Required columns: `feature_id`, `feature`, `source_refs`, `user_story`, "
        "`expected_behavior`, `status`, `evidence`, `errors`, `fix_ref`, `retest_status`.\n"
        "- First enumerate implemented features from code and write expected behavior from the "
        "actual implementation, not assumptions.\n"
        "- Then test each user story through the real UI/code path and document errors before "
        "fixing them.\n"
        "- After fixes, retest every affected story and leave rows as failing/blocked when evidence "
        "is missing."
    )


def generate_packet(
    project_name: str,
    project_id: str,
    conn: sqlite3.Connection,
    cwd: str,
    objective: str,
    session_id: str | None = None,
) -> str:
    """Assemble a compact session context packet."""
    parts = []

    # 0. Repo-level agent rules are the highest-level behavioral contract for AIOS runs.
    rules_context = agent_rules_context(max_rules=6)
    if rules_context:
        parts.append(rules_context)

    verification_loop_context = user_story_verification_loop_context(objective)
    if verification_loop_context:
        parts.append(verification_loop_context)

    # 1. Project note — extract Current Focus section only
    note_result = vault_search(["--note", project_name])
    if note_result.get("count", 0) > 0:
        note_excerpt = note_result["results"][0].get("excerpt", "")
        if (
            note_excerpt
            and "<!-- No commits" not in note_excerpt
            and "<!-- Add context" not in note_excerpt
        ):
            # Extract just Current Focus if present
            import re

            cf_match = re.search(r"## Current Focus\n\n(.*?)(?=\n## |\Z)", note_excerpt, re.DOTALL)
            if cf_match:
                focus_text = cf_match.group(1).strip()
                if focus_text and "<!--" not in focus_text and len(focus_text) > 20:
                    parts.append(f"**Current Focus ({project_name}):**\n{focus_text[:400]}")

    # 2. Open next actions from most recent handoff
    handoff_result = vault_search(["--handoffs", project_name, "--last", "1"])
    if handoff_result.get("count", 0) > 0:
        excerpt = handoff_result["results"][0].get("excerpt", "")
        actions = extract_open_actions(excerpt)
        if actions:
            action_lines = "\n".join(f"- [ ] {a}" for a in actions)
            parts.append(f"**Open actions (last session):**\n{action_lines}")

        # Grab outcome from most recent handoff too
        import re

        outcome_match = re.search(r"### Outcome\n(.+?)(?=\n###|\Z)", excerpt, re.DOTALL)
        if outcome_match:
            outcome = outcome_match.group(1).strip()[:200]
            if outcome:
                parts.append(f"**Last session outcome:** {outcome}")

    # 3. Most recent open bug
    open_bug = get_open_bug(conn, project_id)
    if open_bug:
        parts.append(f"**Open bug:** {open_bug[:200]}")

    # 4. Active rules (human-approved patterns)
    rules = get_active_rules(conn, max_rules=3)
    if rules:
        parts.append("**Active rules:**\n" + "\n".join(rules))

    # 5. Pattern review queue hint (shown only when actionable)
    review_hint = get_review_queue_hint(conn)
    if review_hint:
        parts.append(f"**Review queue:** {review_hint}")

    # 6. Success criteria preview (resolved before implementation begins)
    standards_resolution = resolve_task_standards(
        project_id=project_id,
        project_name=project_name,
        objective=objective,
        conn=conn,
    )
    criteria_rows = standards_resolution.get("criteria", [])
    if criteria_rows:
        criteria_lines = [
            f"- {row['id']} ({'blocker' if row['blocking'] else 'advisory'})"
            for row in criteria_rows[:8]
        ]
        header = "**Applicable success criteria:**"
        parts.append(header + "\n" + "\n".join(criteria_lines))
    standard_rows = standards_resolution.get("standards", [])
    if standard_rows:
        standard_lines = [
            f"- {row['standard_id']} ({row['domain']}; weight={row['weight']})"
            for row in standard_rows[:8]
        ]
        parts.append("**Applicable standards:**\n" + "\n".join(standard_lines))
    triggers = standards_resolution.get("execution_first_triggers", [])
    if triggers:
        trigger_lines = [f"- {trigger}" for trigger in triggers[:8]]
        parts.append("**Execution-first triggers:**\n" + "\n".join(trigger_lines))

    # 7. Code Topology Service context (only when index is current)
    cts_context = get_cts_context(cwd, objective)
    if cts_context:
        parts.append(cts_context)

    # 8. RTK command-output compression policy
    try:
        rtk_rules = load_compression_rules()
        default_mode = rtk_rules.get("default_mode", "compressed")
        preserve = ", ".join(str(item) for item in rtk_rules.get("preserve", [])[:4])
        fallback = rtk_rules.get("fallbacks", {}).get("ambiguous_failure", "adaptive")
        parts.append(
            "**RTK context compression:**\n"
            f"- Default command mode: {default_mode}\n"
            f"- Preserve: {preserve}\n"
            f"- Ambiguous failures expand via: {fallback}\n"
            "- Use `python bin/rtk-run.py --mode adaptive -- <command>` for managed command output."
        )
    except Exception as e:
        log(f"rtk rules unavailable: {e}")

    # 9. Linked serious-work resume snapshot
    if session_id:
        session_row = conn.execute(
            "SELECT run_id FROM sessions WHERE id = ? LIMIT 1",
            (session_id,),
        ).fetchone()
        if session_row and session_row[0]:
            snapshot = load_resume_snapshot(conn, str(session_row[0]))
            if snapshot:
                parts.append(
                    "**Resume snapshot:**\n"
                    f"- Stage: {snapshot.get('current_stage') or 'unknown'}\n"
                    f"- Next action: {snapshot.get('next_recommended_action') or 'Continue the linked run.'}\n"
                    f"- Pending approvals: {int(snapshot.get('pending_approval_count') or 0)}"
                )

    if not parts:
        return ""

    packet = "\n\n".join(parts)
    if len(packet) > MAX_PACKET_CHARS:
        packet = packet[:MAX_PACKET_CHARS] + "\n\n_(packet truncated)_"
    return packet


def main() -> None:
    data = load_hook_payload(log=log, hook_name="session-start")

    session_id = data.get("session_id", "")
    cwd = data.get("cwd", os.getcwd())
    objective = data.get("objective", "")
    run_id = data.get("run_id")
    invocation_id = data.get("invocation_id")
    backend_key = data.get("backend_key")

    if not session_id:
        log("no session_id in payload")
        sys.exit(0)

    context_packet = ""

    try:
        conn = sqlite3.connect(DB)
        resolved_cwd = resolve_session_cwd(conn, cwd)
        project_id = get_or_create_project(conn, resolved_cwd)
        ensure_runtime_schema(conn)
        ensure_rtk_schema(conn)

        # Check if session already exists — /clear re-fires SessionStart with same ID
        existing = conn.execute(
            "SELECT id, status FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if existing:
            if run_id or invocation_id:
                link_session_runtime(
                    conn,
                    session_id=session_id,
                    run_id=run_id,
                    invocation_id=invocation_id,
                    runtime_metadata={
                        "backend_key": backend_key,
                        "cwd": resolved_cwd,
                    },
                    objective=objective or None,
                )
                if invocation_id:
                    update_invocation(
                        conn,
                        invocation_id=invocation_id,
                        status="running",
                        session_id=session_id,
                        metadata={"cwd": resolved_cwd},
                        started_at=datetime.now(UTC).isoformat(),
                    )
                if run_id:
                    store_resume_snapshot(
                        conn,
                        run_id,
                        {
                            "packet_id": data.get("packet_id"),
                            "current_stage": "execution_active",
                            "next_recommended_action": "Continue execution against the governed packet and request targeted expansion only when needed.",
                            "pending_approval_count": 0,
                            "approval_targets": [],
                            "updated_at": datetime.now(UTC).isoformat(),
                        },
                    )
                    transition_run(
                        conn,
                        run_id=run_id,
                        to_status="in_progress",
                        event_type="in_progress",
                        summary="Runtime session started.",
                        session_id=session_id,
                        invocation_id=invocation_id,
                        reason={"kind": "session_start", "backend_key": backend_key},
                        resume_snapshot={
                            "current_stage": "execution_active",
                            "next_recommended_action": "Continue execution against the governed packet and request targeted expansion only when needed.",
                            "pending_approval_count": 0,
                            "approval_targets": [],
                        },
                    )
                conn.commit()
            conn.close()
            current_path = os.path.expanduser("~/AIOS/logs/current_session")
            with open(current_path, "w") as f:
                f.write(session_id)
            log(f"session {session_id} re-fired (clear event), skipping duplicate row")
            sys.exit(0)

        conn.execute(
            """
            INSERT OR IGNORE INTO sessions
              (id, project_id, tool, started_at, objective, status, cwd)
            VALUES (?, ?, 'claude-code', ?, ?, 'open', ?)
            """,
            (
                session_id,
                project_id,
                datetime.now(UTC).isoformat(),
                objective or None,
                resolved_cwd,
            ),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'SessionStart', ?, ?)
            """,
            (
                f"{session_id}-start",
                session_id,
                datetime.now(UTC).isoformat(),
                json.dumps(data),
            ),
        )
        if run_id or invocation_id:
            link_session_runtime(
                conn,
                session_id=session_id,
                run_id=run_id,
                invocation_id=invocation_id,
                runtime_metadata={
                    "backend_key": backend_key,
                    "cwd": resolved_cwd,
                },
                objective=objective or None,
            )
        if invocation_id:
            update_invocation(
                conn,
                invocation_id=invocation_id,
                status="running",
                session_id=session_id,
                metadata={"cwd": resolved_cwd},
                started_at=datetime.now(UTC).isoformat(),
            )
        if run_id:
            store_resume_snapshot(
                conn,
                run_id,
                {
                    "packet_id": data.get("packet_id"),
                    "current_stage": "execution_active",
                    "next_recommended_action": "Continue execution against the governed packet and request targeted expansion only when needed.",
                    "pending_approval_count": 0,
                    "approval_targets": [],
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )
            transition_run(
                conn,
                run_id=run_id,
                to_status="in_progress",
                event_type="in_progress",
                summary="Runtime session started.",
                session_id=session_id,
                invocation_id=invocation_id,
                reason={"kind": "session_start", "backend_key": backend_key},
                resume_snapshot={
                    "current_stage": "execution_active",
                    "next_recommended_action": "Continue execution against the governed packet and request targeted expansion only when needed.",
                    "pending_approval_count": 0,
                    "approval_targets": [],
                },
            )
        conn.commit()

        # Generate session packet
        project_name = get_project_name(conn, project_id)
        if project_name:
            try:
                context_packet = generate_packet(
                    project_name=project_name,
                    project_id=project_id,
                    conn=conn,
                    cwd=resolved_cwd,
                    objective=objective,
                    session_id=session_id,
                )
                if context_packet:
                    packet_path = os.path.join(PACKET_DIR, f"session_packet_{session_id}.md")
                    with open(packet_path, "w") as f:
                        f.write(context_packet)
                    log(f"session packet written: {packet_path} ({len(context_packet)} chars)")
            except Exception as e:
                log(f"packet generation error: {e}")

        conn.close()

        # Write current session pointer
        current_path = os.path.expanduser("~/AIOS/logs/current_session")
        with open(current_path, "w") as f:
            f.write(session_id)

        log(f"session {session_id} opened (project: {project_id}, cwd: {resolved_cwd})")

    except Exception as e:
        log(f"db error: {e}")

    # Output context packet for injection (empty string = no injection)
    if context_packet:
        output = {"context": f"<!-- AIOS session context -->\n{context_packet}"}
        print(json.dumps(output))


if __name__ == "__main__":
    main()
