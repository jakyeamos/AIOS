#!/usr/bin/env python3
"""
AIOS hook: Stop
Closes the session, writes a summary candidate, extracts next-action hints.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import UTC, datetime

from aios_orchestration_runtime import (
    ensure_runtime_schema,
    evaluate_run_consistency,
    insert_writeback,
    resolve_run_linkage,
    transition_run,
    update_invocation,
)

DB = os.environ.get("AIOS_DB", os.path.expanduser("~/AIOS/data/aios.db"))
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")
SUMMARIES_DIR = os.path.expanduser("~/AIOS/logs/summaries")


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [stop] {msg}\n")
    except Exception:
        pass


def ensure_memory_updates_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_updates (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id),
            run_id TEXT,
            packet_id TEXT,
            session_id TEXT REFERENCES sessions(id),
            source TEXT NOT NULL,
            summary TEXT NOT NULL,
            changes_json TEXT NOT NULL DEFAULT '[]',
            risks_json TEXT NOT NULL DEFAULT '[]',
            open_questions_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )

    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(memory_updates)").fetchall()
    }
    if "run_id" not in existing:
        conn.execute("ALTER TABLE memory_updates ADD COLUMN run_id TEXT")
    if "packet_id" not in existing:
        conn.execute("ALTER TABLE memory_updates ADD COLUMN packet_id TEXT")


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()

    stop = {
        "this", "that", "with", "from", "into", "then", "than", "what", "when",
        "where", "which", "task", "work", "aios", "project", "system",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]{4,}", text.lower())
        if token not in stop
    }


def find_matching_orchestration_run(
    conn: sqlite3.Connection,
    project_id: str | None,
    objective: str | None,
) -> tuple[str | None, str | None]:
    if not project_id:
        return None, None

    rows = conn.execute(
        """
        SELECT id, packet_id, objective, status, created_at
        FROM orchestration_runs
        WHERE project_id = ?
          AND status IN ('ready', 'in_progress')
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (project_id,),
    ).fetchall()

    if not rows:
        return None, None

    session_tokens = _tokenize(objective)
    best_row = None
    best_score = -1

    for row in rows:
        run_tokens = _tokenize(row[2])
        overlap = len(session_tokens & run_tokens)
        score = overlap * 10
        if row[3] == "in_progress":
            score += 5
        if best_row is None or score > best_score:
            best_row = row
            best_score = score

    if best_row and (best_score >= 10 or len(rows) == 1):
        return best_row[0], best_row[1]

    return None, None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"failed to parse stdin: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "")
    if not session_id:
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)

        cur = conn.execute(
            "SELECT id, project_id, started_at, cwd, objective, status FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            log(f"session {session_id} not found")
            conn.close()
            sys.exit(0)
        if row[5] == "closed":
            log(f"session {session_id} already closed, skipping")
            conn.close()
            print("AIOS · session already closed, skipping")
            sys.exit(0)

        now = datetime.now(UTC).isoformat()
        run_outcome = data.get("run_outcome") or "completed"
        explicit_result_summary = data.get("result_summary")
        reason_json = data.get("reason_json")
        if isinstance(reason_json, str):
            try:
                reason_json = json.loads(reason_json)
            except Exception:
                reason_json = {"raw": reason_json}
        if not isinstance(reason_json, dict):
            reason_json = {}

        ensure_memory_updates_table(conn)
        ensure_runtime_schema(conn)

        # Flag reusable insights from this session
        insight_count = 0
        try:
            insight_cur = conn.execute(
                """
                SELECT prompt_text, classification FROM prompts_used
                WHERE session_id = ? AND reusable_candidate = 1
                ORDER BY rowid
                """,
                (session_id,),
            )
            insight_rows = insight_cur.fetchall()
            insight_count = len(insight_rows)
            for prompt_text, classification in insight_rows:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO patterns
                      (id, class, title, domain, state, confidence, source_type,
                       first_observed_at, created_at, project_id)
                    VALUES (?, 'prompt', ?, 'prompting', 'observation', 0.50, 'session-stop', ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        f"Reusable prompt [{classification}]: {prompt_text[:80]}",
                        now,
                        now,
                        row[1],  # project_id
                    ),
                )
        except Exception as e:
            log(f"insight flagging error: {e}")

        # Build summary candidate
        prompts_cur = conn.execute(
            "SELECT classification, prompt_text, reusable_candidate FROM prompts_used WHERE session_id = ? ORDER BY rowid",
            (session_id,),
        )
        prompts = prompts_cur.fetchall()

        artifacts_cur = conn.execute(
            "SELECT artifact_type, path FROM artifacts WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        )
        artifacts = artifacts_cur.fetchall()

        summary = {
            "session_id": session_id,
            "project_id": row[1],
            "started_at": row[2],
            "ended_at": now,
            "cwd": row[3],
            "objective": row[4],
            "prompt_count": len(prompts),
            "reusable_prompt_count": sum(1 for p in prompts if p[2]),
            "artifacts": [{"type": a[0], "path": a[1]} for a in artifacts],
            "prompt_classifications": list({p[0] for p in prompts}),
        }

        # Write candidate file
        os.makedirs(SUMMARIES_DIR, exist_ok=True)
        candidate_path = os.path.join(SUMMARIES_DIR, f"{session_id}.json")
        with open(candidate_path, "w") as f:
            json.dump(summary, f, indent=2)

        # Find handoff file in staging (named {date}-{project}-{session_id[:8]}.md)
        handoff_path = None
        try:
            staging_dir = os.path.expanduser("~/AIOS/staging/session-handoffs")
            short_id = session_id[:8]
            for fname in os.listdir(staging_dir):
                if fname.endswith(f"-{short_id}.md"):
                    handoff_path = os.path.join(staging_dir, fname)
                    break
        except Exception as e:
            log(f"handoff path scan failed: {e}")

        bug_rows = conn.execute(
            "SELECT symptom FROM bug_log WHERE session_id = ? ORDER BY created_at DESC LIMIT 3",
            (session_id,),
        ).fetchall()
        recent_paths = [artifact[1] for artifact in artifacts if artifact[1]][:5]
        change_items = [f"Artifact touched: {path}" for path in recent_paths]

        classifications = sorted({prompt[0] for prompt in prompts if prompt[0]})
        if classifications:
            change_items.append("Prompt classifications: " + ", ".join(classifications))

        risk_items = [f"Observed failure: {bug[0]}" for bug in bug_rows]
        if not handoff_path:
            risk_items.append("No session handoff file was found at close.")

        open_questions = []
        if len(prompts) == 0:
            open_questions.append("Why were no prompts captured for this session?")
        if len(artifacts) == 0:
            open_questions.append("Should this session have produced durable artifacts or was it analysis-only?")

        memory_summary = (
            f"Closed session for objective '{row[4] or 'unspecified'}' with "
            f"{len(prompts)} prompts and {len(artifacts)} artifacts."
        )
        linked_run_id, linked_packet_id, linked_invocation_id, used_legacy_link = resolve_run_linkage(
            conn,
            session_id=session_id,
            payload_run_id=data.get("run_id"),
            payload_invocation_id=data.get("invocation_id"),
            legacy_matcher=find_matching_orchestration_run,
            project_id=row[1],
            objective=row[4],
        )
        memory_update_id = str(uuid.uuid4())

        # Close session in DB
        conn.execute(
            "UPDATE sessions SET status = 'closed', ended_at = ?, summary_candidate_path = ?, handoff_path = ? WHERE id = ?",
            (now, candidate_path, handoff_path, session_id),
        )

        conn.execute(
            """
            INSERT INTO memory_updates (
                id,
                project_id,
                run_id,
                packet_id,
                session_id,
                source,
                summary,
                changes_json,
                risks_json,
                open_questions_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, 'hook-stop', ?, ?, ?, ?, ?)
            """,
            (
                memory_update_id,
                row[1],
                linked_run_id,
                linked_packet_id,
                session_id,
                memory_summary,
                json.dumps(change_items),
                json.dumps(risk_items),
                json.dumps(open_questions),
                now,
            ),
        )

        if linked_run_id:
            run_row = conn.execute(
                """
                SELECT workflow_key, agent_key
                FROM orchestration_runs
                WHERE id = ?
                LIMIT 1
                """,
                (linked_run_id,),
            ).fetchone()

            runtime_summary = explicit_result_summary or memory_summary
            transition_run(
                conn,
                run_id=linked_run_id,
                to_status=run_outcome,
                event_type=run_outcome,
                summary=runtime_summary,
                reason=(
                    {
                        **reason_json,
                        "linkage": "legacy-match" if used_legacy_link else "explicit-handshake",
                    }
                ),
                session_id=session_id,
                invocation_id=linked_invocation_id,
                result_summary=runtime_summary,
                memory_update_id=memory_update_id,
                created_at=now,
            )
            if linked_invocation_id:
                update_invocation(
                    conn,
                    invocation_id=linked_invocation_id,
                    status=run_outcome,
                    session_id=session_id,
                    metadata={
                        "result_summary": runtime_summary,
                        "reason": reason_json,
                        "linked_via": "legacy-match" if used_legacy_link else "explicit-handshake",
                    },
                    ended_at=now,
                )

            insert_writeback(
                conn,
                run_id=linked_run_id,
                project_id=row[1],
                layer_type="project",
                layer_key=row[1],
                title=f"Project writeback from {row[4] or 'unspecified objective'}",
                summary=memory_summary,
                evidence=change_items[:3] if change_items else [memory_summary],
                proposed_change={
                    "source": "hook-stop",
                    "memory_update_id": memory_update_id,
                },
                impact_scope="project",
            )

            if run_row:
                token_regressive = len(change_items) > 4 or len(prompts) > 12
                insert_writeback(
                    conn,
                    run_id=linked_run_id,
                    project_id=row[1],
                    layer_type="workflow",
                    layer_key=run_row[0],
                    title=f"Workflow learning for {run_row[0]}",
                    summary=(
                        "Compact ranked context should stay the default."
                        if not token_regressive
                        else "This run may be pushing packet breadth upward and should not alter defaults without approval."
                    ),
                    evidence=[memory_summary, *risk_items[:2]],
                    proposed_change={
                        "default_packet_policy": "compact-ranked",
                        "workflow_key": run_row[0],
                    },
                    impact_scope="workflow-default",
                    requires_approval=token_regressive,
                    approval_reason=(
                        "Potential token-regressive learning proposal."
                        if token_regressive
                        else None
                    ),
                    token_regressive=token_regressive,
                )
            evaluate_run_consistency(
                conn,
                linked_run_id,
                invocation_id=linked_invocation_id,
            )
            if used_legacy_link:
                log(
                    "legacy run-link fallback used for "
                    f"session {session_id} -> run {linked_run_id}"
                )

        # Log Stop event
        conn.execute(
            """
            INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'Stop', ?, ?)
            """,
            (str(uuid.uuid4()), session_id, now, json.dumps({"summary_candidate": candidate_path})),
        )

        conn.commit()
        conn.close()
        msg = f"{len(prompts)} prompts · {len(artifacts)} artifacts captured · {insight_count} insights flagged"
        log(f"session {session_id} closed. summary: {candidate_path}. handoff: {handoff_path or 'none'}")
        print(f"AIOS · session closed · {msg}")
        subprocess.run(
            ["osascript", "-e", f'display notification "{msg}" with title "AIOS · Session Closed"'],
            capture_output=True,
        )
    except Exception as e:
        log(f"db error: {e}")
        print(f"AIOS · session close failed: {e}")
        subprocess.run(
            ["osascript", "-e", f'display notification "{e}" with title "AIOS · Session Close Failed"'],
            capture_output=True,
        )


if __name__ == "__main__":
    main()
