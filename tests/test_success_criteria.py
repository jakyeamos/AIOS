from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import standards_health, success_criteria  # noqa: E402


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
    assert "truth-file-consistency" not in criterion_ids
    assert "workflow-state-integrity" in criterion_ids
    assert "observability" in criterion_ids
    assert "architecture-boundary" in criterion_ids
    assert "agent-claim-verification" in criterion_ids
    assert "simplicity" in criterion_ids


def test_quality_gate_registry_contains_expected_new_gates() -> None:
    registry = success_criteria.load_registry()
    criterion_ids = {item.id for item in registry}

    assert {
        "complexity-budget",
        "supply-chain-review",
        "architecture-boundary",
        "thin-display",
        "test-quality",
        "data-integrity",
        "api-contract",
        "performance-budget",
        "accessibility",
        "resilience",
        "product-alignment",
        "simplicity",
        "agent-claim-verification",
    } <= criterion_ids

    missing_paths = [
        item.path for item in registry if item.path and not (ROOT / item.path).exists()
    ]
    assert missing_paths == []


def test_ui_diff_routes_to_display_accessibility_and_performance_gates() -> None:
    result = success_criteria.resolve_task_standards(
        project_id=None,
        project_name=None,
        objective="Implement dashboard component changes",
        prompt_classifications=["implement"],
        changed_files=["aios-ui/components/query/GroundedQueryStudio.tsx"],
        skills=[],
    )

    criterion_ids = {item["id"] for item in result["criteria"]}
    assert {
        "thin-display",
        "accessibility",
        "performance-budget",
        "product-alignment",
    } <= criterion_ids


def test_data_and_api_diffs_route_to_integrity_contract_and_resilience_gates() -> None:
    result = success_criteria.resolve_task_standards(
        project_id=None,
        project_name=None,
        objective="Update database schema and API response contract",
        prompt_classifications=["implement"],
        changed_files=["schema.sql", "aios-ui/server/routers/workflows.ts"],
        skills=[],
    )

    criterion_ids = {item["id"] for item in result["criteria"]}
    assert {"data-integrity", "api-contract", "resilience"} <= criterion_ids


def test_dependency_diff_routes_to_supply_chain_gate() -> None:
    result = success_criteria.resolve_task_standards(
        project_id=None,
        project_name=None,
        objective="Add package dependency",
        prompt_classifications=["implement"],
        changed_files=["aios-ui/package.json", "aios-ui/pnpm-lock.yaml"],
        skills=[],
    )

    criterion_ids = {item["id"] for item in result["criteria"]}
    assert "supply-chain-review" in criterion_ids


def test_supply_chain_blocks_package_manager_drift() -> None:
    context = success_criteria.infer_context(
        objective="Add package dependency",
        prompt_classifications=["implement"],
        changed_files=["aios-ui/package-lock.json"],
        skills=[],
    )
    criterion = next(
        item for item in success_criteria.load_registry() if item.id == "supply-chain-review"
    )

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "blocker"
    assert "Package-manager drift" in finding.summary


def test_critical_behavior_without_evidence_blocks_test_quality() -> None:
    context = success_criteria.infer_context(
        objective="Update API authorization behavior",
        prompt_classifications=["implement"],
        changed_files=["aios-ui/server/routers/auth.ts"],
        skills=[],
    )
    criterion = next(item for item in success_criteria.load_registry() if item.id == "test-quality")

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "blocker"
    assert "lacks focused tests" in finding.summary


def test_resolve_task_standards_merges_criteria_and_standards() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_runtime_tables(conn)
    standards_health.ensure_standards_health_schema(conn)
    conn.execute(
        """
        INSERT INTO project_standards_profiles (
            project_id, profile_id, attached_version, latest_version, migration_mode, updated_at
        )
        VALUES ('p1', 'aios-core', '2026.05.0', '2026.05.0', 'current', '2026-05-23T00:00:00Z')
        """
    )

    result = success_criteria.resolve_task_standards(
        conn=conn,
        project_id="p1",
        project_name="AIOS",
        objective="Implement workflow orchestration updates",
        prompt_classifications=["implement"],
        changed_files=["services/workflow_orchestration.py"],
        skills=[],
        workflow_key="implementation-delivery",
    )

    assert result["resolution_status"] == "ok"
    assert result["workflow_key"] == "implementation-delivery"
    assert {row["id"] for row in result["criteria"]} >= {
        "execution-first-verification",
        "workflow-state-integrity",
    }
    assert {row["standard_id"] for row in result["standards"]} >= {
        "workflow_agent_control.explicit_handshake",
        "testing.trust_signal",
    }
    assert result["execution_first_triggers"]


