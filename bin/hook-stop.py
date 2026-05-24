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
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aios_orchestration_runtime import (  # noqa: E402
    ensure_runtime_schema,
    evaluate_run_consistency,
    insert_workflow_execution_report,
    insert_writeback,
    resolve_run_linkage,
    transition_run,
    update_invocation,
)
from hook_lifecycle import ensure_session, load_hook_payload, resolve_hook_session_id  # noqa: E402

from services.rtk_integration import ensure_rtk_schema, rtk_metrics_log  # noqa: E402
from services.session_effectiveness import write_session_effectiveness_receipt  # noqa: E402

DB = os.environ.get("AIOS_DB", os.path.expanduser("~/AIOS/data/aios.db"))
LOG = os.path.expanduser("~/AIOS/logs/hooks.log")
SUMMARIES_DIR = os.path.expanduser("~/AIOS/logs/summaries")


def evaluate_and_record(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from services.success_criteria import (
        evaluate_and_record as evaluate_and_record_impl,  # noqa: PLC0415
    )

    return evaluate_and_record_impl(*args, **kwargs)


def evaluate_standards_health(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from services.standards_health import (  # noqa: PLC0415
        evaluate_and_record as evaluate_standards_impl,
    )

    return evaluate_standards_impl(*args, **kwargs)


def log(msg: str) -> None:
    ts = datetime.now(UTC).isoformat()
    try:
        with open(LOG, "a") as f:
            f.write(f"{ts} [stop] {msg}\n")
    except Exception:
        pass


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _pending_approval_summary(
    conn: sqlite3.Connection, run_id: str | None
) -> tuple[int, list[str]]:
    if not run_id:
        return 0, []
    rows = conn.execute(
        """
        SELECT title
        FROM improvement_writebacks
        WHERE run_id = ?
          AND (requires_approval = 1 OR status = 'pending_approval')
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (run_id,),
    ).fetchall()
    titles = [str(row[0]) for row in rows if row[0]]
    return len(titles), titles


def _stage_evaluations_for_run(
    conn: sqlite3.Connection, run_id: str | None
) -> list[dict[str, Any]]:
    if not run_id or not _table_exists(conn, "success_criteria_stage_findings"):
        return []
    rows = conn.execute(
        """
        SELECT id, stage_key, stage_kind, level
        FROM success_criteria_stage_findings
        WHERE run_id = ?
        ORDER BY stage_key, created_at
        """,
        (run_id,),
    ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for finding_id, stage_key, stage_kind, level in rows:
        key = str(stage_key)
        entry = grouped.setdefault(
            key,
            {
                "stage_key": key,
                "stage_kind": str(stage_kind),
                "blocker_count": 0,
                "warning_count": 0,
                "pass_count": 0,
                "finding_ids": [],
            },
        )
        entry["finding_ids"].append(str(finding_id))
        if level == "blocker":
            entry["blocker_count"] += 1
        elif level == "warning":
            entry["warning_count"] += 1
        elif level == "pass":
            entry["pass_count"] += 1
    return list(grouped.values())


def _writeback_governance_summary(conn: sqlite3.Connection, run_id: str | None) -> dict[str, Any]:
    if not run_id:
        return {
            "writeback_count": 0,
            "approval_required_count": 0,
            "approval_policy_classes": [],
            "writebacks": [],
        }
    rows = conn.execute(
        """
        SELECT id, layer_type, layer_key, impact_scope, status, requires_approval,
               approval_reason, proposed_change_json
        FROM improvement_writebacks
        WHERE run_id = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (run_id,),
    ).fetchall()
    writebacks: list[dict[str, Any]] = []
    policy_classes: list[str] = []
    for row in rows:
        try:
            proposed_change = json.loads(row[7] or "{}")
        except json.JSONDecodeError:
            proposed_change = {}
        policy = (
            proposed_change.get("approval_policy") if isinstance(proposed_change, dict) else None
        )
        policy_class = (
            str(policy.get("policy_class"))
            if isinstance(policy, dict) and policy.get("policy_class")
            else "legacy_or_unclassified"
        )
        policy_classes.append(policy_class)
        writebacks.append(
            {
                "id": row[0],
                "layer_type": row[1],
                "layer_key": row[2],
                "impact_scope": row[3],
                "status": row[4],
                "requires_approval": bool(row[5]),
                "approval_reason": row[6],
                "approval_policy_class": policy_class,
            }
        )
    return {
        "writeback_count": len(writebacks),
        "approval_required_count": len([item for item in writebacks if item["requires_approval"]]),
        "approval_policy_classes": sorted(set(policy_classes)),
        "writebacks": writebacks,
    }


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

    existing = {row[1] for row in conn.execute("PRAGMA table_info(memory_updates)").fetchall()}
    if "run_id" not in existing:
        conn.execute("ALTER TABLE memory_updates ADD COLUMN run_id TEXT")
    if "packet_id" not in existing:
        conn.execute("ALTER TABLE memory_updates ADD COLUMN packet_id TEXT")


def execution_evidence_for_session(conn: sqlite3.Connection, session_id: str) -> list[str]:
    evidence: list[str] = []
    try:
        rows = conn.execute(
            """
            SELECT metadata_json
            FROM artifacts
            WHERE session_id = ? AND artifact_type = 'patch' AND metadata_json IS NOT NULL
            ORDER BY created_at
            """,
            (session_id,),
        ).fetchall()
        for row in rows:
            try:
                metadata = json.loads(row[0] or "{}")
            except json.JSONDecodeError:
                continue
            command = str(metadata.get("command", "")).strip()
            if command:
                evidence.append(f"command: {command[:200]}")
    except sqlite3.Error:
        pass

    try:
        rows = conn.execute(
            """
            SELECT command, exit_code
            FROM rtk_compression_events
            WHERE session_id = ? AND command IS NOT NULL
            ORDER BY created_at
            """,
            (session_id,),
        ).fetchall()
        for row in rows:
            command = str(row[0] or "").strip()
            if not command:
                continue
            exit_code = row[1]
            suffix = f" exit_code={exit_code}" if exit_code is not None else ""
            evidence.append(f"rtk-command: {command[:180]}{suffix}")
    except sqlite3.Error:
        pass

    deduped: list[str] = []
    seen: set[str] = set()
    for item in evidence:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()

    stop = {
        "this",
        "that",
        "with",
        "from",
        "into",
        "then",
        "than",
        "what",
        "when",
        "where",
        "which",
        "task",
        "work",
        "aios",
        "project",
        "system",
    }
    return {token for token in re.findall(r"[a-z0-9]{4,}", text.lower()) if token not in stop}


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


def legacy_run_link_fallback_enabled() -> bool:
    return os.environ.get("AIOS_ALLOW_LEGACY_RUN_LINK", "").lower() in {"1", "true", "yes"}


def get_project_name(conn: sqlite3.Connection, project_id: str | None) -> str | None:
    if not project_id:
        return None
    row = conn.execute(
        "SELECT name FROM projects WHERE id = ? LIMIT 1",
        (project_id,),
    ).fetchone()
    if not row:
        return None
    return str(row[0])


def main() -> None:
    data = load_hook_payload(
        log=log,
        hook_name="stop",
        logs_dir=os.path.dirname(LOG),
        allow_current_session_fallback=True,
    )

    session_id = data.get("session_id", "")
    if not session_id:
        sys.exit(0)

    try:
        conn = sqlite3.connect(DB)
        resolved_session_id = resolve_hook_session_id(
            conn,
            payload_session_id=session_id,
            payload_cwd=data.get("cwd"),
            logs_dir=os.path.dirname(LOG),
            hook_name="stop",
            log=log,
        )
        if not resolved_session_id:
            conn.close()
            sys.exit(0)
        session_id = resolved_session_id
        ensure_session(
            conn,
            session_id=session_id,
            cwd=data.get("cwd"),
            objective=data.get("objective"),
            source_event="Stop",
            log=log,
        )
        conn.commit()

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
        ensure_rtk_schema(conn)

        # Count reusable prompt candidates from this session. Prompt text is not
        # inserted into patterns here; library promotion is handled separately.
        insight_count = 0
        try:
            insight_cur = conn.execute(
                """
                SELECT COUNT(*) FROM prompts_used
                WHERE session_id = ? AND reusable_candidate = 1
                """,
                (session_id,),
            )
            insight_count = int(insight_cur.fetchone()[0] or 0)
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
            open_questions.append(
                "Should this session have produced durable artifacts or was it analysis-only?"
            )

        memory_summary = (
            f"Closed session for objective '{row[4] or 'unspecified'}' with "
            f"{len(prompts)} prompts and {len(artifacts)} artifacts."
        )
        project_name = get_project_name(conn, row[1])
        legacy_fallback_enabled = legacy_run_link_fallback_enabled()
        linked_run_id, linked_packet_id, linked_invocation_id, used_legacy_link = (
            resolve_run_linkage(
                conn,
                session_id=session_id,
                payload_run_id=data.get("run_id"),
                payload_invocation_id=data.get("invocation_id"),
                legacy_matcher=find_matching_orchestration_run if legacy_fallback_enabled else None,
                project_id=row[1],
                objective=row[4],
            )
        )
        if not linked_run_id and row[1]:
            log(
                "strict run-linkage required; no explicit run/session/invocation handshake "
                f"found for session {session_id}"
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

        run_row = None
        consistency_eval_id = None
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
            consistency_eval_id = evaluate_run_consistency(
                conn,
                linked_run_id,
                invocation_id=linked_invocation_id,
            )
            if used_legacy_link:
                log(
                    f"legacy run-link fallback used for session {session_id} -> run {linked_run_id}"
                )

        criteria_changed_paths = [
            path for artifact_type, path in artifacts if path and artifact_type == "patch"
        ]
        prompt_classifications = [prompt[0] for prompt in prompts if prompt[0]]
        accepted_tradeoffs = reason_json.get("accepted_tradeoffs", [])
        if not isinstance(accepted_tradeoffs, list):
            accepted_tradeoffs = [str(accepted_tradeoffs)]
        execution_evidence = execution_evidence_for_session(conn, session_id)
        criteria_eval = evaluate_and_record(
            conn,
            project_id=row[1],
            project_name=project_name,
            run_id=linked_run_id,
            session_id=session_id,
            packet_id=linked_packet_id,
            objective=row[4],
            task_id=linked_run_id or session_id,
            trigger_kind="session_close",
            cwd=row[3],
            prompt_classifications=prompt_classifications,
            changed_files=criteria_changed_paths,
            execution_evidence=execution_evidence,
            used_legacy_link=used_legacy_link,
            accepted_tradeoffs=accepted_tradeoffs,
        )
        log(
            "success criteria evaluation recorded: "
            f"{criteria_eval['evaluation_id']} ({criteria_eval['summary']})"
        )
        standards_eval = evaluate_standards_health(
            conn,
            project_id=row[1],
            project_name=project_name,
            run_id=linked_run_id,
            session_id=session_id,
            trigger_kind="session_close",
        )
        log(
            "standards health snapshot recorded: "
            f"{standards_eval['snapshot_id']} ({standards_eval['summary']})"
        )
        rtk_metrics = rtk_metrics_log(conn, session_id=session_id)
        log(
            "rtk compression metrics: "
            f"events={rtk_metrics['event_count']} "
            f"tokens={rtk_metrics['raw_tokens']}->{rtk_metrics['compressed_tokens']} "
            f"saved={rtk_metrics['tokens_saved']} "
            f"reduction={rtk_metrics['weighted_reduction_percent']}%"
        )
        if linked_run_id:
            pending_approval_count, approval_titles = _pending_approval_summary(conn, linked_run_id)
            governance_summary = _writeback_governance_summary(conn, linked_run_id)
            stage_evaluations = _stage_evaluations_for_run(conn, linked_run_id)
            closeout_summary = {
                "report_type": "governed_closeout",
                "run_id": linked_run_id,
                "packet_id": linked_packet_id,
                "session_id": session_id,
                "invocation_id": linked_invocation_id,
                "outcome": run_outcome,
                "result_summary": explicit_result_summary or memory_summary,
                "changed_artifacts": criteria_changed_paths,
                "checks_run": {
                    "success_criteria_evaluation_id": criteria_eval["evaluation_id"],
                    "standards_snapshot_id": standards_eval["snapshot_id"],
                    "consistency_evaluation_id": consistency_eval_id,
                },
                "approvals": {
                    "pending_approval_count": pending_approval_count,
                    "pending_titles": approval_titles,
                },
                "unresolved_deltas": {
                    "risks": risk_items,
                    "open_questions": open_questions,
                    "accepted_tradeoffs": accepted_tradeoffs,
                },
                "writeback_implications": {
                    "memory_update_id": memory_update_id,
                    "project_writeback_expected": True,
                    "workflow_learning_writeback_expected": run_row is not None,
                },
                "governance": {
                    **governance_summary,
                    "stage_evaluations": stage_evaluations,
                    "unresolved_follow_up_count": len(risk_items) + len(open_questions),
                    "requires_review": pending_approval_count > 0
                    or len(risk_items) > 0
                    or len(open_questions) > 0
                    or any(item["blocker_count"] > 0 for item in stage_evaluations),
                },
                "generated_at": now,
            }
            insert_workflow_execution_report(
                conn,
                run_id=linked_run_id,
                invocation_id=linked_invocation_id,
                workflow_key=run_row[0] if run_row else "implementation-delivery",
                status=run_outcome,
                report=closeout_summary,
                artifact_path=str(candidate_path),
            )

        # Log Stop event
        conn.execute(
            """
            INSERT INTO tool_events (id, session_id, source_tool, event_type, event_time, payload_json)
            VALUES (?, ?, 'claude-code', 'Stop', ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                now,
                json.dumps({"summary_candidate": candidate_path, "rtk_metrics": rtk_metrics}),
            ),
        )

        effectiveness_receipt = write_session_effectiveness_receipt(conn, session_id)
        if effectiveness_receipt:
            log(
                "session effectiveness receipt recorded: "
                f"{effectiveness_receipt['rating']} ({effectiveness_receipt['score']})"
            )

        conn.commit()
        conn.close()
        msg = (
            f"{len(prompts)} prompts · {len(artifacts)} artifacts captured · "
            f"{insight_count} insights flagged · RTK saved {rtk_metrics['tokens_saved']} tokens"
        )
        log(
            f"session {session_id} closed. summary: {candidate_path}. handoff: {handoff_path or 'none'}"
        )
        print(f"AIOS · session closed · {msg}")
        subprocess.run(
            ["osascript", "-e", f'display notification "{msg}" with title "AIOS · Session Closed"'],
            capture_output=True,
        )
    except Exception as e:
        log(f"db error: {e}")
        print(f"AIOS · session close failed: {e}")
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{e}" with title "AIOS · Session Close Failed"',
            ],
            capture_output=True,
        )


if __name__ == "__main__":
    main()
