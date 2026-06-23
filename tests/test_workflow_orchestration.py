from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import get_args

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import success_criteria  # noqa: E402
from services.asset_lifecycle import AssetLifecycleState  # noqa: E402
from services.workflow_orchestration import (  # noqa: E402
    HEALTH_TO_WORKFLOW_RULES,
    ApprovalGateBinding,
    ArtifactBinding,
    InputBinding,
    LearningSignalBinding,
    OutputBinding,
    PromptBinding,
    StageSpec,
    ValidationBinding,
    WorkflowExecutionContext,
    WorkflowSpec,
    WritebackBindingSpec,
    _build_stage_evaluation_summary,
    _reset_validation_caches,
    _stage_from_row,
    developer_experience_capability_report,
    execute_workflow,
    load_developer_experience_capability_pack,
    load_skill_registry,
    load_workflow_registry,
    rank_workflow_candidates,
    recommend_prompt_family,
    recommend_route_primitives,
    recommend_workflow_from_health,
    summarize_execution_report,
    validate_workflow_bindings,
    workflow_requires_independent_verification,
    workflow_stage_gate_report,
)


def test_registry_bindings_are_valid() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    errors = validate_workflow_bindings(workflows, skills)
    assert errors == []
    assert "academic_paper_v1" in workflows


def test_load_registry_normalizes_lifecycle_fields() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    states = set(get_args(AssetLifecycleState))

    assert all(workflow.lifecycle_state in states for workflow in workflows.values())
    assert all(isinstance(workflow.applicability, tuple) for workflow in workflows.values())
    assert all(isinstance(workflow.purpose_long, str) for workflow in workflows.values())
    assert all(isinstance(workflow.implementation_bearing, bool) for workflow in workflows.values())
    assert all(isinstance(workflow.verification_exempt, bool) for workflow in workflows.values())
    assert all(skill.lifecycle_state in states for skill in skills.values())
    assert all(isinstance(skill.applicability, tuple) for skill in skills.values())
    assert all(isinstance(skill.purpose_long, str) for skill in skills.values())


def test_existing_six_workflows_load_with_defaults() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    assert {
        "implementation-delivery",
        "failure-recovery",
        "academic_paper_v1",
        "divergent-strategy",
        "personalized-humanizer",
        "agentize",
    } <= set(workflows)
    assert workflows["implementation-delivery"].lifecycle_state == "active"
    assert workflows["failure-recovery"].lifecycle_state == "active"


def test_implementation_workflows_require_independent_verification() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")

    assert workflows["implementation-delivery"].implementation_bearing is True
    assert workflow_requires_independent_verification(workflows["implementation-delivery"]) is True


def test_implementation_delivery_declares_deterministic_stage_gates() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    workflow = workflows["implementation-delivery"]
    validate_stage = next(stage for stage in workflow.stages if stage.key == "validate")
    finalize_stage = next(stage for stage in workflow.stages if stage.key == "finalize")

    assert validate_stage.required_evidence == ("evidence_artifacts",)
    assert finalize_stage.required_verifier is True


def test_developer_experience_pack_loads_with_required_capabilities() -> None:
    pack = load_developer_experience_capability_pack(
        ROOT / "config" / "developer-experience" / "capability-pack.json"
    )

    report = developer_experience_capability_report(pack)

    assert report["fixed_model_per_capability"] is False
    assert report["peer_run_second_brain_dependency_allowed"] is False
    assert {row["id"] for row in report["capabilities"]} == {
        "dx_optimizer",
        "interface_dx_reviewer",
        "docs_writer",
        "security_reviewer",
        "typescript_specialist",
        "spec_fidelity_coder",
    }


def test_developer_experience_workflow_uses_existing_skill_registry() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")

    workflow = workflows["developer-experience-pack"]
    expected = {
        "dx_optimizer",
        "interface_dx_reviewer",
        "docs_writer",
        "security_reviewer",
        "typescript_specialist",
        "spec_fidelity_coder",
    }
    capability_skills = {
        skill
        for stage in workflow.stages
        for skill in stage.required_skills
        if skill in expected
    }

    assert workflow.workflow_family == "developer_experience"
    assert capability_skills == expected
    assert all(
        skills[skill].source_path == "config/developer-experience/capability-pack.json"
        for skill in capability_skills
    )
    assert validate_workflow_bindings({"developer-experience-pack": workflow}, skills) == []