def test_resolve_task_standards_warns_when_no_profile_attached() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_runtime_tables(conn)
    standards_health.ensure_standards_health_schema(conn)

    result = success_criteria.resolve_task_standards(
        conn=conn,
        project_id="p1",
        project_name="AIOS",
        objective="Implement workflow orchestration updates",
        prompt_classifications=["implement"],
    )

    assert result["resolution_status"] == "no_profile_attached"
    assert result["standards"] == []
    assert result["criteria"]


def test_resolve_task_standards_filters_standards_by_applicability(monkeypatch) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_runtime_tables(conn)
    standards_health.ensure_standards_health_schema(conn)
    conn.execute(
        """
        INSERT INTO project_standards_profiles (
            project_id, profile_id, attached_version, latest_version, migration_mode, updated_at
        )
        VALUES ('p1', 'aios-core', '2026.05.0', '2026.05.0', 'current', '2026-05-23T00:00:00Z')
        """
    )
    matching = SimpleNamespace(
        id="matching.standard",
        profile_id="aios-core",
        title="Matching Standard",
        domain="workflow",
        weight=1.0,
        severity_if_missing=3,
        related_criteria=(),
        applicability={"project_pattern": "AIOS"},
    )
    excluded = SimpleNamespace(
        id="excluded.standard",
        profile_id="aios-core",
        title="Excluded Standard",
        domain="workflow",
        weight=1.0,
        severity_if_missing=3,
        related_criteria=(),
        applicability={"project_pattern": "other-project"},
    )
    monkeypatch.setattr(
        standards_health,
        "load_registry",
        lambda: ({"id": "aios-core", "version": "2026.05.0"}, [matching, excluded]),
    )

    result = success_criteria.resolve_task_standards(
        conn=conn,
        project_id="p1",
        project_name="AIOS",
        objective="Implement workflow orchestration updates",
        prompt_classifications=["implement"],
    )

    assert [row["standard_id"] for row in result["standards"]] == ["matching.standard"]


def test_resolve_task_standards_propagates_execution_first_triggers() -> None:
    result = success_criteria.resolve_task_standards(
        project_id=None,
        project_name=None,
        objective="Debug inconsistent workflow state",
        prompt_classifications=["debug"],
        changed_files=["services/workflow_orchestration.py"],
        skills=[],
    )

    assert "core/shared logic modification" in result["execution_first_triggers"]
    assert "debugging inconsistent behavior" in result["execution_first_triggers"]


def test_resolve_task_standards_signature_accepts_packet_inputs() -> None:
    result = success_criteria.resolve_task_standards(
        project_id=None,
        project_name=None,
        objective=None,
        prompt_classifications=None,
        changed_files=None,
        skills=None,
        workflow_key=None,
    )

    assert result["resolution_status"] == "ok"
    assert isinstance(result["criteria"], list)


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


def test_execution_first_skips_pure_doc_changes() -> None:
    context = success_criteria.infer_context(
        objective="Update service docs",
        prompt_classifications=["implement"],
        changed_files=["services/foo/README.md"],
        skills=[],
    )
    context["execution_evidence"] = []
    criterion = next(
        item
        for item in success_criteria.load_registry()
        if item.id == "execution-first-verification"
    )

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "pass"
    assert finding.metadata["triggers"] == []


def test_git_worktree_cleanliness_blocks_dirty_session_close() -> None:
    context = success_criteria.infer_context(
        objective="Implement service change",
        prompt_classifications=["implement"],
        changed_files=["services/example.py"],
        skills=[],
    )
    context["trigger_kind"] = "session_close"
    context["git_status_entries"] = [" M services/example.py", "?? tests/test_example.py"]
    criterion = next(
        item for item in success_criteria.load_registry() if item.id == "git-worktree-cleanliness"
    )

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "blocker"
    assert "uncommitted git changes" in finding.summary
    assert finding.metadata["dirty_entry_count"] == 2


def test_git_worktree_cleanliness_passes_clean_session_close() -> None:
    context = success_criteria.infer_context(
        objective="Explain code",
        prompt_classifications=[],
        changed_files=[],
        skills=[],
    )
    context["trigger_kind"] = "session_close"
    context["git_status_entries"] = []
    criterion = next(
        item for item in success_criteria.load_registry() if item.id == "git-worktree-cleanliness"
    )

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "pass"
    assert "clean" in finding.summary


