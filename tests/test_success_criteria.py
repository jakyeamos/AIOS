from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import success_criteria  # noqa: E402


def _seed_minimal_runtime_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE orchestration_runs (id TEXT PRIMARY KEY);
        CREATE TABLE sessions (id TEXT PRIMARY KEY);
        CREATE TABLE briefing_packets (id TEXT PRIMARY KEY);
        """
    )
    conn.execute("INSERT INTO projects (id, name) VALUES ('p1', 'AIOS')")
    conn.execute("INSERT INTO orchestration_runs (id) VALUES ('run-1')")
    conn.execute("INSERT INTO sessions (id) VALUES ('session-1')")
    conn.execute("INSERT INTO briefing_packets (id) VALUES ('packet-1')")


def test_preview_applicable_criteria_includes_project_and_domain_rules() -> None:
    preview = success_criteria.preview_applicable_criteria(
        project_id="p1",
        project_name="AIOS",
        objective="Implement workflow orchestration and observability updates",
        prompt_classifications=["implement"],
    )
    criterion_ids = {item["id"] for item in preview["criteria"]}
    assert "code-simplicity" in criterion_ids
    assert "execution-first-verification" in criterion_ids
    assert "truth-file-consistency" in criterion_ids
    assert "workflow-state-integrity" in criterion_ids
    assert "observability" in criterion_ids


def test_security_review_warns_without_explicit_security_focus() -> None:
    context = success_criteria.infer_context(
        objective="Refactor login flow",
        prompt_classifications=["refactor"],
        changed_files=["services/auth/token_manager.py"],
        skills=[],
    )
    registry = success_criteria.load_registry()
    security_criterion = next(item for item in registry if item.id == "security-review")

    finding = success_criteria.evaluate_criterion(security_criterion, context)
    assert finding.level == "blocker"
    assert "Sensitive paths changed" in finding.summary


def test_execution_first_blocks_triggered_change_without_execution_evidence() -> None:
    context = success_criteria.infer_context(
        objective="Debug inconsistent workflow state",
        prompt_classifications=["debug"],
        changed_files=["services/workflow_orchestration.py"],
        skills=[],
    )
    context["execution_evidence"] = []
    registry = success_criteria.load_registry()
    criterion = next(item for item in registry if item.id == "execution-first-verification")

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "blocker"
    assert "no direct execution evidence" in finding.summary
    assert "debugging inconsistent behavior" in finding.metadata["triggers"]


def test_execution_first_passes_triggered_change_with_execution_evidence() -> None:
    context = success_criteria.infer_context(
        objective="Update workflow state persistence",
        prompt_classifications=["implement"],
        changed_files=["services/workflow_orchestration.py"],
        skills=[],
    )
    context["execution_evidence"] = ["command: uv run pytest tests/test_workflow.py"]
    registry = success_criteria.load_registry()
    criterion = next(item for item in registry if item.id == "execution-first-verification")

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "pass"
    assert finding.evidence == ["command: uv run pytest tests/test_workflow.py"]


def test_evaluate_and_record_persists_rows_and_artifact(tmp_path: Path) -> None:
    db_path = tmp_path / "criteria.db"
    conn = sqlite3.connect(db_path)
    _seed_minimal_runtime_tables(conn)

    original_artifacts_dir = success_criteria.ARTIFACTS_DIR
    success_criteria.ARTIFACTS_DIR = tmp_path / "artifacts"
    try:
        result = success_criteria.evaluate_and_record(
            conn,
            project_id="p1",
            project_name="AIOS",
            run_id="run-1",
            session_id="session-1",
            packet_id="packet-1",
            objective="Implement runtime hook change",
            task_id="task-1",
            trigger_kind="session_close",
            cwd=str(tmp_path),
            prompt_classifications=["implement"],
            changed_files=["services/new_feature.py"],
            skills=[],
            accepted_tradeoffs=["none"],
        )
        conn.commit()
    finally:
        success_criteria.ARTIFACTS_DIR = original_artifacts_dir

    eval_row = conn.execute(
        """
        SELECT id, blocker_count, artifact_path
        FROM success_criteria_evaluations
        WHERE id = ?
        """,
        (result["evaluation_id"],),
    ).fetchone()
    assert eval_row is not None
    assert eval_row[1] >= 1
    artifact_path = Path(str(eval_row[2]))
    assert artifact_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["id"] == result["evaluation_id"]
    assert payload["files_changed"] == ["services/new_feature.py"]

    finding_rows = conn.execute(
        """
        SELECT criterion_id, level
        FROM success_criteria_findings
        WHERE evaluation_id = ?
        """,
        (result["evaluation_id"],),
    ).fetchall()
    conn.close()
    assert len(finding_rows) >= 1
    assert any(row[0] == "truth-file-consistency" and row[1] == "blocker" for row in finding_rows)