def test_workflow_stage_gate_report_exposes_gate_metadata() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")

    report = workflow_stage_gate_report(workflows)

    assert {
        "workflow_key": "implementation-delivery",
        "stage_key": "validate",
        "stage_kind": "validate",
        "required_evidence": ["evidence_artifacts"],
        "required_verifier": False,
        "prompt_templates": [],
    } in report
    assert any(
        row["workflow_key"] == "implementation-delivery"
        and row["stage_key"] == "finalize"
        and row["required_verifier"] is True
        for row in report
    )


def test_verification_exempt_workflow_requires_reason() -> None:
    workflows = {
        "synthetic": WorkflowSpec(
            key="synthetic",
            name="Synthetic",
            workflow_family="implementation",
            purpose="Implement",
            trigger_hints=(),
            output_contract=(),
            required_validations=(),
            stages=(),
            implementation_bearing=True,
            verification_exempt=True,
        )
    }

    errors = validate_workflow_bindings(workflows, {})

    assert "workflow=synthetic verification_exempt=true requires verification_exempt_reason" in errors


def test_prompt_registry_accepts_legacy_route_status_alias(tmp_path: Path) -> None:
    workflow_registry = tmp_path / "workflows.json"
    workflow_registry.write_text(
        json.dumps(
            {
                "workflows": [
                    {
                        "key": "audit",
                        "name": "Audit",
                        "workflow_family": "audit_only",
                        "purpose": "Audit",
                        "trigger_hints": ["audit"],
                        "output_contract": [],
                        "required_validations": [],
                        "stages": [
                            {"key": "parse", "kind": "parse_request", "required_skills": []}
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    prompt_registry = tmp_path / "prompts.json"

    prompt_registry.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "legacy",
                        "prompt_family": "research_handoff",
                        "route_status": "approved",
                        "classification": "plan",
                        "applicable_workflow_families": ["audit_only"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = recommend_prompt_family(
        objective="audit plan",
        workflow_key="audit",
        prompt_registry_path=prompt_registry,
        workflow_registry_path=workflow_registry,
    )
    assert result["lifecycle_state"] == "active"

    prompt_registry.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "new",
                        "prompt_family": "research_handoff",
                        "route_status": "approved",
                        "lifecycle_state": "candidate",
                        "classification": "plan",
                        "applicable_workflow_families": ["audit_only"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = recommend_prompt_family(
        objective="audit plan",
        workflow_key="audit",
        prompt_registry_path=prompt_registry,
        workflow_registry_path=workflow_registry,
    )
    assert result["lifecycle_state"] == "candidate"

    prompt_registry.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "defaulted",
                        "prompt_family": "research_handoff",
                        "classification": "plan",
                        "applicable_workflow_families": ["audit_only"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = recommend_prompt_family(
        objective="audit plan",
        workflow_key="audit",
        prompt_registry_path=prompt_registry,
        workflow_registry_path=workflow_registry,
    )
    assert result["lifecycle_state"] == "candidate"


def test_validate_workflow_bindings_still_passes_for_existing_workflows() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    assert validate_workflow_bindings(workflows, skills) == []


def test_stage_spec_loads_vnext_bindings() -> None:
    stage = _stage_from_row(
        {
            "key": "validate",
            "kind": "validate",
            "required_skills": ["scope_check"],
            "required_inputs": [{"key": "packet", "source": "packet"}],
            "required_outputs": [{"key": "report", "target": "report"}],
            "validations": [{"criterion_id": "code-simplicity", "blocking": True}],
            "approval_gates": [
                {
                    "impact_scope": "workflow-default",
                    "condition": "on_failure",
                    "rationale_template": "review",
                }
            ],
            "expected_artifacts": [{"artifact_kind": "evidence", "path_template": "x"}],
            "writeback_behavior": {
                "on_success": ["workflow_learning_event"],
                "on_failure": ["follow_up_item"],
            },
            "learning_signals": [{"signal_kind": "validation_pass", "measure": "per_run"}],
            "prompt_bindings": [{"template_id": "research", "role": "primary"}],
            "standards_bindings": ["code_quality.lint_ratchet"],
        },
        workflow_key="test",
    )

    assert isinstance(stage.required_inputs[0], InputBinding)
    assert isinstance(stage.required_outputs[0], OutputBinding)
    assert isinstance(stage.validations[0], ValidationBinding)
    assert isinstance(stage.approval_gates[0], ApprovalGateBinding)
    assert isinstance(stage.expected_artifacts[0], ArtifactBinding)
    assert isinstance(stage.writeback_behavior, WritebackBindingSpec)
    assert isinstance(stage.learning_signals[0], LearningSignalBinding)
    assert isinstance(stage.prompt_bindings[0], PromptBinding)
    assert stage.standards_bindings == ("code_quality.lint_ratchet",)
    assert stage.required_evidence == ()
    assert stage.required_verifier is False


def test_stage_spec_defaults_when_bindings_omitted() -> None:
    stage = _stage_from_row(
        {"key": "parse", "kind": "parse_request", "required_skills": []},
        workflow_key="test",
    )
    assert stage.required_inputs == ()
    assert stage.required_outputs == ()
    assert stage.validations == ()
    assert stage.approval_gates == ()
    assert stage.expected_artifacts == ()
    assert stage.writeback_behavior == WritebackBindingSpec()
    assert stage.learning_signals == ()
    assert stage.prompt_bindings == ()
    assert stage.standards_bindings == ()
    assert stage.required_evidence == ()
    assert stage.required_verifier is False


def test_existing_six_workflows_load_with_default_bindings() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    assert len(workflows) >= 6
    assert all(
        isinstance(stage.writeback_behavior, WritebackBindingSpec)
        for workflow in workflows.values()
        for stage in workflow.stages
    )


def test_input_binding_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="ether"):
        _stage_from_row(
            {
                "key": "parse",
                "kind": "parse_request",
                "required_skills": [],
                "required_inputs": [{"key": "x", "source": "ether"}],
            },
            workflow_key="test",
        )


def test_prompt_binding_resolves_template_id() -> None:
    stage = _stage_from_row(
        {
            "key": "parse",
            "kind": "parse_request",
            "required_skills": [],
            "prompt_bindings": [{"template_id": "research", "role": "primary"}],
        },
        workflow_key="test",
    )
    assert stage.prompt_bindings[0].template_id == "research"


def test_approval_gate_binding_rejects_unknown_condition() -> None:
    with pytest.raises(ValueError, match="sometimes"):
        _stage_from_row(
            {
                "key": "validate",
                "kind": "validate",
                "required_skills": [],
                "approval_gates": [
                    {
                        "impact_scope": "workflow-default",
                        "condition": "sometimes",
                        "rationale_template": "x",
                    }
                ],
            },
            workflow_key="test",
        )


def test_writeback_behavior_preserves_no_learning_evidence_required_flag() -> None:
    stage = _stage_from_row(
        {
            "key": "validate",
            "kind": "validate",
            "required_skills": [],
            "writeback_behavior": {
                "on_success": ["workflow_learning_event"],
                "on_failure": [],
                "no_learning_evidence_required": True,
            },
        },
        workflow_key="test",
    )
    assert stage.writeback_behavior.no_learning_evidence_required is True


def _workflow_for_validation(
    *,
    lifecycle_state: str = "candidate",
    validations: tuple[ValidationBinding, ...] = (),
    prompt_bindings: tuple[PromptBinding, ...] = (),
    standards_bindings: tuple[str, ...] = (),
) -> dict[str, WorkflowSpec]:
    return {
        "synthetic": WorkflowSpec(
            key="synthetic",
            name="Synthetic",
            workflow_family="audit_only",
            purpose="Synthetic",
            trigger_hints=(),
            output_contract=(),
            required_validations=(),
            stages=(
                StageSpec(
                    key="validate",
                    kind="validate",
                    required_skills=(),
                    validations=validations,
                    prompt_bindings=prompt_bindings,
                    standards_bindings=standards_bindings,
                ),
            ),
            lifecycle_state=lifecycle_state,  # type: ignore[arg-type]
        )
    }


def test_validate_bindings_rejects_unresolvable_validation_criterion_id() -> None:
    _reset_validation_caches()
    errors = validate_workflow_bindings(
        _workflow_for_validation(validations=(ValidationBinding("nonexistent-criterion"),)),
        {},
    )
    assert any("nonexistent-criterion" in error and "synthetic" in error for error in errors)


def test_validate_bindings_rejects_unresolvable_prompt_binding() -> None:
    _reset_validation_caches()
    errors = validate_workflow_bindings(
        _workflow_for_validation(prompt_bindings=(PromptBinding("ghost-template"),)),
        {},
    )
    assert any("ghost-template" in error and "synthetic" in error for error in errors)


def test_validate_bindings_accepts_resolvable_bindings() -> None:
    _reset_validation_caches()
    errors = validate_workflow_bindings(
        _workflow_for_validation(
            validations=(ValidationBinding("code-simplicity"),),
            prompt_bindings=(PromptBinding("research"),),
            standards_bindings=("code_quality.lint_ratchet",),
        ),
        {},
    )
    assert errors == []


def test_active_workflow_without_validations_is_rejected() -> None:
    _reset_validation_caches()
    errors = validate_workflow_bindings(_workflow_for_validation(lifecycle_state="active"), {})
    assert any("zero validations" in error for error in errors)


def test_candidate_workflow_without_validations_is_accepted() -> None:
    _reset_validation_caches()
    errors = validate_workflow_bindings(_workflow_for_validation(lifecycle_state="candidate"), {})
    assert errors == []


def test_six_existing_workflows_pass_validation_post_vnext() -> None:
    _reset_validation_caches()
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    assert validate_workflow_bindings(workflows, skills) == []


def test_validate_bindings_rejects_unknown_standards_binding() -> None:
    _reset_validation_caches()
    errors = validate_workflow_bindings(
        _workflow_for_validation(standards_bindings=("fake-standard",)),
        {},
    )
    assert any("fake-standard" in error for error in errors)


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
    (vault_root / "style.md").write_text(
        "Use direct transitions and explicit claims.\n", encoding="utf-8"
    )

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


def test_stage_evaluation_summary_in_report() -> None:
    context = WorkflowExecutionContext(
        objective="Audit and implement a scoped fix for failing runtime checks",
        workflow_key="implementation-delivery",
        surface="codex",
        run_id="run-stage-summary",
        invocation_id="invoke-stage-summary",
    )

    report = execute_workflow(context)

    assert "stage_evaluations" in report
    assert len(report["stage_evaluations"]) == len(report["stages"])
    first_stage = report["stage_evaluations"][0]
    assert first_stage["stage_key"] == report["stages"][0]["stage_key"]
    assert first_stage["outcome"] in {"completed", "failed", "blocked"}


def test_divergent_judge_stage_satisfies_required_validation_with_stage_findings(
    tmp_path: Path,
) -> None:
    conn = sqlite3.connect(":memory:")
    success_criteria.ensure_success_criteria_schema(conn)

    context = WorkflowExecutionContext(
        objective="Evaluate multiple plausible workflow strategies before implementation",
        workflow_key="divergent-strategy",
        surface="codex",
        run_id="run-divergent-validation-accounting",
        invocation_id="invoke-divergent-validation-accounting",
    )

    report = execute_workflow(
        context,
        conn=conn,
        stage_artifact_root=tmp_path / "success-criteria",
    )

    judge_stage = next(
        stage for stage in report["stages"] if stage["stage_key"] == "judge_candidates"
    )
    assert judge_stage["status"] == "completed"
    assert judge_stage["stage_evaluation"]["stage_finding_ids"]
    assert report["validations"] == []
    assert report["required_validations"] == ["divergent_judge_panel"]
    assert report["failed_required_validations"] == []
    assert "Required validation did not run: divergent_judge_panel" not in report[
        "unresolved_issues"
    ]
    assert report["status"] == "completed"


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
    assert any(
        rule["title"] == "Read before you write" for rule in report["artifacts"]["agent_rules"]
    )
    assert "Agent rules:" in report["artifacts"]["normalized_prompt"]
    generate_stage = next(stage for stage in report["stages"] if stage["kind"] == "generate")
    assert generate_stage["skills"][0]["output_keys"] == ["evidence", "result_text"]
    assert generate_stage["skills"][0]["source_path"] == "/tmp/skills/debug/SKILL.md"
    assert generate_stage["skills"][0]["installed_name"] == "debug-root-cause"


def test_rank_workflow_candidates_for_recovery_objective() -> None:
    ranked = rank_workflow_candidates("Debug the failing runtime and fix the regression")

    assert ranked
    assert ranked[0].workflow_key == "failure-recovery"
    assert ranked[0].workflow_family == "failure_recovery"


def test_recommend_prompt_family_for_implementation_workflow() -> None:
    recommendation = recommend_prompt_family(
        objective="Implement a scoped feature with a concise handoff",
        workflow_key="implementation-delivery",
    )

    assert recommendation["workflow_family"] == "audit_and_implement"
    assert recommendation["prompt_family"] in {
        "implementation_handoff",
        "reasoning_handoff",
        "research_handoff",
        "recovery_handoff",
    }
    assert recommendation["template_id"] is not None
    assert recommendation["route_status"] in {"approved", "candidate"}


def test_recommend_route_primitives_for_implementation_objective() -> None:
    route = recommend_route_primitives(
        "Audit the current implementation and ship a scoped fix with tests",
        surface="codex",
    )

    assert route["selected_workflow"]["workflow_key"] == "implementation-delivery"
    assert route["prompt_recommendation"]["prompt_family"] is not None
    assert route["backend_recommendation"]["selected_surface"] == "codex"


def _approval_policy_stub(**_: object) -> dict[str, object]:
    return {
        "policy_class": "workflow-default_change",
        "requires_approval": True,
        "reason": "workflow-default changes require approval.",
    }


def test_recommend_workflow_returns_standards_backfill_for_foundational() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {
                "standard_id": "code_quality.lint_ratchet",
                "domain": "code_quality",
                "status": "fail",
                "priority_bucket": "foundational",
                "priority_score": 10.0,
            }
        ],
        registry_workflows={"implementation-delivery", "failure-recovery"},
        approval_policy_fn=_approval_policy_stub,
    )

    assert recommendations[0]["workflow_key"] == "standards-backfill"
    assert recommendations[0]["available_in_registry"] is False


def test_recommend_workflow_returns_failure_recovery_for_blocked_workflow_agent_control() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {
                "standard_id": "workflow_agent_control.explicit_handshake",
                "domain": "workflow_agent_control",
                "status": "fail",
                "priority_bucket": "blocked",
                "priority_score": 9.0,
            }
        ],
        registry_workflows={"failure-recovery"},
        approval_policy_fn=_approval_policy_stub,
    )

    assert recommendations[0]["workflow_key"] == "failure-recovery"
    assert recommendations[0]["available_in_registry"] is True


def test_recommend_workflow_returns_security_review_for_security_fail() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {
                "standard_id": "security.review_traceability",
                "domain": "security",
                "status": "fail",
                "priority_bucket": "high_leverage",
                "priority_score": 8.0,
            }
        ],
        registry_workflows={"implementation-delivery"},
        approval_policy_fn=_approval_policy_stub,
    )

    assert recommendations[0]["workflow_key"] == "security-review"
    assert recommendations[0]["available_in_registry"] is False


def test_recommend_workflow_returns_codebase_architecture_review_for_architecture_fail() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {
                "standard_id": "architecture.boundary_enforcement",
                "domain": "architecture",
                "status": "fail",
                "priority_bucket": "high_leverage",
                "priority_score": 8.0,
            }
        ],
        registry_workflows={"implementation-delivery"},
        approval_policy_fn=_approval_policy_stub,
    )

    assert recommendations[0]["workflow_key"] == "codebase architecture review"
    assert recommendations[0]["available_in_registry"] is False