def test_execution_first_still_fires_on_code_under_services() -> None:
    context = success_criteria.infer_context(
        objective="Update service behavior",
        prompt_classifications=["implement"],
        changed_files=["services/foo.py"],
        skills=[],
    )
    context["execution_evidence"] = []
    criterion = next(
        item
        for item in success_criteria.load_registry()
        if item.id == "execution-first-verification"
    )

    finding = success_criteria.evaluate_criterion(criterion, context)

    assert finding.level == "blocker"
    assert "core/shared logic modification" in finding.metadata["triggers"]


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
    assert all(row[0] != "truth-file-consistency" for row in finding_rows)


def test_stage_findings_table_exists_after_ensure_schema() -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_runtime_tables(conn)
    success_criteria.ensure_success_criteria_schema(conn)

    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(success_criteria_stage_findings)").fetchall()
    }

    assert {
        "id",
        "run_id",
        "stage_key",
        "stage_kind",
        "criterion_id",
        "criterion_title",
        "criterion_scope",
        "level",
        "summary",
        "evidence_json",
        "metadata_json",
        "resolution_status",
        "resolution_actor",
        "resolution_rationale",
        "resolution_evidence_json",
        "resolved_at",
        "created_at",
    } <= columns


def test_evaluate_stage_findings_only_fires_for_applicable_criteria() -> None:
    criterion = success_criteria.CriterionRecord(
        id="testing-trust",
        title="Testing Trust",
        scope="global",
        blocking=False,
        applies_when={},
        path="",
        related=[],
        evaluation_method="heuristic",
        stage_applicability=("validate",),
    )
    context = success_criteria.infer_context(
        objective="Implement service change",
        prompt_classifications=["implement"],
        changed_files=["services/example.py"],
        skills=[],
    )

    skipped = success_criteria.evaluate_stage_findings(
        criteria=[criterion],
        context=context,
        stage_key="parse",
        stage_kind="parse_request",
        run_state={},
    )
    evaluated = success_criteria.evaluate_stage_findings(
        criteria=[criterion],
        context=context,
        stage_key="validate",
        stage_kind="validate",
        run_state={},
    )

    assert skipped == []
    assert len(evaluated) == 1
    assert evaluated[0]["criterion_id"] == "testing-trust"


def test_evaluate_stage_findings_produces_finding_records() -> None:
    criterion = success_criteria.CriterionRecord(
        id="testing-trust",
        title="Testing Trust",
        scope="global",
        blocking=True,
        applies_when={},
        path="",
        related=[],
        evaluation_method="heuristic",
    )
    context = success_criteria.infer_context(
        objective="Implement service change",
        prompt_classifications=["implement"],
        changed_files=["services/example.py"],
        skills=[],
    )

    findings = success_criteria.evaluate_stage_findings(
        criteria=[criterion],
        context=context,
        stage_key="validate",
        stage_kind="validate",
        run_state={},
    )

    assert findings[0]["criterion_id"] == "testing-trust"
    assert findings[0]["level"] == "blocker"
    assert findings[0]["evidence"] == ["services/example.py"]


def test_persist_stage_findings_writes_rows_and_json_artifact(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_runtime_tables(conn)
    finding = {
        "criterion_id": "testing-trust",
        "criterion_title": "Testing Trust",
        "criterion_scope": "global",
        "level": "warning",
        "summary": "Missing tests.",
        "evidence": ["services/example.py"],
        "metadata": {"code_changes": 1},
    }

    result = success_criteria.persist_stage_findings(
        conn,
        run_id="run-1",
        stage_key="validate",
        stage_kind="validate",
        findings=[finding],
        artifact_root=tmp_path,
    )

    rows = conn.execute(
        "SELECT id, criterion_id, level FROM success_criteria_stage_findings"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] in result["finding_ids"]
    assert rows[0][1:] == ("testing-trust", "warning")
    artifact_path = Path(str(result["artifact_path"]))
    assert artifact_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["stage_key"] == "validate"
    assert payload["findings"][0]["summary"] == "Missing tests."


def test_persist_stage_findings_empty_list_is_noop(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_minimal_runtime_tables(conn)

    result = success_criteria.persist_stage_findings(
        conn,
        run_id="run-1",
        stage_key="validate",
        stage_kind="validate",
        findings=[],
        artifact_root=tmp_path,
    )

    assert result["finding_ids"] == []
    assert result["artifact_path"] is None
    assert list(tmp_path.iterdir()) == []
