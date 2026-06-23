from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.execution_strategy import (  # noqa: E402
    StrategySelectionError,
    build_strategy_registry_snapshot,
    compile_execution_strategy,
    list_model_selection_records,
    list_strategy_candidates,
    load_developer_experience_routing_policy,
    load_model_routing_policy,
    load_strategy_catalog,
    load_task_specs,
    recommend_execution_surface,
    record_model_selection,
    select_developer_experience_route,
    validate_model_routing_policy,
    validate_strategy_catalog,
)


def test_catalog_validation_and_snapshot() -> None:
    task_specs = load_task_specs(ROOT / "config" / "execution-strategies" / "task-specs.json")
    strategy_catalog = load_strategy_catalog(ROOT / "config" / "execution-strategies" / "strategies.json")

    errors = validate_strategy_catalog(task_specs, strategy_catalog)
    assert errors == []

    snapshot = build_strategy_registry_snapshot(task_specs, strategy_catalog)
    selected = snapshot["strategy_selection"]
    assert len(selected) == 2
    surfaces = {row["surface"] for row in selected}
    assert surfaces == {"claude_code", "codex"}


def test_model_routing_policy_validation() -> None:
    policy = load_model_routing_policy(
        ROOT / "config" / "execution-strategies" / "model-routing-policy.json"
    )

    errors = validate_model_routing_policy(policy)

    assert errors == []
    assert policy["policy_id"] == "subagent-default-routing-policy"
    assert policy["subagent_preference_policy"]["default_execution_mode"] == (
        "orchestrated_subagents"
    )
    assert {role["role"] for role in policy["agent_roles"]} >= {
        "orchestrator",
        "explorer",
        "implementer",
        "reviewer",
        "specialist",
    }
    telemetry_fields = set(policy["telemetry_schema"]["run_fields"])
    assert {"model_used", "reasoning_level_used", "model_choice_notes"} <= telemetry_fields


def test_compile_execution_strategy_for_codex() -> None:
    compiled = compile_execution_strategy(
        objective="Audit the current implementation and ship a scoped fix with tests",
        task_family="audit_and_implement",
        surface="codex",
        task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
        strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
    )

    assert compiled["strategy_id"] == "audit_and_implement_codex_v1"
    assert compiled["strategy_status"] == "validated"
    assert "Task Family: audit_and_implement" in compiled["compiled_instruction"]


def test_compile_unknown_task_family_raises() -> None:
    with pytest.raises(StrategySelectionError, match="Unknown task family"):
        compile_execution_strategy(
            objective="irrelevant",
            task_family="not_real",
            surface="codex",
            task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
            strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
        )


def test_list_strategy_candidates_prefers_validated_entries() -> None:
    candidates = list_strategy_candidates(
        task_family="audit_and_implement",
        task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
        strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
    )

    assert [candidate.surface for candidate in candidates] == ["claude_code", "codex"]
    assert all(candidate.status == "validated" for candidate in candidates)


def test_recommend_execution_surface_prefers_codex_first() -> None:
    recommendation = recommend_execution_surface(
        task_family="audit_and_implement",
        preferred_surfaces=("codex", "claude_code"),
        task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
        strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
    )

    assert recommendation["selected_surface"] == "codex"
    assert recommendation["selected_strategy_id"] == "audit_and_implement_codex_v1"
    assert recommendation["alternatives"][0]["surface"] == "claude_code"


def test_model_selection_records_allow_unavailable_cost_and_token_data() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    record_id = record_model_selection(
        conn,
        task_id="task-1",
        phase="16-06",
        task_type="multi_file_feature_implementation",
        selected_model="gpt-5-codex",
        reasoning_level="high",
        selection_reason="Non-trivial multi-file harness persistence change.",
        fallback_model=None,
        tokens_used=None,
        cost_estimate=None,
        latency_ms=None,
        outcome="success",
        caveat="Provider did not expose token or cost usage.",
    )

    rows = list_model_selection_records(conn, task_id="task-1")

    assert rows[0]["id"] == record_id
    assert rows[0]["tokens_used"] is None
    assert rows[0]["cost_estimate"] is None
    assert rows[0]["caveat"] == "Provider did not expose token or cost usage."


def test_dx_simple_docs_cleanup_uses_low_reasoning() -> None:
    route = select_developer_experience_route(
        capability_id="docs_writer",
        task_signals={"docs_cleanup"},
        second_brain_available=False,
    )

    assert route["mode"] == "implementation"
    assert route["reasoning_level"] == "low"
    assert route["second_brain_required"] is False


def test_dx_security_sensitive_automation_escalates() -> None:
    route = select_developer_experience_route(
        capability_id="security_reviewer",
        task_signals={"security_sensitive_change"},
        second_brain_available=True,
    )

    assert route["reasoning_level"] == "high"
    assert route["human_gate_required"] is True
    assert route["second_brain_available"] is True


def test_dx_typescript_specialist_avoids_simple_non_typescript_work() -> None:
    route = select_developer_experience_route(
        capability_id="typescript_specialist",
        task_signals={"simple_non_typescript_work"},
        second_brain_available=False,
    )

    assert route["selected_capability"] == "dx_optimizer"
    assert route["reasoning_level"] == "low"


def test_dx_routing_policy_loads() -> None:
    policy = load_developer_experience_routing_policy()

    assert policy["second_brain_policy"]["peer_run_requires_second_brain"] is False
    assert "security_sensitive_change" in policy["escalation_triggers"]
