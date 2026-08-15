from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from services import standards_health  # noqa: E402
from services.agentize import (  # noqa: E402
    AgentizedTaskPacket,
    TaskClassification,
    agentize_request,
    ensure_agentize_schema,
    record_agentize_evaluation,
)
from services.success_criteria import resolve_task_standards  # noqa: E402
from services.workflow_orchestration import (  # noqa: E402
    WorkflowExecutionContext,
    execute_workflow,
    load_skill_registry,
    load_workflow_registry,
    validate_workflow_bindings,
)


def _fake_recommendation(asset_key: str) -> Any:
    from services.asset_recommendation import AssetRecommendation, AssetUsageEvidence

    return AssetRecommendation(
        asset_kind="skill",
        asset_key=asset_key,
        lifecycle_state="active",
        rationale="active asset; success_rate=1.00 over sample_size=2; per_workflow_top=agentize",
        evidence=AssetUsageEvidence(
            "skill",
            asset_key,
            2,
            2,
            0,
            None,
            {"agentize": {"used": 2, "succeeded": 2, "failed": 0}},
            {},
        ),
        rank=1,
    )


def test_basic_transformation_returns_structured_packet() -> None:
    packet = agentize_request("Clean up this repo and make the workflow docs easier to trust.")

    assert isinstance(packet, AgentizedTaskPacket)
    assert (
        packet.original_request == "Clean up this repo and make the workflow docs easier to trust."
    )
    assert (
        packet.normalized_objective
        == "Clean up this repo and make the workflow docs easier to trust."
    )
    assert packet.task_classifications
    assert packet.execution_mode.reasoning
    assert packet.output_contract.summary_required is True
    assert "original_request" in packet.to_json()


def test_task_classification_covers_core_request_families() -> None:
    cases = {
        "audit this feature for security risk": TaskClassification.AUDIT,
        "implement this PRD": TaskClassification.IMPLEMENT,
        "audit and then fix the failing route": TaskClassification.DEBUG,
        "make this UI better": TaskClassification.UI_UX_IMPROVEMENT,
        "write tests for the parser": TaskClassification.TEST_GENERATION,
        "refactor this without breaking behavior": TaskClassification.REFACTOR,
        "research this library": TaskClassification.RESEARCH,
        "turn this idea into a plan": TaskClassification.PLANNING,
    }

    for request, expected in cases.items():
        packet = agentize_request(request)
        assert expected in packet.task_classifications


def test_execution_mode_selection_uses_request_risk_and_complexity() -> None:
    assert (
        agentize_request("rename this one variable").execution_mode.mode == "single_agent_execution"
    )
    assert (
        agentize_request(
            "audit the whole repo architecture and implement the migration"
        ).execution_mode.mode
        == "sub_agent_driven_development"
    )
    assert (
        agentize_request(
            "change the authentication architecture and security policy"
        ).execution_mode.mode
        == "approval_gated_mode"
    )
    assert (
        agentize_request("write tests first for this parser feature").execution_mode.mode
        == "tdd_first_implementation"
    )


def test_context_plan_is_targeted_and_includes_workflow_and_success_criteria_when_relevant() -> (
    None
):
    packet = agentize_request("implement this AIOS workflow change with project context updates")
    paths = [item.path for item in packet.required_context]

    assert "AGENTS.md" in paths
    assert "config/workflows/registry.json" in paths
    assert "config/workflows/skills.json" in paths
    assert "spec/success-criteria/index.md" in paths
    assert all(item.reason for item in packet.required_context)
    assert not any(item.path == "." for item in packet.required_context)


def test_standards_attachment_uses_registry_ids() -> None:
    security = agentize_request("audit auth token handling for security bugs")
    workflow = agentize_request("implement workflow orchestration state updates")
    refactor = agentize_request("refactor this service without changing behavior")

    assert "security.review_traceability" in security.relevant_standards
    assert "workflow_agent_control.explicit_handshake" in workflow.relevant_standards
    assert {"code_quality.lint_ratchet", "testing.trust_signal"} <= set(refactor.relevant_standards)


