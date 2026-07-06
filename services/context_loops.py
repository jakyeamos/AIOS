from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
import uuid
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXT_LOOP_ROOT = ROOT / "aios" / "context-loops"
APPROVED_LESSONS_FILE = "approved-lessons.md"
REJECTED_LESSONS_FILE = "rejected-lessons.md"

ReviewOutcome = Literal[
    "sent_unchanged",
    "edited_and_sent",
    "edited_not_sent",
    "deleted",
    "rejected",
    "left_pending",
    "replaced_manually",
    "human_judgment_only",
]
LessonDestination = Literal[
    "writing_guidance",
    "retrieval_policy",
    "source_list",
    "safety_check_policy",
    "human_handoff_rule",
    "project_memory",
    "personal_preference_memory",
    "no_durable_memory",
]
LearningCategory = Literal[
    "style_preference",
    "missing_fact",
    "missing_relationship_context",
    "unsupported_commitment",
    "bad_source",
    "stale_context",
    "incomplete_retrieval",
    "task_misunderstood",
    "human_judgment_only",
    "one_off_exception",
]

REVIEW_OUTCOMES: tuple[ReviewOutcome, ...] = (
    "sent_unchanged",
    "edited_and_sent",
    "edited_not_sent",
    "deleted",
    "rejected",
    "left_pending",
    "replaced_manually",
    "human_judgment_only",
)


@dataclass(frozen=True)
class LoopContext:
    workflow: str
    task_type: str
    task_input: str
    approved_lessons: tuple[str, ...]
    retrieved_context: tuple[dict[str, Any], ...]
    context_sources: tuple[dict[str, Any], ...]


