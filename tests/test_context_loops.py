from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.context_loops import (  # noqa: E402
    LoopContext,
    apply_approved_candidates,
    approve_candidate,
    context_loop_metrics,
    create_email_draft_run,
    create_inner_loop_run,
    detect_unsupported_commitments,
    ensure_context_loop_schema,
    propose_learning_candidates,
    read_approved_lessons,
    record_review_event,
    reject_candidate,
)


def test_inner_loop_reads_approved_lessons_before_drafting(tmp_path: Path) -> None:
    context_root = tmp_path / "context-loops"
    context_root.mkdir()
    (context_root / "approved-lessons.md").write_text(
        "# Approved Context Loop Lessons\n\n"
        "## Email Drafting\n\n"
        "- Avoid unsupported deadline commitments.\n",
        encoding="utf-8",
    )
    conn = sqlite3.connect(":memory:")
    seen_lessons: list[str] = []

    def draft(context: LoopContext) -> str:
        seen_lessons.extend(context.approved_lessons)
        return "I will send it tomorrow."

    result = create_inner_loop_run(
        conn,
        workflow="email_drafting",
        task_type="email_reply",
        task_input="Reply to Sam",
        triggering_event="manual_test",
        prompt_version="test-v1",
        guidance_version="approved-lessons.md",
        draft_generator=draft,
        context_loop_root=context_root,
    )

    assert seen_lessons == ["Avoid unsupported deadline commitments."]
    assert result["approved_lessons_read"] == 1
    assert result["unsupported_claims"]
    row = conn.execute("SELECT approved_lessons_json FROM context_loop_runs").fetchone()
    assert "Avoid unsupported deadline commitments" in row[0]