def test_recommend_workflow_returns_implementation_delivery_for_quick_wins() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {
                "standard_id": "documentation.truth_file_currency",
                "domain": "documentation",
                "status": "partial",
                "priority_bucket": "quick_wins",
                "priority_score": 4.0,
            }
        ],
        registry_workflows={"implementation-delivery"},
        approval_policy_fn=_approval_policy_stub,
    )

    assert recommendations[0]["workflow_key"] == "implementation-delivery"
    assert recommendations[0]["available_in_registry"] is True


def test_recommend_workflow_enriches_with_approval_policy() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {
                "standard_id": "documentation.truth_file_currency",
                "domain": "documentation",
                "status": "partial",
                "priority_bucket": "quick_wins",
                "priority_score": 4.0,
            }
        ],
        registry_workflows={"implementation-delivery"},
        approval_policy_fn=_approval_policy_stub,
    )

    assert recommendations[0]["requires_approval"] is True
    assert recommendations[0]["impact_scope"] == "workflow-default"
    assert recommendations[0]["policy_class"] == "workflow-default_change"


def test_recommend_workflow_returns_unique_recommendations_up_to_five() -> None:
    delta_items = [
        {
            "standard_id": f"standard-{index}",
            "domain": domain,
            "status": status,
            "priority_bucket": bucket,
            "priority_score": float(20 - index),
        }
        for index, (domain, status, bucket) in enumerate(
            [
                ("workflow_agent_control", "fail", "blocked"),
                ("security", "fail", "high_leverage"),
                ("architecture", "fail", "high_leverage"),
                ("testing", "fail", "foundational"),
                ("documentation", "partial", "quick_wins"),
                ("code_quality", "fail", "foundational"),
                ("maintainability", "partial", "high_leverage"),
                ("ux", "unknown", "quick_wins"),
                ("observability", "partial", "quick_wins"),
                ("launch_readiness", "fail", "foundational"),
            ]
        )
    ]

    recommendations = recommend_workflow_from_health(
        delta_items=delta_items,
        registry_workflows={"failure-recovery", "implementation-delivery"},
        approval_policy_fn=_approval_policy_stub,
    )

    assert len(recommendations) <= 5
    workflow_keys = [row["workflow_key"] for row in recommendations]
    assert len(workflow_keys) == len(set(workflow_keys))
    assert (
        recommendations[0]["triggered_by"]["priority_score"]
        >= recommendations[-1]["triggered_by"]["priority_score"]
    )