def ensure_context_loop_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS context_loop_runs (
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          workflow TEXT NOT NULL,
          task_type TEXT NOT NULL,
          task_input_hash TEXT NOT NULL,
          triggering_event TEXT NOT NULL,
          prompt_version TEXT NOT NULL,
          guidance_version TEXT NOT NULL,
          retrieved_context_json TEXT NOT NULL DEFAULT '[]',
          context_sources_json TEXT NOT NULL DEFAULT '[]',
          approved_lessons_json TEXT NOT NULL DEFAULT '[]',
          generated_output_hash TEXT NOT NULL,
          generated_output TEXT NOT NULL,
          uncertainty_flags_json TEXT NOT NULL DEFAULT '[]',
          unsupported_claims_json TEXT NOT NULL DEFAULT '[]',
          assumptions_json TEXT NOT NULL DEFAULT '[]',
          handoff_notes TEXT NOT NULL,
          reversible_artifact_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS context_loop_review_events (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES context_loop_runs(id),
          created_at TEXT NOT NULL,
          review_outcome TEXT NOT NULL,
          original_output_hash TEXT NOT NULL,
          final_output_hash TEXT,
          final_output TEXT,
          diff_text TEXT NOT NULL,
          edit_distance_ratio REAL NOT NULL,
          reviewer_notes TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS context_loop_learning_candidates (
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          workflow TEXT NOT NULL,
          review_event_id TEXT NOT NULL REFERENCES context_loop_review_events(id),
          observed_pattern TEXT NOT NULL,
          likely_interpretation TEXT NOT NULL,
          confidence REAL NOT NULL,
          affected_workflow TEXT NOT NULL,
          proposed_change TEXT NOT NULL,
          help_reason TEXT NOT NULL,
          destination TEXT NOT NULL,
          category TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status TEXT NOT NULL DEFAULT 'candidate',
          decision_note TEXT,
          decided_by TEXT,
          decided_at TEXT,
          applied_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_context_loop_runs_workflow
          ON context_loop_runs(workflow, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_context_loop_reviews_run
          ON context_loop_review_events(run_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_context_loop_candidates_status
          ON context_loop_learning_candidates(status, created_at DESC);
        """
    )


def create_inner_loop_run(
    conn: sqlite3.Connection,
    *,
    workflow: str,
    task_type: str,
    task_input: str,
    triggering_event: str,
    prompt_version: str,
    guidance_version: str,
    retrieved_context: Sequence[Mapping[str, Any]] = (),
    context_sources: Sequence[Mapping[str, Any]] = (),
    assumptions: Sequence[str] = (),
    draft_generator: Callable[[LoopContext], str],
    handoff_notes: str = "",
    context_loop_root: Path = DEFAULT_CONTEXT_LOOP_ROOT,
) -> dict[str, Any]:
    ensure_context_loop_schema(conn)
    approved_lessons = tuple(read_approved_lessons(context_loop_root, workflow=workflow))
    loop_context = LoopContext(
        workflow=workflow,
        task_type=task_type,
        task_input=task_input,
        approved_lessons=approved_lessons,
        retrieved_context=tuple(dict(item) for item in retrieved_context),
        context_sources=tuple(dict(item) for item in context_sources),
    )
    generated_output = draft_generator(loop_context)
    unsupported_claims = detect_unsupported_commitments(generated_output, context_sources)
    uncertainty_flags = []
    if unsupported_claims:
        uncertainty_flags.append("unsupported_commitment")
    if not retrieved_context and workflow != "email_drafting":
        uncertainty_flags.append("no_retrieved_context")
    run_id = f"clr-{uuid.uuid4().hex[:12]}"
    now = _now_iso()
    reversible = {
        "artifact_kind": "draft",
        "finalization_policy": "human_review_required",
        "email_policy": "draft_only_never_send" if workflow == "email_drafting" else None,
    }
    conn.execute(
        """
        INSERT INTO context_loop_runs (
          id, created_at, workflow, task_type, task_input_hash, triggering_event,
          prompt_version, guidance_version, retrieved_context_json, context_sources_json,
          approved_lessons_json, generated_output_hash, generated_output,
          uncertainty_flags_json, unsupported_claims_json, assumptions_json,
          handoff_notes, reversible_artifact_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            now,
            workflow,
            task_type,
            _hash(task_input),
            triggering_event,
            prompt_version,
            guidance_version,
            _json(loop_context.retrieved_context),
            _json(loop_context.context_sources),
            _json(approved_lessons),
            _hash(generated_output),
            generated_output,
            _json(uncertainty_flags),
            _json(unsupported_claims),
            _json(list(assumptions)),
            handoff_notes,
            _json(reversible),
        ),
    )
    return {
        "run_id": run_id,
        "workflow": workflow,
        "generated_output": generated_output,
        "approved_lessons_read": len(approved_lessons),
        "unsupported_claims": unsupported_claims,
        "uncertainty_flags": uncertainty_flags,
        "reversible_artifact": reversible,
    }


def create_email_draft_run(
    conn: sqlite3.Connection,
    *,
    task_input: str,
    recipient: str = "",
    subject: str = "",
    context_loop_root: Path = DEFAULT_CONTEXT_LOOP_ROOT,
) -> dict[str, Any]:
    def _draft(context: LoopContext) -> str:
        lesson_text = "\n".join(context.approved_lessons)
        safety_note = (
            "\n\n[Review note: draft only. Confirm commitments, dates, pricing, scope, and "
            "relationship context before sending.]"
        )
        opener = "Hi,"
        if "warmer openings" in lesson_text.lower() or "close collaborators" in lesson_text.lower():
            opener = "Hi -"
        body = task_input.strip() or "Thanks for the note. I’ll review and follow up."
        return f"{opener}\n\n{body}{safety_note}"

    return create_inner_loop_run(
        conn,
        workflow="email_drafting",
        task_type="email_reply",
        task_input=task_input,
        triggering_event="manual_command",
        prompt_version="context-loop-email-pilot-v1",
        guidance_version="approved-lessons.md",
        retrieved_context=(
            {"source": "manual_input", "summary": "Operator-provided email task input"},
        ),
        context_sources=(
            {
                "source_type": "manual_input",
                "recipient": recipient,
                "subject": subject,
                "supports_commitments": False,
            },
        ),
        assumptions=("Email pilot is local draft-only; no Gmail/send integration is wired.",),
        draft_generator=_draft,
        handoff_notes="Create a draft only. Human must review and send manually.",
        context_loop_root=context_loop_root,
    )


def record_review_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    outcome: ReviewOutcome,
    final_output: str | None = None,
    reviewer_notes: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_context_loop_schema(conn)
    if outcome not in REVIEW_OUTCOMES:
        raise ValueError(f"Unsupported review outcome: {outcome}")
    row = conn.execute(
        "SELECT generated_output, generated_output_hash FROM context_loop_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown context loop run: {run_id}")
    original = str(row[0])
    final = final_output if final_output is not None else ""
    diff_text = _diff(original, final)
    edit_distance = 1.0 - difflib.SequenceMatcher(None, original, final).ratio()
    event_id = f"clr-review-{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO context_loop_review_events (
          id, run_id, created_at, review_outcome, original_output_hash, final_output_hash,
          final_output, diff_text, edit_distance_ratio, reviewer_notes, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            run_id,
            _now_iso(),
            outcome,
            str(row[1]),
            _hash(final) if final_output is not None else None,
            final_output,
            diff_text,
            round(edit_distance, 4),
            reviewer_notes,
            _json(dict(metadata or {})),
        ),
    )
    return {
        "review_event_id": event_id,
        "run_id": run_id,
        "outcome": outcome,
        "edit_distance_ratio": round(edit_distance, 4),
        "diff_text": diff_text,
    }


def propose_learning_candidates(
    conn: sqlite3.Connection,
    *,
    min_reviews: int = 1,
) -> dict[str, Any]:
    ensure_context_loop_schema(conn)
    rows = conn.execute(
        """
        SELECT
          review.id AS review_id,
          review.review_outcome,
          review.diff_text,
          review.edit_distance_ratio,
          review.reviewer_notes,
          review.final_output,
          run.workflow,
          run.generated_output,
          run.unsupported_claims_json,
          run.retrieved_context_json
        FROM context_loop_review_events AS review
        JOIN context_loop_runs AS run ON run.id = review.run_id
        WHERE NOT EXISTS (
          SELECT 1 FROM context_loop_learning_candidates AS candidate
          WHERE candidate.review_event_id = review.id
        )
        ORDER BY review.created_at ASC
        """
    ).fetchall()
    if len(rows) < min_reviews:
        return {"proposed_count": 0, "skipped_reason": "below_min_reviews", "candidates": []}

    candidates: list[dict[str, Any]] = []
    for row in rows:
        candidate = _candidate_from_review(row)
        if candidate is None or _matches_rejected_candidate(
            conn, str(candidate["proposed_change"])
        ):
            continue
        candidate_id = _insert_candidate(conn, candidate)
        candidates.append({"candidate_id": candidate_id, **candidate})
    return {"proposed_count": len(candidates), "candidates": candidates}


def approve_candidate(
    conn: sqlite3.Connection,
    candidate_id: str,
    *,
    actor: str = "local-user",
    note: str = "",
) -> dict[str, Any]:
    return _transition_candidate(conn, candidate_id, "approved", actor=actor, note=note)


def reject_candidate(
    conn: sqlite3.Connection,
    candidate_id: str,
    *,
    actor: str = "local-user",
    note: str = "",
    context_loop_root: Path = DEFAULT_CONTEXT_LOOP_ROOT,
) -> dict[str, Any]:
    result = _transition_candidate(conn, candidate_id, "rejected", actor=actor, note=note)
    append_rejected_lesson(context_loop_root, result, note=note)
    return result


def apply_approved_candidates(
    conn: sqlite3.Connection,
    *,
    context_loop_root: Path = DEFAULT_CONTEXT_LOOP_ROOT,
) -> dict[str, Any]:
    ensure_context_loop_schema(conn)
    rows = conn.execute(
        """
        SELECT id, workflow, proposed_change, category, destination, help_reason
        FROM context_loop_learning_candidates
        WHERE status = 'approved' AND applied_at IS NULL
        ORDER BY created_at ASC
        """
    ).fetchall()
    applied: list[dict[str, str]] = []
    now = _now_iso()
    for row in rows:
        entry = {
            "candidate_id": str(row[0]),
            "workflow": str(row[1]),
            "proposed_change": str(row[2]),
            "category": str(row[3]),
            "destination": str(row[4]),
            "help_reason": str(row[5]),
        }
        append_approved_lesson(context_loop_root, entry)
        conn.execute(
            "UPDATE context_loop_learning_candidates SET applied_at = ?, updated_at = ? WHERE id = ?",
            (now, now, str(row[0])),
        )
        applied.append(entry)
    return {
        "applied_count": len(applied),
        "approved_lessons_path": str(context_loop_root / APPROVED_LESSONS_FILE),
        "applied": applied,
    }


def context_loop_metrics(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_context_loop_schema(conn)
    run_count = conn.execute("SELECT COUNT(*) FROM context_loop_runs").fetchone()[0]
    draft_count = conn.execute(
        "SELECT COUNT(*) FROM context_loop_runs WHERE json_extract(reversible_artifact_json, '$.artifact_kind') = 'draft'"
    ).fetchone()[0]
    outcome_rows = conn.execute(
        "SELECT review_outcome, COUNT(*) FROM context_loop_review_events GROUP BY review_outcome"
    ).fetchall()
    candidate_rows = conn.execute(
        "SELECT status, COUNT(*) FROM context_loop_learning_candidates GROUP BY status"
    ).fetchall()
    avg_edit = conn.execute(
        "SELECT AVG(edit_distance_ratio) FROM context_loop_review_events"
    ).fetchone()[0]
    category_rows = conn.execute(
        "SELECT category, COUNT(*) FROM context_loop_learning_candidates GROUP BY category"
    ).fetchall()
    source_rows = conn.execute("SELECT context_sources_json FROM context_loop_runs").fetchall()
    source_counter: Counter[str] = Counter()
    for row in source_rows:
        for item in _json_loads(str(row[0]), default=[]):
            if isinstance(item, dict):
                source_counter[str(item.get("source_type") or item.get("source") or "unknown")] += 1
    return {
        "inner_loop_runs": int(run_count),
        "drafts_created": int(draft_count),
        "review_outcomes": {str(key): int(value) for key, value in outcome_rows},
        "average_edit_distance": round(float(avg_edit or 0.0), 4),
        "candidate_statuses": {str(key): int(value) for key, value in candidate_rows},
        "recurring_edit_categories": {str(key): int(value) for key, value in category_rows},
        "retrieval_sources_used": dict(source_counter),
    }


def write_metrics_report(
    conn: sqlite3.Connection,
    *,
    context_loop_root: Path = DEFAULT_CONTEXT_LOOP_ROOT,
) -> Path:
    metrics = context_loop_metrics(conn)
    context_loop_root.mkdir(parents=True, exist_ok=True)
    path = context_loop_root / "metrics-summary.md"
    lines = [
        "# Context Loop Metrics Summary",
        "",
        f"- Inner-loop runs: {metrics['inner_loop_runs']}",
        f"- Drafts created: {metrics['drafts_created']}",
        f"- Average edit distance: {metrics['average_edit_distance']}",
        f"- Review outcomes: `{json.dumps(metrics['review_outcomes'], sort_keys=True)}`",
        f"- Candidate statuses: `{json.dumps(metrics['candidate_statuses'], sort_keys=True)}`",
        f"- Recurring edit categories: `{json.dumps(metrics['recurring_edit_categories'], sort_keys=True)}`",
        f"- Retrieval sources used: `{json.dumps(metrics['retrieval_sources_used'], sort_keys=True)}`",
        "",
        "Use this report to find repeated missing-context failures, not to claim quality from volume.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def read_approved_lessons(context_loop_root: Path, *, workflow: str) -> list[str]:
    path = context_loop_root / APPROVED_LESSONS_FILE
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lessons: list[str] = []
    in_workflow_section = False
    target_heading = _workflow_heading(workflow)
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            in_workflow_section = line[3:].strip().lower() == target_heading.lower()
            continue
        if in_workflow_section and line.strip().startswith("- "):
            lessons.append(line.strip()[2:])
    return lessons


def detect_unsupported_commitments(
    text: str,
    context_sources: Sequence[Mapping[str, Any]],
) -> list[str]:
    has_support = any(bool(source.get("supports_commitments")) for source in context_sources)
    if has_support:
        return []
    patterns = (
        r"\bI will\b",
        r"\bwe will\b",
        r"\bI can\b.*\b(by|tomorrow|today|next week|this week)\b",
        r"\bwe can\b.*\b(by|tomorrow|today|next week|this week)\b",
        r"\bdeadline\b",
        r"\bdeliver\b.*\b(by|tomorrow|today|next week|this week)\b",
        r"\bavailable\b.*\b(at|tomorrow|today|next week|this week)\b",
        r"\bmeet\b.*\b(at|tomorrow|today|next week|this week)\b",
    )
    claims = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            claims.append(pattern)
    return claims


def append_approved_lesson(context_loop_root: Path, entry: Mapping[str, Any]) -> None:
    path = context_loop_root / APPROVED_LESSONS_FILE
    context_loop_root.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Approved Context Loop Lessons\n\n", encoding="utf-8")
    workflow = str(entry["workflow"])
    heading = _workflow_heading(workflow)
    line = (
        f"- [{entry['category']} -> {entry['destination']}] {entry['proposed_change']} "
        f"(source: {entry['candidate_id']})"
    )
    text = path.read_text(encoding="utf-8")
    if f"## {heading}" not in text:
        text = text.rstrip() + f"\n\n## {heading}\n\n{line}\n"
    else:
        text = text.rstrip() + f"\n{line}\n"
    path.write_text(text, encoding="utf-8")


def append_rejected_lesson(
    context_loop_root: Path,
    candidate: Mapping[str, Any],
    *,
    note: str,
) -> None:
    path = context_loop_root / REJECTED_LESSONS_FILE
    context_loop_root.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("# Rejected Context Loop Lessons\n\n", encoding="utf-8")
    line = (
        f"- {datetime.now(UTC).date()}: `{candidate['proposed_change']}` rejected for "
        f"`{candidate['workflow']}`. Reason: {note or 'No reason recorded.'} "
        f"Related example: {candidate['candidate_id']}."
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _candidate_from_review(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any] | None:
    (
        review_id,
        outcome,
        diff_text,
        edit_distance,
        reviewer_notes,
        final_output,
        workflow,
        generated_output,
        unsupported_claims_json,
        retrieved_context_json,
    ) = row
    unsupported_claims = _json_loads(str(unsupported_claims_json), default=[])
    retrieved_context = _json_loads(str(retrieved_context_json), default=[])
    category: LearningCategory
    destination: LessonDestination
    proposed_change: str
    interpretation: str

    if str(outcome) == "human_judgment_only":
        category = "human_judgment_only"
        destination = "human_handoff_rule"
        proposed_change = (
            "Escalate similar cases to human-only judgment instead of drafting final language."
        )
        interpretation = "The reviewer marked this as judgment that should not be automated."
    elif unsupported_claims:
        category = "unsupported_commitment"
        destination = "safety_check_policy"
        proposed_change = "Flag commitments to deadlines, meetings, deliverables, scope, or availability unless a trusted source supports them."
        interpretation = "The draft included commitment-like language without source support."
    elif str(outcome) in {"deleted", "rejected", "replaced_manually"}:
        category = "task_misunderstood"
        destination = "human_handoff_rule"
        proposed_change = "When review deletes or replaces the draft, ask for task clarification before proposing a durable style or memory rule."
        interpretation = (
            "The review outcome is a weak signal that the task may have been misunderstood."
        )
    elif not retrieved_context and float(edit_distance) > 0.25:
        category = "incomplete_retrieval"
        destination = "retrieval_policy"
        proposed_change = "For edited outputs with no retrieved context, retrieve at least one task-relevant source before drafting."
        interpretation = "A large edit happened after the inner loop used no retrieved context."
    elif _looks_like_formality_edit(str(generated_output), str(final_output or ""), str(diff_text)):
        category = "style_preference"
        destination = "writing_guidance"
        proposed_change = "For close collaborators or informal prior threads, avoid overly formal openings unless the thread is formal."
        interpretation = "The human review softened or removed formal phrasing."
    elif str(reviewer_notes).strip():
        category = "missing_fact"
        destination = "project_memory"
        proposed_change = str(reviewer_notes).strip()
        interpretation = "Reviewer notes supplied a possible reusable missing fact or preference."
    else:
        category = "one_off_exception"
        destination = "no_durable_memory"
        proposed_change = "Treat this review as one-off evidence unless the same pattern recurs."
        interpretation = "The edit does not justify durable memory on its own."

    if destination == "no_durable_memory":
        confidence = 0.3
    elif category in {"unsupported_commitment", "human_judgment_only"}:
        confidence = 0.8
    else:
        confidence = 0.6
    return {
        "workflow": str(workflow),
        "review_event_id": str(review_id),
        "observed_pattern": _summarize_diff(str(diff_text), str(outcome)),
        "likely_interpretation": interpretation,
        "confidence": confidence,
        "affected_workflow": str(workflow),
        "proposed_change": proposed_change,
        "help_reason": "Feeds reviewed evidence back into future inner-loop context without automatic promotion.",
        "destination": destination,
        "category": category,
        "evidence": [{"type": "context_loop_review_event", "id": str(review_id)}],
    }


def _insert_candidate(conn: sqlite3.Connection, candidate: Mapping[str, Any]) -> str:
    candidate_id = f"clc-{uuid.uuid4().hex[:12]}"
    now = _now_iso()
    conn.execute(
        """
        INSERT INTO context_loop_learning_candidates (
          id, created_at, updated_at, workflow, review_event_id, observed_pattern,
          likely_interpretation, confidence, affected_workflow, proposed_change,
          help_reason, destination, category, evidence_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate')
        """,
        (
            candidate_id,
            now,
            now,
            str(candidate["workflow"]),
            str(candidate["review_event_id"]),
            str(candidate["observed_pattern"]),
            str(candidate["likely_interpretation"]),
            float(candidate["confidence"]),
            str(candidate["affected_workflow"]),
            str(candidate["proposed_change"]),
            str(candidate["help_reason"]),
            str(candidate["destination"]),
            str(candidate["category"]),
            _json(candidate["evidence"]),
        ),
    )
    return candidate_id


def _transition_candidate(
    conn: sqlite3.Connection,
    candidate_id: str,
    status: Literal["approved", "rejected"],
    *,
    actor: str,
    note: str,
) -> dict[str, Any]:
    ensure_context_loop_schema(conn)
    row = conn.execute(
        """
        SELECT id, workflow, proposed_change, category, destination, help_reason
        FROM context_loop_learning_candidates
        WHERE id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown context-loop candidate: {candidate_id}")
    now = _now_iso()
    conn.execute(
        """
        UPDATE context_loop_learning_candidates
        SET status = ?, updated_at = ?, decision_note = ?, decided_by = ?, decided_at = ?
        WHERE id = ?
        """,
        (status, now, note, actor, now, candidate_id),
    )
    return {
        "candidate_id": str(row[0]),
        "workflow": str(row[1]),
        "proposed_change": str(row[2]),
        "category": str(row[3]),
        "destination": str(row[4]),
        "help_reason": str(row[5]),
        "status": status,
    }


def _matches_rejected_candidate(conn: sqlite3.Connection, proposed_change: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM context_loop_learning_candidates
        WHERE status = 'rejected' AND proposed_change = ?
        LIMIT 1
        """,
        (proposed_change,),
    ).fetchone()
    return row is not None


def _looks_like_formality_edit(original: str, final: str, diff_text: str) -> bool:
    lowered = f"{original}\n{final}\n{diff_text}".lower()
    formal_terms = ("dear", "sincerely", "regards", "i hope this message finds you well")
    return any(term in lowered for term in formal_terms)


def _summarize_diff(diff_text: str, outcome: str) -> str:
    changed = [
        line
        for line in diff_text.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    if not changed:
        return f"Review outcome `{outcome}` with no textual final-output diff."
    return " ".join(changed[:4])[:500]


def _diff(original: str, final: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            original.splitlines(),
            final.splitlines(),
            fromfile="ai-output",
            tofile="human-final",
            lineterm="",
        )
    )


def _workflow_heading(workflow: str) -> str:
    return workflow.replace("_", " ").replace("-", " ").title()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _json_loads(text: str, *, default: Any) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