def test_briefing_packets_has_selected_criteria_and_standards_columns() -> None:
    from aios_orchestration_runtime import ensure_runtime_schema

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE briefing_packets (id TEXT PRIMARY KEY)")
    ensure_runtime_schema(conn)
    columns = {
        row[1]: row[2] for row in conn.execute("PRAGMA table_info(briefing_packets)").fetchall()
    }

    assert columns["selected_criteria_json"] == "TEXT"
    assert columns["selected_standards_json"] == "TEXT"


def test_agentize_standards_come_from_registry() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO projects (id, name) VALUES ('p1', 'AIOS')")
    standards_health.ensure_standards_health_schema(conn)
    conn.execute(
        """
        INSERT INTO project_standards_profiles (
            project_id, profile_id, attached_version, latest_version, migration_mode, updated_at
        )
        VALUES ('p1', 'aios-core', '2026.05.0', '2026.05.0', 'current', '2026-05-23T00:00:00Z')
        """
    )
    packet = agentize_request(
        "implement workflow orchestration state updates",
        project_id="p1",
        project_name="AIOS",
        workflow_key="implementation-delivery",
        conn=conn,
    )
    resolved = resolve_task_standards(
        conn=conn,
        project_id="p1",
        project_name="AIOS",
        objective=packet.normalized_objective,
        prompt_classifications=[
            classification.value for classification in packet.task_classifications
        ],
        skills=packet.relevant_skills,
        workflow_key="implementation-delivery",
    )

    assert set(packet.relevant_standards) == {row["standard_id"] for row in resolved["standards"]}


def test_verification_plan_matches_execution_risk() -> None:
    implementation = agentize_request("implement the feature and update docs")
    audit = agentize_request("audit the feature only")
    risky = agentize_request("migrate authentication and database schema")

    assert {"unit_tests", "lint", "typecheck", "build"} <= {
        step.kind for step in implementation.verification_plan
    }
    assert {"evidence_review", "recommendation_review"} <= {
        step.kind for step in audit.verification_plan
    }
    assert "rollback_plan" in {step.kind for step in risky.verification_plan}


def test_prompt_library_is_evidence_not_required_static_mapping() -> None:
    packet = agentize_request("clean up this repo")

    assert packet.prompt_pattern_evidence
    assert packet.prompt_library_role == "supporting_pattern_corpus"
    assert packet.experiment_metadata["requires_static_template_mapping"] is False


def test_agentize_evaluation_records_outcome_without_promoting_learning() -> None:
    conn = sqlite3.connect(":memory:")
    ensure_agentize_schema(conn)
    packet = agentize_request("write tests for the workflow router")

    record = record_agentize_evaluation(
        conn,
        packet=packet,
        outcome_quality=4,
        tests_passed=True,
        user_correction=None,
        follow_up_required=False,
        major_repair_required=False,
    )

    assert record["packet_id"] == packet.packet_id
    row = conn.execute(
        "SELECT selected_execution_mode, outcome_quality, tests_passed FROM agentize_evaluations"
    ).fetchone()
    assert row == ("tdd_first_implementation", 4, 1)