def test_recommend_workflow_returns_empty_list_when_no_delta_items() -> None:
    assert recommend_workflow_from_health(delta_items=[], registry_workflows=set()) == []


def test_recommend_workflow_triggered_by_carries_delta_metadata() -> None:
    recommendations = recommend_workflow_from_health(
        delta_items=[
            {
                "standard_id": "testing.trust_signal",
                "domain": "testing",
                "status": "fail",
                "priority_bucket": "foundational",
                "priority_score": 7.5,
            }
        ],
        registry_workflows=set(),
        approval_policy_fn=_approval_policy_stub,
    )

    assert recommendations[0]["triggered_by"] == {
        "standard_id": "testing.trust_signal",
        "domain": "testing",
        "priority_bucket": "foundational",
        "priority_score": 7.5,
    }
    assert len(HEALTH_TO_WORKFLOW_RULES) == 5


def test_stage_evaluation_summary_outcome_completed_when_no_blockers() -> None:
    summary = _build_stage_evaluation_summary(
        stage_key="validate",
        skill_reports=[],
        validations=[{"passed": True}],
        stage_issues=[],
        stage_findings=[],
    )
    assert summary["outcome"] == "completed"
    assert summary["passed_validations"] == 1
    assert summary["total_validations"] == 1


def test_stage_evaluation_summary_outcome_failed_when_validation_fails() -> None:
    summary = _build_stage_evaluation_summary(
        stage_key="validate",
        skill_reports=[],
        validations=[{"passed": False}],
        stage_issues=[],
        stage_findings=[],
    )
    assert summary["outcome"] == "failed"


def test_stage_evaluation_summary_outcome_blocked_when_blocker_finding() -> None:
    summary = _build_stage_evaluation_summary(
        stage_key="validate",
        skill_reports=[],
        validations=[{"passed": True}],
        stage_issues=[],
        stage_findings=[{"id": "finding-1", "level": "blocker"}],
    )
    assert summary["outcome"] == "blocked"
    assert summary["blocker_count"] == 1


def test_stage_evaluation_summary_includes_stage_finding_ids() -> None:
    summary = _build_stage_evaluation_summary(
        stage_key="validate",
        skill_reports=[],
        validations=[],
        stage_issues=[],
        stage_findings=[{"id": "finding-1", "level": "warning"}],
    )
    assert summary["stage_finding_ids"] == ["finding-1"]


def test_stage_evaluation_summary_counts_warnings_separately() -> None:
    summary = _build_stage_evaluation_summary(
        stage_key="validate",
        skill_reports=[],
        validations=[],
        stage_issues=[],
        stage_findings=[{"id": "finding-1", "level": "warning"}],
    )
    assert summary["warning_count"] == 1
    assert summary["outcome"] == "completed"
