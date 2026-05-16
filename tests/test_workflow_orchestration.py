from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.workflow_orchestration import (  # noqa: E402
    WorkflowExecutionContext,
    execute_workflow,
    load_skill_registry,
    load_workflow_registry,
    summarize_execution_report,
    validate_workflow_bindings,
)


def test_registry_bindings_are_valid() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    errors = validate_workflow_bindings(workflows, skills)
    assert errors == []
    assert "academic_paper_v1" in workflows


def test_execute_academic_workflow_with_validations(tmp_path: Path) -> None:
    prompt_registry = tmp_path / "prompt-registry.json"
    prompt_registry.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "content_writing",
                        "classification": "content_writing",
                        "tags": ["paper", "academic", "citations"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "style.md").write_text("Use direct transitions and explicit claims.\n", encoding="utf-8")

    context = WorkflowExecutionContext(
        objective="Write an academic paper about retrieval quality and citation fidelity",
        workflow_key="academic_paper_v1",
        vault_root=str(vault_root),
        prompt_registry_path=str(prompt_registry),
        run_id="run-1",
        invocation_id="invoke-1",
    )

    report = execute_workflow(context)
    assert report["status"] == "completed"
    assert report["workflow_key"] == "academic_paper_v1"
    assert len(report["stages"]) >= 6

    validations = {row["validation_key"]: row for row in report["validations"]}
    assert validations["structure_checker"]["passed"] is True
    assert validations["citation_checker"]["passed"] is True
    assert validations["meaning_preservation_checker"]["passed"] is True

    artifacts = report["artifacts"]
    assert artifacts["template_id"] == "content_writing"
    assert "## References" in artifacts["humanized_text"]

    summary = summarize_execution_report(report)
    assert "academic_paper_v1" in summary
    assert "status=completed" in summary


def test_unknown_workflow_raises(tmp_path: Path) -> None:
    context = WorkflowExecutionContext(
        objective="Any objective",
        workflow_key="does_not_exist",
    )

    with pytest.raises(ValueError, match="Unknown workflow key"):
        execute_workflow(context)


def test_implementation_workflow_attaches_execution_strategy() -> None:
    context = WorkflowExecutionContext(
        objective="Audit and implement a scoped fix for failing runtime checks",
        workflow_key="implementation-delivery",
        surface="codex",
    )

    report = execute_workflow(context)
    assert report["status"] == "completed"
    strategy = report["artifacts"]["execution_strategy"]
    assert strategy is not None
    assert strategy["strategy_id"] == "audit_and_implement_codex_v1"


def test_generated_executor_skill_affects_execution(tmp_path: Path) -> None:
    workflow_registry = tmp_path / "registry.json"
    skill_registry = tmp_path / "skills.json"
    workflow_registry.write_text(
        json.dumps(
            {
                "version": "test",
                "stage_kinds": ["normalize_prompt", "generate", "validate"],
                "workflows": [
                    {
                        "key": "debug_root_cause_investigation_v1",
                        "name": "Debug & Root Cause Investigation",
                        "purpose": "Debug workflow",
                        "trigger_hints": ["debug"],
                        "output_contract": ["evidence-backed result"],
                        "required_validations": ["scope_check"],
                        "stages": [
                            {
                                "key": "normalize_prompt",
                                "kind": "normalize_prompt",
                                "required_skills": ["prompt_library_normalizer"],
                            },
                            {
                                "key": "execute_pattern",
                                "kind": "generate",
                                "required_skills": ["debug_root_cause_investigation_v1_executor"],
                            },
                            {
                                "key": "validate",
                                "kind": "validate",
                                "required_skills": ["scope_check"],
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    skill_registry.write_text(
        json.dumps(
            {
                "version": "test",
                "skills": [
                    {
                        "key": "prompt_library_normalizer",
                        "purpose": "Normalize prompt",
                        "allowed_stages": ["normalize_prompt"],
                        "input_schema": {},
                        "output_schema": {},
                        "invariants": [],
                        "failure_conditions": [],
                        "side_effects": [],
                        "execution_mode": "deterministic",
                    },
                    {
                        "key": "debug_root_cause_investigation_v1_executor",
                        "purpose": "Execute learned debug pattern",
                        "allowed_stages": ["generate"],
                        "input_schema": {"objective": "string"},
                        "output_schema": {"result_text": "string", "evidence": "string[]"},
                        "invariants": [
                            "Use the learned pattern only when trigger evidence matches.",
                            "Return explicit evidence for why the workflow applied.",
                        ],
                        "failure_conditions": [],
                        "side_effects": [],
                        "execution_mode": "heuristic",
                        "source_path": "/tmp/skills/debug/SKILL.md",
                        "installed_name": "debug-root-cause",
                    },
                    {
                        "key": "scope_check",
                        "purpose": "Check scope",
                        "allowed_stages": ["validate"],
                        "input_schema": {},
                        "output_schema": {},
                        "invariants": [],
                        "failure_conditions": [],
                        "side_effects": [],
                        "execution_mode": "deterministic",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    report = execute_workflow(
        WorkflowExecutionContext(
            objective="Debug failing runtime checks",
            workflow_key="debug_root_cause_investigation_v1",
        ),
        workflow_registry_path=workflow_registry,
        skill_registry_path=skill_registry,
    )

    assert report["status"] == "completed"
    assert "Debug failing runtime checks" in report["artifacts"]["result_text"]
    assert any(rule["title"] == "Read before you write" for rule in report["artifacts"]["agent_rules"])
    assert "Agent rules:" in report["artifacts"]["normalized_prompt"]
    generate_stage = next(stage for stage in report["stages"] if stage["kind"] == "generate")
    assert generate_stage["skills"][0]["output_keys"] == ["evidence", "result_text"]
    assert generate_stage["skills"][0]["source_path"] == "/tmp/skills/debug/SKILL.md"
    assert generate_stage["skills"][0]["installed_name"] == "debug-root-cause"