def test_agentize_skills_come_from_recommender_when_available(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    conn = sqlite3.connect(":memory:")

    def fake_recommend_assets_for_packet(*args, **kwargs):  # type: ignore[no-untyped-def]
        if kwargs["asset_kind"] == "skill":
            return [
                _fake_recommendation("agentize_intent_compiler"),
                _fake_recommendation("smart_search"),
            ]
        return []

    monkeypatch.setattr(
        "services.asset_recommendation.recommend_assets_for_packet",
        fake_recommend_assets_for_packet,
    )
    packet = agentize_request(
        "research the implementation plan", conn=conn, workflow_key="agentize"
    )
    assert packet.relevant_skills == ("agentize_intent_compiler", "smart_search")
    assert packet.experiment_metadata["recommendation_source"] == "recommender"


def test_agentize_falls_back_to_heuristic_when_recommender_empty() -> None:
    conn = sqlite3.connect(":memory:")
    packet = agentize_request(
        "build the feature", conn=conn, workflow_key="implementation-delivery"
    )
    assert "agentize_intent_compiler" in packet.relevant_skills
    assert packet.experiment_metadata["recommendation_source"] == "fallback"


def test_agentize_evaluations_record_recommendation_source(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    conn = sqlite3.connect(":memory:")
    monkeypatch.setattr(
        "services.asset_recommendation.recommend_assets_for_packet",
        lambda *args, **kwargs: (
            [_fake_recommendation("agentize_intent_compiler")]
            if kwargs["asset_kind"] == "skill"
            else []
        ),
    )
    packet = agentize_request("compile this task", conn=conn, workflow_key="agentize")
    record_agentize_evaluation(
        conn,
        packet=packet,
        outcome_quality=1,
        tests_passed=True,
        user_correction=None,
        follow_up_required=False,
        major_repair_required=False,
    )
    row = conn.execute("SELECT transformed_request_json FROM agentize_evaluations").fetchone()
    payload = json.loads(row[0])
    assert payload["experiment_metadata"]["recommendation_source"] == "recommender"


def test_agentize_workflow_and_skill_registry_bindings_are_valid() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")

    assert "agentize" in workflows
    assert "agentize_intent_compiler" in skills
    assert validate_workflow_bindings(workflows, skills) == []


def test_agentize_workflow_executes_and_emits_packet_artifact() -> None:
    report = execute_workflow(
        WorkflowExecutionContext(
            objective="Agentize this request: audit the workflow router and propose tests",
            workflow_key="agentize",
        )
    )

    packet = report["artifacts"]["agentized_task_packet"]

    assert report["status"] == "completed"
    assert packet["prompt_library_role"] == "supporting_pattern_corpus"
    assert packet["execution_mode"]["reasoning"]
    assert packet["verification_plan"]


def test_stage_evaluation_emits_findings(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orchestration_runs (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO orchestration_runs (id) VALUES ('run-stage')")

    report = execute_workflow(
        WorkflowExecutionContext(
            objective="Agentize this request: implement workflow routing",
            workflow_key="agentize",
            run_id="run-stage",
        ),
        conn=conn,
        stage_artifact_root=tmp_path,
    )

    rows = conn.execute(
        """
        SELECT stage_key, stage_kind, criterion_id, level
        FROM success_criteria_stage_findings
        ORDER BY stage_key, criterion_id
        """
    ).fetchall()

    assert report["stage_evaluations"]
    assert rows
    assert {row[0] for row in rows} == {"validate"}
    assert all(row[1] == "validate" for row in rows)


def test_parse_request_stages_produce_no_findings(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orchestration_runs (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO orchestration_runs (id) VALUES ('run-stage')")

    execute_workflow(
        WorkflowExecutionContext(
            objective="Agentize this request: implement workflow routing",
            workflow_key="agentize",
            run_id="run-stage",
        ),
        conn=conn,
        stage_artifact_root=tmp_path,
    )

    parse_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM success_criteria_stage_findings
        WHERE stage_key = 'compile_intent'
        """
    ).fetchone()[0]
    assert parse_count == 0


def test_stage_findings_persisted_to_db_and_artifact(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orchestration_runs (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO orchestration_runs (id) VALUES ('run-stage')")

    execute_workflow(
        WorkflowExecutionContext(
            objective="Agentize this request: implement workflow routing",
            workflow_key="agentize",
            run_id="run-stage",
        ),
        conn=conn,
        stage_artifact_root=tmp_path,
    )

    assert conn.execute("SELECT COUNT(*) FROM success_criteria_stage_findings").fetchone()[0] > 0
    artifact = tmp_path / "stage-run-stage-validate.json"
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["stage_key"] == "validate"
    assert payload["finding_ids"]