def test_email_pilot_creates_draft_only_and_never_sends(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")

    result = create_email_draft_run(
        conn,
        task_input="Thanks. I can deliver by tomorrow.",
        recipient="sam@example.com",
        subject="Update",
        context_loop_root=tmp_path,
    )

    assert result["workflow"] == "email_drafting"
    assert result["reversible_artifact"]["email_policy"] == "draft_only_never_send"
    assert "Review note: draft only" in result["generated_output"]
    assert result["unsupported_claims"]


def test_outer_loop_proposes_candidate_without_automatic_memory_promotion(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    run = create_inner_loop_run(
        conn,
        workflow="email_drafting",
        task_type="email_reply",
        task_input="Reply",
        triggering_event="manual_test",
        prompt_version="test-v1",
        guidance_version="approved-lessons.md",
        context_sources=[{"source_type": "manual_input", "supports_commitments": False}],
        draft_generator=lambda _context: "I will deliver it tomorrow.",
        context_loop_root=tmp_path,
    )
    review = record_review_event(
        conn,
        run_id=str(run["run_id"]),
        outcome="edited_and_sent",
        final_output="I will review it and follow up.",
    )

    proposed = propose_learning_candidates(conn)

    assert proposed["proposed_count"] == 1
    candidate = proposed["candidates"][0]
    assert candidate["category"] == "unsupported_commitment"
    assert candidate["destination"] == "safety_check_policy"
    assert candidate["evidence"] == [
        {"type": "context_loop_review_event", "id": review["review_event_id"]}
    ]
    assert not (tmp_path / "approved-lessons.md").exists()


def test_approval_requires_apply_step_before_lesson_is_read(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    run = create_inner_loop_run(
        conn,
        workflow="email_drafting",
        task_type="email_reply",
        task_input="Reply",
        triggering_event="manual_test",
        prompt_version="test-v1",
        guidance_version="approved-lessons.md",
        context_sources=[{"source_type": "manual_input", "supports_commitments": False}],
        draft_generator=lambda _context: "I will deliver it tomorrow.",
        context_loop_root=tmp_path,
    )
    record_review_event(
        conn,
        run_id=str(run["run_id"]),
        outcome="edited_and_sent",
        final_output="I will review it and follow up.",
    )
    candidate_id = str(propose_learning_candidates(conn)["candidates"][0]["candidate_id"])

    approval = approve_candidate(conn, candidate_id, actor="tester")

    assert approval["status"] == "approved"
    assert read_approved_lessons(tmp_path, workflow="email_drafting") == []
    applied = apply_approved_candidates(conn, context_loop_root=tmp_path)
    assert applied["applied_count"] == 1
    lessons = read_approved_lessons(tmp_path, workflow="email_drafting")
    assert any("Flag commitments" in lesson for lesson in lessons)


def test_rejected_lesson_memory_suppresses_repeated_candidate(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")

    def make_review() -> None:
        run = create_inner_loop_run(
            conn,
            workflow="email_drafting",
            task_type="email_reply",
            task_input="Reply",
            triggering_event="manual_test",
            prompt_version="test-v1",
            guidance_version="approved-lessons.md",
            context_sources=[{"source_type": "manual_input", "supports_commitments": False}],
            draft_generator=lambda _context: "I will deliver it tomorrow.",
            context_loop_root=tmp_path,
        )
        record_review_event(
            conn,
            run_id=str(run["run_id"]),
            outcome="edited_and_sent",
            final_output="I will review it and follow up.",
        )

    make_review()
    first = propose_learning_candidates(conn)
    candidate_id = str(first["candidates"][0]["candidate_id"])
    reject_candidate(
        conn, candidate_id, note="Already handled elsewhere", context_loop_root=tmp_path
    )
    make_review()

    second = propose_learning_candidates(conn)

    assert second["proposed_count"] == 0
    assert "Already handled elsewhere" in (tmp_path / "rejected-lessons.md").read_text(
        encoding="utf-8"
    )


def test_metrics_capture_review_outcomes_candidates_and_sources(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    run = create_inner_loop_run(
        conn,
        workflow="briefs",
        task_type="status_brief",
        task_input="Summarize",
        triggering_event="manual_test",
        prompt_version="test-v1",
        guidance_version="approved-lessons.md",
        retrieved_context=[{"source": "PROJECT.md", "summary": "Project truth"}],
        context_sources=[{"source_type": "project_truth", "path": "PROJECT.md"}],
        draft_generator=lambda _context: "Dear team,\n\nHere is the status.",
        context_loop_root=tmp_path,
    )
    record_review_event(
        conn,
        run_id=str(run["run_id"]),
        outcome="edited_and_sent",
        final_output="Team,\n\nHere is the status.",
    )
    propose_learning_candidates(conn)

    metrics = context_loop_metrics(conn)

    assert metrics["inner_loop_runs"] == 1
    assert metrics["drafts_created"] == 1
    assert metrics["review_outcomes"]["edited_and_sent"] == 1
    assert metrics["candidate_statuses"]["candidate"] == 1
    assert metrics["retrieval_sources_used"]["project_truth"] == 1


def test_unsupported_commitment_detection_respects_supporting_sources() -> None:
    assert detect_unsupported_commitments("I can meet tomorrow.", []) != []
    assert (
        detect_unsupported_commitments(
            "I can meet tomorrow.",
            [{"source_type": "calendar", "supports_commitments": True}],
        )
        == []
    )


def test_cli_context_loop_smoke(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    context_root = tmp_path / "context-loops"
    sqlite3.connect(db_path).close()

    from services.aios_cli import run_cli  # noqa: PLC0415

    with patch(
        "sys.argv",
        [
            "aios",
            "--db",
            str(db_path),
            "context-loops",
            "email-draft",
            "--task-input",
            "I can deliver by tomorrow.",
            "--context-root",
            str(context_root),
            "--json",
        ],
    ):
        assert run_cli() == 0

    conn = sqlite3.connect(db_path)
    ensure_context_loop_schema(conn)
    assert conn.execute("SELECT COUNT(*) FROM context_loop_runs").fetchone()[0] == 1
