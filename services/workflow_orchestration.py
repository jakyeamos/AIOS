from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast, get_args

from services import success_criteria
from services.agent_rules import load_agent_rules
from services.agentize import agentize_request
from services.asset_lifecycle import AssetLifecycleState
from services.execution_strategy import (
    StrategySelectionError,
    compile_execution_strategy,
    recommend_execution_surface,
)
from services.expert_rubric_remediation import (
    build_audit_report,
    build_implementation_handoff,
    build_remediation_plan,
    synthesize_rubric,
    validate_audit_report,
    validate_remediation_plan,
    validate_rubric,
    write_review_artifacts,
)
from services.personalized_humanizer import (
    VoiceMode,
    build_voice_packet,
    classify_writing_task,
    score_quality,
    transform_text,
)
from services.rtk_integration import load_compression_rules
from services.semantic_workflow_routing import (
    SemanticWorkflowReasoner,
    configured_semantic_reasoner,
    semantic_recommendation,
)
from services.tmcp_runtime import expand_tmcp_packet_for_requirement_change

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_REGISTRY = ROOT / "config" / "workflows" / "registry.json"
DEFAULT_SKILL_REGISTRY = ROOT / "config" / "workflows" / "skills.json"
DEFAULT_PROMPT_REGISTRY = ROOT / "prompts" / "registry.json"
DEFAULT_DX_CAPABILITY_PACK = ROOT / "config" / "developer-experience" / "capability-pack.json"
WORKFLOW_TASK_FAMILIES = {
    "implementation-delivery": "audit_and_implement",
    "failure-recovery": "audit_and_implement",
    "expert_rubric_remediation_v1": "audit_and_plan",
    "developer-experience-pack": "developer_experience",
}
DX_CAPABILITY_IDS = {
    "dx_optimizer",
    "interface_dx_reviewer",
    "docs_writer",
    "security_reviewer",
    "typescript_specialist",
    "spec_fidelity_coder",
}
HealthWorkflowPredicate = Callable[[dict[str, Any]], bool]
HEALTH_TO_WORKFLOW_RULES: list[tuple[HealthWorkflowPredicate, str, str]] = [
    (
        lambda delta: (
            delta.get("priority_bucket") == "blocked"
            and delta.get("domain") == "workflow_agent_control"
        ),
        "failure-recovery",
        "Critical workflow-handshake blocker - recover handshake integrity before other work.",
    ),
    (
        lambda delta: (
            delta.get("domain") == "security" and delta.get("status") in {"fail", "partial"}
        ),
        "security-review",
        "Security domain has open delta - focused security review before broader work.",
    ),
    (
        lambda delta: delta.get("domain") == "architecture" and delta.get("status") == "fail",
        "codebase architecture review",
        "Architecture boundary failure - review before remediation work compounds.",
    ),
    (
        lambda delta: delta.get("priority_bucket") in {"foundational", "high_leverage"},
        "standards-backfill",
        "Highest-leverage standards gap - backfill workflow targets foundational deltas.",
    ),
    (
        lambda delta: delta.get("priority_bucket") == "quick_wins",
        "implementation-delivery",
        "Quick-win standards gap - implementation-delivery covers low-effort fixes.",
    ),
]

_ALLOWED_INPUT_SOURCES = frozenset({"packet", "prior_stage", "registry", "evidence"})
_ALLOWED_OUTPUT_TARGETS = frozenset({"report", "writeback", "artifact"})
_ALLOWED_IMPACT_SCOPES = frozenset(
    {
        "prompt-default",
        "skill-default",
        "workflow-default",
        "truth-default",
        "standards-default",
        "packet-default",
    }
)
_ALLOWED_APPROVAL_CONDITIONS = frozenset({"always", "on_failure", "on_blocker"})
_ALLOWED_ARTIFACT_KINDS = frozenset({"patch", "report", "evidence", "summary", "checkpoint"})
_ALLOWED_LEARNING_SIGNALS = frozenset(
    {
        "rework_rate",
        "validation_pass",
        "writeback_usefulness",
        "route_quality",
        "ambiguity_count",
        "blocker_count",
    }
)
_ALLOWED_PROMPT_ROLES = frozenset({"primary", "fallback"})
_VALID_CRITERION_IDS_CACHE: frozenset[str] | None = None
_VALID_PROMPT_TEMPLATE_IDS_CACHE: frozenset[str] | None = None
_VALID_STANDARDS_IDS_CACHE: frozenset[str] | None = None
_TMCP_STAGE_PHASES = {
    "parse_request": "planning",
    "normalize_prompt": "planning",
    "enrich_context": "planning",
    "generate": "implementation",
    "transform": "implementation",
    "validate": "testing",
    "finalize": "closeout",
}


@dataclass(frozen=True)
class InputBinding:
    key: str
    source: str
    required: bool = True
    schema_ref: str | None = None

    def __post_init__(self) -> None:
        if self.source not in _ALLOWED_INPUT_SOURCES:
            raise ValueError(
                f"Unsupported input source {self.source!r}; expected one of {sorted(_ALLOWED_INPUT_SOURCES)}"
            )


@dataclass(frozen=True)
class OutputBinding:
    key: str
    target: str
    required: bool = True
    schema_ref: str | None = None

    def __post_init__(self) -> None:
        if self.target not in _ALLOWED_OUTPUT_TARGETS:
            raise ValueError(
                f"Unsupported output target {self.target!r}; expected one of {sorted(_ALLOWED_OUTPUT_TARGETS)}"
            )


@dataclass(frozen=True)
class ValidationBinding:
    criterion_id: str
    blocking: bool = True


@dataclass(frozen=True)
class ApprovalGateBinding:
    impact_scope: str
    condition: str
    rationale_template: str

    def __post_init__(self) -> None:
        if self.impact_scope not in _ALLOWED_IMPACT_SCOPES:
            raise ValueError(
                f"Unsupported impact_scope {self.impact_scope!r}; expected one of {sorted(_ALLOWED_IMPACT_SCOPES)}"
            )
        if self.condition not in _ALLOWED_APPROVAL_CONDITIONS:
            raise ValueError(
                f"Unsupported approval condition {self.condition!r}; expected one of {sorted(_ALLOWED_APPROVAL_CONDITIONS)}"
            )


@dataclass(frozen=True)
class ArtifactBinding:
    artifact_kind: str
    path_template: str
    required: bool = True

    def __post_init__(self) -> None:
        if self.artifact_kind not in _ALLOWED_ARTIFACT_KINDS:
            raise ValueError(
                f"Unsupported artifact_kind {self.artifact_kind!r}; expected one of {sorted(_ALLOWED_ARTIFACT_KINDS)}"
            )


@dataclass(frozen=True)
class WritebackBindingSpec:
    on_success: tuple[str, ...] = ()
    on_failure: tuple[str, ...] = ("workflow_learning_event",)
    no_learning_evidence_required: bool = False


@dataclass(frozen=True)
class LearningSignalBinding:
    signal_kind: str
    measure: str

    def __post_init__(self) -> None:
        if self.signal_kind not in _ALLOWED_LEARNING_SIGNALS:
            raise ValueError(
                f"Unsupported learning signal {self.signal_kind!r}; expected one of {sorted(_ALLOWED_LEARNING_SIGNALS)}"
            )


@dataclass(frozen=True)
class PromptBinding:
    template_id: str
    role: str = "primary"

    def __post_init__(self) -> None:
        if self.role not in _ALLOWED_PROMPT_ROLES:
            raise ValueError(
                f"Unsupported prompt role {self.role!r}; expected one of {sorted(_ALLOWED_PROMPT_ROLES)}"
            )


@dataclass(frozen=True)
class StageSpec:
    key: str
    kind: str
    required_skills: tuple[str, ...]
    required_inputs: tuple[InputBinding, ...] = ()
    required_outputs: tuple[OutputBinding, ...] = ()
    validations: tuple[ValidationBinding, ...] = ()
    approval_gates: tuple[ApprovalGateBinding, ...] = ()
    expected_artifacts: tuple[ArtifactBinding, ...] = ()
    writeback_behavior: WritebackBindingSpec = field(default_factory=WritebackBindingSpec)
    learning_signals: tuple[LearningSignalBinding, ...] = ()
    prompt_bindings: tuple[PromptBinding, ...] = ()
    standards_bindings: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
    required_verifier: bool = False


@dataclass(frozen=True)
class WorkflowSpec:
    key: str
    name: str
    workflow_family: str
    purpose: str
    trigger_hints: tuple[str, ...]
    output_contract: tuple[str, ...]
    required_validations: tuple[str, ...]
    stages: tuple[StageSpec, ...]
    lifecycle_state: AssetLifecycleState = "candidate"
    applicability: tuple[str, ...] = ()
    purpose_long: str = ""
    implementation_bearing: bool = False
    verification_exempt: bool = False
    verification_exempt_reason: str | None = None


@dataclass(frozen=True)
class SkillSpec:
    key: str
    purpose: str
    allowed_stages: tuple[str, ...]
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    invariants: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    side_effects: tuple[str, ...]
    execution_mode: str
    source_path: str | None = None
    installed_name: str | None = None
    lifecycle_state: AssetLifecycleState = "candidate"
    applicability: tuple[str, ...] = ()
    purpose_long: str = ""


@dataclass(frozen=True)
class WorkflowRouteCandidate:
    workflow_key: str
    workflow_family: str
    score: int
    matched_terms: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class WorkflowExecutionContext:
    objective: str
    workflow_key: str
    surface: str = "codex"
    repo_path: str | None = None
    vault_root: str | None = None
    prompt_registry_path: str | None = None
    run_id: str | None = None
    invocation_id: str | None = None
    session_id: str | None = None
    tmcp_packet: dict[str, Any] | None = None
    evidence_items: tuple[dict[str, Any], ...] = ()
    selected_slice_id: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return loaded


def _lifecycle_state_from_row(
    row: dict[str, Any], *, default: AssetLifecycleState
) -> AssetLifecycleState:
    raw = str(row.get("lifecycle_state", row.get("route_status", default))).strip()
    if raw == "approved" and "lifecycle_state" not in row:
        return "active"
    if raw not in get_args(AssetLifecycleState):
        raise ValueError(f"Unsupported lifecycle_state: {raw}")
    return cast(AssetLifecycleState, raw)


def _prompt_lifecycle_state(template: dict[str, Any]) -> AssetLifecycleState:
    return _lifecycle_state_from_row(template, default="candidate")


def _dict_rows(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(row for row in value if isinstance(row, dict))


def _input_binding_from_row(row: dict[str, Any]) -> InputBinding:
    return InputBinding(
        key=str(row.get("key", "")).strip(),
        source=str(row.get("source", "")).strip(),
        required=bool(row.get("required", True)),
        schema_ref=str(row["schema_ref"]) if row.get("schema_ref") else None,
    )


def _output_binding_from_row(row: dict[str, Any]) -> OutputBinding:
    return OutputBinding(
        key=str(row.get("key", "")).strip(),
        target=str(row.get("target", "")).strip(),
        required=bool(row.get("required", True)),
        schema_ref=str(row["schema_ref"]) if row.get("schema_ref") else None,
    )


def _validation_binding_from_row(row: dict[str, Any]) -> ValidationBinding:
    return ValidationBinding(
        criterion_id=str(row.get("criterion_id", "")).strip(),
        blocking=bool(row.get("blocking", True)),
    )


def _approval_binding_from_row(row: dict[str, Any]) -> ApprovalGateBinding:
    return ApprovalGateBinding(
        impact_scope=str(row.get("impact_scope", "")).strip(),
        condition=str(row.get("condition", "")).strip(),
        rationale_template=str(row.get("rationale_template", "")).strip(),
    )


def _artifact_binding_from_row(row: dict[str, Any]) -> ArtifactBinding:
    return ArtifactBinding(
        artifact_kind=str(row.get("artifact_kind", "")).strip(),
        path_template=str(row.get("path_template", "")).strip(),
        required=bool(row.get("required", True)),
    )


def _writeback_binding_from_row(row: dict[str, Any]) -> WritebackBindingSpec:
    return WritebackBindingSpec(
        on_success=tuple(str(item) for item in row.get("on_success", []) if isinstance(item, str)),
        on_failure=tuple(
            str(item)
            for item in row.get("on_failure", ("workflow_learning_event",))
            if isinstance(item, str)
        ),
        no_learning_evidence_required=bool(row.get("no_learning_evidence_required", False)),
    )


def _learning_binding_from_row(row: dict[str, Any]) -> LearningSignalBinding:
    return LearningSignalBinding(
        signal_kind=str(row.get("signal_kind", "")).strip(),
        measure=str(row.get("measure", "")).strip(),
    )


def _prompt_binding_from_row(row: dict[str, Any]) -> PromptBinding:
    return PromptBinding(
        template_id=str(row.get("template_id", "")).strip(),
        role=str(row.get("role", "primary")).strip(),
    )


def _stage_from_row(row: dict[str, Any], *, workflow_key: str) -> StageSpec:
    required_skills = row.get("required_skills") or []
    if not isinstance(required_skills, list):
        raise ValueError(f"Workflow {workflow_key} stage required_skills must be a list.")
    writeback_row = row.get("writeback_behavior") or {}
    if not isinstance(writeback_row, dict):
        raise ValueError(f"Workflow {workflow_key} stage writeback_behavior must be an object.")
    standards_bindings = row.get("standards_bindings") or []
    if not isinstance(standards_bindings, list):
        raise ValueError(f"Workflow {workflow_key} stage standards_bindings must be a list.")
    required_evidence = row.get("required_evidence") or []
    if not isinstance(required_evidence, list):
        raise ValueError(f"Workflow {workflow_key} stage required_evidence must be a list.")
    return StageSpec(
        key=str(row.get("key", "")).strip(),
        kind=str(row.get("kind", "")).strip(),
        required_skills=tuple(
            str(skill).strip() for skill in required_skills if str(skill).strip()
        ),
        required_inputs=tuple(
            _input_binding_from_row(item) for item in _dict_rows(row.get("required_inputs"))
        ),
        required_outputs=tuple(
            _output_binding_from_row(item) for item in _dict_rows(row.get("required_outputs"))
        ),
        validations=tuple(
            _validation_binding_from_row(item) for item in _dict_rows(row.get("validations"))
        ),
        approval_gates=tuple(
            _approval_binding_from_row(item) for item in _dict_rows(row.get("approval_gates"))
        ),
        expected_artifacts=tuple(
            _artifact_binding_from_row(item) for item in _dict_rows(row.get("expected_artifacts"))
        ),
        writeback_behavior=_writeback_binding_from_row(writeback_row),
        learning_signals=tuple(
            _learning_binding_from_row(item) for item in _dict_rows(row.get("learning_signals"))
        ),
        prompt_bindings=tuple(
            _prompt_binding_from_row(item) for item in _dict_rows(row.get("prompt_bindings"))
        ),
        standards_bindings=tuple(
            str(item).strip() for item in standards_bindings if str(item).strip()
        ),
        required_evidence=tuple(
            str(item).strip() for item in required_evidence if str(item).strip()
        ),
        required_verifier=bool(row.get("required_verifier", False)),
    )


def load_workflow_registry(path: Path | None = None) -> dict[str, WorkflowSpec]:
    registry_path = path or DEFAULT_WORKFLOW_REGISTRY
    loaded = _load_json(registry_path)
    workflows_raw = loaded.get("workflows")
    if not isinstance(workflows_raw, list):
        raise ValueError("Workflow registry must contain a workflows list.")

    registry: dict[str, WorkflowSpec] = {}
    for item in workflows_raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            raise ValueError("Workflow key is required.")
        stage_rows = item.get("stages")
        if not isinstance(stage_rows, list) or not stage_rows:
            raise ValueError(f"Workflow {key} must define at least one stage.")
        stages: list[StageSpec] = []
        for row in stage_rows:
            if not isinstance(row, dict):
                raise ValueError(f"Workflow {key} has invalid stage row.")
            stages.append(_stage_from_row(row, workflow_key=key))
        registry[key] = WorkflowSpec(
            key=key,
            name=str(item.get("name", key)),
            workflow_family=str(item.get("workflow_family", WORKFLOW_TASK_FAMILIES.get(key, key))),
            purpose=str(item.get("purpose", "")),
            trigger_hints=tuple(
                str(hint) for hint in item.get("trigger_hints", []) if isinstance(hint, str)
            ),
            output_contract=tuple(
                str(row) for row in item.get("output_contract", []) if isinstance(row, str)
            ),
            required_validations=tuple(
                str(row) for row in item.get("required_validations", []) if isinstance(row, str)
            ),
            stages=tuple(stages),
            lifecycle_state=_lifecycle_state_from_row(item, default="candidate"),
            applicability=tuple(
                str(row) for row in item.get("applicability", []) if isinstance(row, str)
            ),
            purpose_long=str(item.get("purpose_long", "")),
            implementation_bearing=_workflow_implementation_bearing(item, stages),
            verification_exempt=bool(item.get("verification_exempt", False)),
            verification_exempt_reason=(
                str(item["verification_exempt_reason"])
                if item.get("verification_exempt_reason")
                else None
            ),
        )
    return registry


def workflow_requires_independent_verification(workflow: WorkflowSpec) -> bool:
    return workflow.implementation_bearing and not workflow.verification_exempt


def workflow_stage_gate_report(workflows: dict[str, WorkflowSpec]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for workflow in sorted(workflows.values(), key=lambda item: item.key):
        for stage in workflow.stages:
            if not stage.required_evidence and not stage.required_verifier:
                continue
            rows.append(
                {
                    "workflow_key": workflow.key,
                    "stage_key": stage.key,
                    "stage_kind": stage.kind,
                    "required_evidence": list(stage.required_evidence),
                    "required_verifier": stage.required_verifier,
                    "prompt_templates": [binding.template_id for binding in stage.prompt_bindings],
                }
            )
    return rows


def _workflow_implementation_bearing(item: dict[str, Any], stages: list[StageSpec]) -> bool:
    explicit = item.get("implementation_bearing")
    if isinstance(explicit, bool):
        return explicit
    text = " ".join(
        [
            str(item.get("key", "")),
            str(item.get("workflow_family", "")),
            str(item.get("purpose", "")),
            str(item.get("purpose_long", "")),
            " ".join(str(row) for row in item.get("output_contract", []) if isinstance(row, str)),
            " ".join(stage.key for stage in stages),
            " ".join(stage.kind for stage in stages),
        ]
    ).lower()
    return "implement" in text or "scoped code changes" in text


def load_skill_registry(path: Path | None = None) -> dict[str, SkillSpec]:
    registry_path = path or DEFAULT_SKILL_REGISTRY
    loaded = _load_json(registry_path)
    skills_raw = loaded.get("skills")
    if not isinstance(skills_raw, list):
        raise ValueError("Skill registry must contain a skills list.")

    registry: dict[str, SkillSpec] = {}
    for item in skills_raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        if not key:
            raise ValueError("Skill key is required.")
        registry[key] = SkillSpec(
            key=key,
            purpose=str(item.get("purpose", "")),
            allowed_stages=tuple(
                str(stage) for stage in item.get("allowed_stages", []) if isinstance(stage, str)
            ),
            input_schema={
                str(name): str(kind)
                for name, kind in (item.get("input_schema") or {}).items()
                if isinstance(name, str)
            },
            output_schema={
                str(name): str(kind)
                for name, kind in (item.get("output_schema") or {}).items()
                if isinstance(name, str)
            },
            invariants=tuple(
                str(row) for row in item.get("invariants", []) if isinstance(row, str)
            ),
            failure_conditions=tuple(
                str(row) for row in item.get("failure_conditions", []) if isinstance(row, str)
            ),
            side_effects=tuple(
                str(row) for row in item.get("side_effects", []) if isinstance(row, str)
            ),
            execution_mode=str(item.get("execution_mode", "deterministic")),
            source_path=str(item["source_path"]) if item.get("source_path") else None,
            installed_name=str(item["installed_name"]) if item.get("installed_name") else None,
            lifecycle_state=_lifecycle_state_from_row(item, default="candidate"),
            applicability=tuple(
                str(row) for row in item.get("applicability", []) if isinstance(row, str)
            ),
            purpose_long=str(item.get("purpose_long", "")),
        )
    return registry


def load_developer_experience_capability_pack(path: Path | None = None) -> dict[str, Any]:
    pack = _load_json(path or DEFAULT_DX_CAPABILITY_PACK)
    capabilities = pack.get("capabilities")
    if not isinstance(capabilities, list):
        raise ValueError("Developer-experience capability pack must define capabilities.")
    capability_ids = {
        str(row.get("id"))
        for row in capabilities
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    missing = DX_CAPABILITY_IDS - capability_ids
    if missing:
        raise ValueError(
            "Developer-experience capability pack missing capabilities: "
            + ", ".join(sorted(missing))
        )
    routing = pack.get("routing_principles")
    if not isinstance(routing, dict):
        raise ValueError("Developer-experience capability pack must define routing_principles.")
    if routing.get("fixed_model_per_capability") is not False:
        raise ValueError("Developer-experience capabilities must not hardcode fixed models.")
    return pack


def developer_experience_capability_report(pack: dict[str, Any]) -> dict[str, Any]:
    capabilities = [
        row
        for row in pack.get("capabilities", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    ]
    return {
        "pack_id": pack.get("id"),
        "status": pack.get("status"),
        "capabilities": [
            {
                "id": row["id"],
                "default_mode": row.get("default_mode"),
                "supported_modes": row.get("supported_modes", []),
                "invoke_when": row.get("invoke_when", []),
                "avoid_when": row.get("avoid_when", []),
            }
            for row in capabilities
        ],
        "metric_count": len(
            pack.get("metrics", []) if isinstance(pack.get("metrics"), list) else []
        ),
        "fixed_model_per_capability": (pack.get("routing_principles") or {}).get(
            "fixed_model_per_capability"
        ),
        "peer_run_second_brain_dependency_allowed": (pack.get("routing_principles") or {}).get(
            "peer_run_second_brain_dependency_allowed"
        ),
    }


def _reset_validation_caches() -> None:
    global _VALID_CRITERION_IDS_CACHE, _VALID_PROMPT_TEMPLATE_IDS_CACHE, _VALID_STANDARDS_IDS_CACHE
    _VALID_CRITERION_IDS_CACHE = None
    _VALID_PROMPT_TEMPLATE_IDS_CACHE = None
    _VALID_STANDARDS_IDS_CACHE = None


def _load_valid_criterion_ids() -> frozenset[str] | None:
    global _VALID_CRITERION_IDS_CACHE
    if _VALID_CRITERION_IDS_CACHE is not None:
        return _VALID_CRITERION_IDS_CACHE
    try:
        _VALID_CRITERION_IDS_CACHE = frozenset(row.id for row in success_criteria.load_registry())
    except (OSError, ValueError):
        return None
    return _VALID_CRITERION_IDS_CACHE


def _load_valid_prompt_template_ids() -> frozenset[str] | None:
    global _VALID_PROMPT_TEMPLATE_IDS_CACHE
    if _VALID_PROMPT_TEMPLATE_IDS_CACHE is not None:
        return _VALID_PROMPT_TEMPLATE_IDS_CACHE
    try:
        templates = _load_prompt_templates(DEFAULT_PROMPT_REGISTRY)
    except (OSError, ValueError):
        return None
    _VALID_PROMPT_TEMPLATE_IDS_CACHE = frozenset(
        str(template.get("id", "")).strip()
        for template in templates
        if str(template.get("id", "")).strip()
    )
    return _VALID_PROMPT_TEMPLATE_IDS_CACHE


def _load_valid_standards_ids() -> frozenset[str] | None:
    global _VALID_STANDARDS_IDS_CACHE
    if _VALID_STANDARDS_IDS_CACHE is not None:
        return _VALID_STANDARDS_IDS_CACHE
    try:
        loaded = _load_json(ROOT / "config" / "standards" / "registry.json")
    except (OSError, ValueError):
        return None
    standards = loaded.get("standards")
    if not isinstance(standards, list):
        return None
    _VALID_STANDARDS_IDS_CACHE = frozenset(
        str(row.get("id", "")).strip()
        for row in standards
        if isinstance(row, dict) and str(row.get("id", "")).strip()
    )
    return _VALID_STANDARDS_IDS_CACHE


def validate_workflow_bindings(
    workflows: dict[str, WorkflowSpec],
    skills: dict[str, SkillSpec],
) -> list[str]:
    errors: list[str] = []
    valid_criterion_ids = _load_valid_criterion_ids()
    valid_prompt_template_ids = _load_valid_prompt_template_ids()
    valid_standards_ids = _load_valid_standards_ids()
    for workflow in workflows.values():
        seen_stage_keys: set[str] = set()
        validation_count = 0
        for stage in workflow.stages:
            if not stage.key:
                errors.append(f"Workflow {workflow.key} has a stage with an empty key.")
                continue
            if stage.key in seen_stage_keys:
                errors.append(f"Workflow {workflow.key} has duplicate stage key {stage.key}.")
            seen_stage_keys.add(stage.key)

            if not stage.kind:
                errors.append(f"Workflow {workflow.key} stage {stage.key} has an empty kind.")
            for skill_key in stage.required_skills:
                spec = skills.get(skill_key)
                if spec is None:
                    errors.append(
                        f"Workflow {workflow.key} stage {stage.key} references unknown skill {skill_key}."
                    )
                    continue
                if stage.kind not in spec.allowed_stages:
                    errors.append(
                        f"Workflow {workflow.key} stage {stage.key} kind {stage.kind} is not allowed for skill {skill_key}."
                    )
            validation_count += len(stage.validations)
            if valid_criterion_ids is None and stage.validations:
                errors.append(
                    f"workflow={workflow.key} stage={stage.key} skipped: criteria registry unavailable"
                )
            elif valid_criterion_ids is not None:
                for validation in stage.validations:
                    if validation.criterion_id not in valid_criterion_ids:
                        errors.append(
                            f"workflow={workflow.key} stage={stage.key} validation criterion_id={validation.criterion_id!r} does not resolve in success-criteria registry"
                        )
            if valid_prompt_template_ids is None and stage.prompt_bindings:
                errors.append(
                    f"workflow={workflow.key} stage={stage.key} skipped: prompt registry unavailable"
                )
            elif valid_prompt_template_ids is not None:
                for prompt_binding in stage.prompt_bindings:
                    if prompt_binding.template_id not in valid_prompt_template_ids:
                        errors.append(
                            f"workflow={workflow.key} stage={stage.key} prompt_binding template_id={prompt_binding.template_id!r} does not resolve in prompts/registry.json"
                        )
            if valid_standards_ids is None and stage.standards_bindings:
                errors.append(
                    f"workflow={workflow.key} stage={stage.key} skipped: standards registry unavailable"
                )
            elif valid_standards_ids is not None:
                for standard_id in stage.standards_bindings:
                    if standard_id not in valid_standards_ids:
                        errors.append(
                            f"workflow={workflow.key} stage={stage.key} standards_binding {standard_id!r} does not resolve in standards registry"
                        )
            for approval_gate in stage.approval_gates:
                if approval_gate.impact_scope not in _ALLOWED_IMPACT_SCOPES:
                    errors.append(
                        f"workflow={workflow.key} stage={stage.key} approval_gate impact_scope={approval_gate.impact_scope!r} is invalid"
                    )

        if workflow.required_validations:
            validate_stage = next(
                (stage for stage in workflow.stages if stage.kind == "validate"), None
            )
            if validate_stage is None:
                errors.append(
                    f"Workflow {workflow.key} declares required validations without a validate stage."
                )
            else:
                missing = [
                    key
                    for key in workflow.required_validations
                    if key not in validate_stage.required_skills
                ]
                if missing:
                    errors.append(
                        f"Workflow {workflow.key} missing required validation skills in validate stage: {', '.join(missing)}"
                    )
        if workflow.lifecycle_state in {"approved", "active"} and validation_count == 0:
            errors.append(
                f"workflow={workflow.key} lifecycle_state={workflow.lifecycle_state} declares zero validations across its stages; approved/active workflows must declare at least one validation (RESEARCH Pitfall 1)"
            )
        if workflow.verification_exempt and not workflow.verification_exempt_reason:
            errors.append(
                f"workflow={workflow.key} verification_exempt=true requires verification_exempt_reason"
            )
    return errors


def _default_workflow_approval_policy(**_: Any) -> dict[str, Any]:
    return {
        "policy_class": "workflow-default_change",
        "requires_approval": True,
        "reason": "workflow-default changes require approval before promotion.",
    }


def recommend_workflow_from_health(
    *,
    delta_items: list[dict[str, Any]],
    registry_workflows: set[str] | None = None,
    workflow_registry_path: Path | None = None,
    approval_policy_fn: Callable[..., dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not delta_items:
        return []
    if registry_workflows is None:
        registry_workflows = set(load_workflow_registry(workflow_registry_path))
    policy_fn = approval_policy_fn or _default_workflow_approval_policy

    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()
    sorted_items = sorted(
        delta_items,
        key=lambda item: float(item.get("priority_score", 0.0) or 0.0),
        reverse=True,
    )
    for item in sorted_items:
        workflow_key = ""
        rationale = ""
        for predicate, candidate_key, candidate_rationale in HEALTH_TO_WORKFLOW_RULES:
            if predicate(item):
                workflow_key = candidate_key
                rationale = candidate_rationale
                break
        if not workflow_key or workflow_key in seen:
            continue
        seen.add(workflow_key)
        try:
            policy = policy_fn(
                layer_type="workflow",
                impact_scope="workflow-default",
                proposed_change={"workflow_key": workflow_key},
            )
        except Exception:
            policy = _default_workflow_approval_policy()
        recommendations.append(
            {
                "workflow_key": workflow_key,
                "rationale": rationale,
                "available_in_registry": workflow_key in registry_workflows,
                "requires_approval": bool(policy.get("requires_approval", True)),
                "impact_scope": "workflow-default",
                "policy_class": str(policy.get("policy_class", "workflow-default_change")),
                "triggered_by": {
                    "standard_id": str(item.get("standard_id", "")),
                    "domain": str(item.get("domain", "")),
                    "priority_bucket": str(item.get("priority_bucket", "")),
                    "priority_score": float(item.get("priority_score", 0.0) or 0.0),
                },
            }
        )
        if len(recommendations) >= 5:
            break
    return recommendations


def _word_set(text: str | None) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(word.lower())}(?![a-z0-9])", text) is not None


def _has_any_word(text: str, words: set[str]) -> bool:
    return any(_has_word(text, word) for word in words)


def _matched_phrases(text: str, phrases: tuple[str, ...] | list[str]) -> list[str]:
    return sorted(
        {phrase.lower() for phrase in phrases if phrase.strip() and phrase.lower() in text}
    )


def _load_prompt_templates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    loaded = _load_json(path)
    templates = loaded.get("templates")
    if not isinstance(templates, list):
        return []
    return [item for item in templates if isinstance(item, dict)]


def rank_workflow_candidates(
    objective: str,
    *,
    workflow_registry_path: Path | None = None,
) -> list[WorkflowRouteCandidate]:
    workflows = load_workflow_registry(workflow_registry_path)
    objective_text = objective.lower()
    implementation_terms = {
        "api",
        "build",
        "bug",
        "ci",
        "db",
        "feature",
        "fix",
        "implement",
        "refactor",
        "ship",
        "test",
        "tests",
        "ui",
        "verify",
    }
    recovery_terms = {
        "broken",
        "crash",
        "debug",
        "error",
        "failing",
        "failure",
        "flaky",
        "regression",
    }
    analysis_terms = {
        "analyze",
        "architecture",
        "audit",
        "investigate",
        "investigation",
        "review",
        "strategy",
    }
    expert_review_terms = {
        "expert",
        "expertise",
        "remediation",
        "rubric",
        "scorecard",
        "tmcp",
    }
    routing_diagnostic_terms = {
        "candidate",
        "coverage",
        "evidence",
        "picked",
        "route",
        "routing",
        "scorer",
        "scoring",
        "selected",
        "shadow",
    }
    content_terms = {"academic", "article", "citations", "draft", "essay", "paper", "write"}
    transformation_terms = {"creative", "humanize", "outreach", "prompt", "rewrite", "voice"}
    implementation_evidence = _has_any_word(objective_text, implementation_terms)
    recovery_evidence = _has_any_word(objective_text, recovery_terms)
    analysis_evidence = _has_any_word(objective_text, analysis_terms)
    expert_review_evidence = _has_any_word(objective_text, expert_review_terms)
    routing_diagnostic_evidence = _has_any_word(objective_text, routing_diagnostic_terms) or any(
        phrase in objective_text
        for phrase in (
            "doesn't make sense",
            "doesnt make sense",
            "doesnt really make sense",
            "incorrect workflow",
            "wrong workflow",
        )
    )
    audit_plan_evidence = any(
        phrase in objective_text
        for phrase in (
            "audit and plan",
            "audit-and-plan",
            "audit_and_plan",
            "remediation plan",
        )
    )
    content_evidence = _has_any_word(objective_text, content_terms)
    transformation_evidence = _has_any_word(objective_text, transformation_terms)
    candidates: list[WorkflowRouteCandidate] = []

    for workflow in workflows.values():
        matched_terms = _matched_phrases(objective_text, workflow.trigger_hints)
        score = len(matched_terms) * 4
        evidence_reasons = [f"matched trigger hint {term!r}" for term in matched_terms]
        if workflow.workflow_family == "audit_and_implement" and implementation_evidence:
            score += 6
            evidence_reasons.append("implementation evidence")
        if workflow.workflow_family == "failure_recovery" and recovery_evidence:
            score += 7
            evidence_reasons.append("failure-recovery evidence")
            if implementation_evidence:
                score += 1
        if workflow.workflow_family == "audit_only" and analysis_evidence:
            score += 5
            evidence_reasons.append("analysis/audit evidence")
            if implementation_evidence or recovery_evidence:
                score -= 3
        if (
            workflow.workflow_family == "audit_and_plan"
            and (expert_review_evidence or audit_plan_evidence)
            and (analysis_evidence or audit_plan_evidence)
        ):
            score += 11
            evidence_reasons.append("expert audit-plan evidence")
            if implementation_evidence:
                score -= 2
        if (
            workflow.workflow_family == "content_generation"
            and content_evidence
            and not (implementation_evidence or recovery_evidence)
            and not (
                (
                    expert_review_evidence
                    or audit_plan_evidence
                    or (workflow.key.lower() in objective_text and routing_diagnostic_evidence)
                )
                and not matched_terms
            )
        ):
            score += 7
            evidence_reasons.append("content-generation evidence")
        if (
            workflow.workflow_family == "writing_transformation"
            and transformation_evidence
            and not (implementation_evidence or recovery_evidence)
        ):
            score += 7
            evidence_reasons.append("writing-transformation evidence")
        if score > 0 and workflow.lifecycle_state == "active":
            score += 1
        if score <= 0:
            continue
        candidates.append(
            WorkflowRouteCandidate(
                workflow_key=workflow.key,
                workflow_family=workflow.workflow_family,
                score=score,
                matched_terms=tuple(matched_terms),
                rationale=(
                    f"Matched {', '.join(evidence_reasons)} for workflow_family={workflow.workflow_family}."
                ),
            )
        )

    if implementation_evidence and not any(
        candidate.workflow_key == "implementation-delivery" for candidate in candidates
    ):
        workflow = workflows.get("implementation-delivery")
        if workflow is not None:
            candidates.append(
                WorkflowRouteCandidate(
                    workflow_key=workflow.key,
                    workflow_family=workflow.workflow_family,
                    score=6 + (1 if workflow.lifecycle_state == "active" else 0),
                    matched_terms=(),
                    rationale="Matched implementation evidence via code-work fallback.",
                )
            )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.workflow_key))
    return candidates


def _recommend_backend_for_task_family(
    task_family: str | None,
    *,
    surface: str,
) -> dict[str, Any] | None:
    if not task_family:
        return None
    try:
        return recommend_execution_surface(
            task_family=task_family, preferred_surfaces=(surface, "claude_code")
        )
    except StrategySelectionError as exc:
        return {
            "task_family": task_family,
            "selected_surface": None,
            "selected_strategy_id": None,
            "alternatives": [],
            "route_status": "missing",
            "rationale": f"No execution strategy is registered for task_family={task_family}: {exc}",
        }


def _semantic_route_payload(
    *,
    objective: str,
    semantic: dict[str, Any],
    surface: str,
    workflow_registry_path: Path | None,
    prompt_registry_path: Path | None,
) -> dict[str, Any]:
    workflow_key = str(semantic["selected_workflow"])
    workflow_family = str(semantic["workflow_family"])
    task_family = WORKFLOW_TASK_FAMILIES.get(workflow_key)
    prompt_recommendation = recommend_prompt_family(
        objective=objective,
        workflow_key=workflow_key,
        prompt_registry_path=prompt_registry_path,
        workflow_registry_path=workflow_registry_path,
    )
    backend_recommendation = _recommend_backend_for_task_family(task_family, surface=surface)
    return {
        "objective": objective,
        "selected_workflow": {
            "workflow_key": workflow_key,
            "workflow_family": workflow_family,
            "score": 0,
            "routing_source": "semantic_reasoner",
            "semantic_confidence": semantic["confidence"],
            "rationale": semantic["rationale"],
        },
        "workflow_candidates": [],
        "prompt_recommendation": prompt_recommendation,
        "backend_recommendation": backend_recommendation,
        "semantic_recommendation": semantic,
    }


def recommend_prompt_family(
    *,
    objective: str,
    workflow_key: str,
    prompt_registry_path: Path | None = None,
    workflow_registry_path: Path | None = None,
) -> dict[str, Any]:
    workflows = load_workflow_registry(workflow_registry_path)
    workflow = workflows.get(workflow_key)
    if workflow is None:
        raise ValueError(f"Unknown workflow key: {workflow_key}")

    prompt_path = prompt_registry_path or DEFAULT_PROMPT_REGISTRY
    templates = _load_prompt_templates(prompt_path)
    objective_words = _word_set(objective)
    ranked: list[tuple[int, dict[str, Any]]] = []

    for template in templates:
        prompt_family = str(template.get("prompt_family", "")).strip()
        if not prompt_family:
            continue
        score = 0
        applicable = template.get("applicable_workflow_families") or []
        if isinstance(applicable, list) and workflow.workflow_family in {
            str(row) for row in applicable
        }:
            score += 4
        classification = str(template.get("classification", "")).lower()
        if workflow.workflow_family == "failure_recovery" and classification == "debug":
            score += 2
        if workflow.workflow_family == "audit_only" and classification == "plan":
            score += 2
        tags = template.get("tags") or []
        if isinstance(tags, list):
            score += len(
                objective_words & {str(tag).lower() for tag in tags if isinstance(tag, str)}
            )
        if score > 0:
            ranked.append((score, template))

    ranked.sort(key=lambda row: (-row[0], str(row[1].get("id", ""))))
    if not ranked:
        return {
            "workflow_key": workflow_key,
            "workflow_family": workflow.workflow_family,
            "prompt_family": None,
            "template_id": None,
            "route_status": "missing",
            "rationale": "No prompt family matched the selected workflow family and objective tokens.",
        }

    _, selected = ranked[0]
    alternatives = [
        {
            "template_id": str(template.get("id", "")),
            "prompt_family": str(template.get("prompt_family", "")),
            "route_status": str(template.get("route_status", _prompt_lifecycle_state(template))),
            "lifecycle_state": _prompt_lifecycle_state(template),
        }
        for _, template in ranked[1:3]
    ]
    lifecycle_state = _prompt_lifecycle_state(selected)
    return {
        "workflow_key": workflow_key,
        "workflow_family": workflow.workflow_family,
        "prompt_family": str(selected.get("prompt_family", "")),
        "template_id": str(selected.get("id", "")),
        "route_status": str(selected.get("route_status", lifecycle_state)),
        "lifecycle_state": lifecycle_state,
        "alternatives": alternatives,
        "rationale": (
            f"Selected prompt family {selected.get('prompt_family')} for workflow_family={workflow.workflow_family} "
            f"using applicable_workflow_families metadata and objective-tag overlap."
        ),
    }


def recommend_route_primitives(
    objective: str,
    *,
    surface: str = "codex",
    workflow_registry_path: Path | None = None,
    prompt_registry_path: Path | None = None,
    semantic_reasoner: SemanticWorkflowReasoner | None = None,
) -> dict[str, Any]:
    workflows = load_workflow_registry(workflow_registry_path)
    candidates = rank_workflow_candidates(objective, workflow_registry_path=workflow_registry_path)
    semantic_reasoner = semantic_reasoner or configured_semantic_reasoner()
    if not candidates:
        semantic = semantic_recommendation(
            objective=objective,
            workflows=workflows,
            candidates=candidates,
            semantic_reasoner=semantic_reasoner,
        )
        if semantic and semantic.get("status") == "usable":
            return _semantic_route_payload(
                objective=objective,
                semantic=semantic,
                surface=surface,
                workflow_registry_path=workflow_registry_path,
                prompt_registry_path=prompt_registry_path,
            )
        return {
            "objective": objective,
            "selected_workflow": None,
            "workflow_candidates": [],
            "prompt_recommendation": None,
            "backend_recommendation": None,
            "semantic_recommendation": semantic,
            "blocked_reason": (
                "Semantic workflow confidence was below the route threshold."
                if semantic
                else "No deterministic or semantic workflow matched the objective."
            ),
        }

    selected = candidates[0]
    runner_up = candidates[1] if len(candidates) > 1 else None
    if selected.score < 4 or (runner_up is not None and runner_up.score >= selected.score):
        semantic = semantic_recommendation(
            objective=objective,
            workflows=workflows,
            candidates=candidates,
            semantic_reasoner=semantic_reasoner,
        )
        if semantic and semantic.get("status") == "usable":
            return _semantic_route_payload(
                objective=objective,
                semantic=semantic,
                surface=surface,
                workflow_registry_path=workflow_registry_path,
                prompt_registry_path=prompt_registry_path,
            )
        return {
            "objective": objective,
            "selected_workflow": None,
            "workflow_candidates": [
                {
                    "workflow_key": candidate.workflow_key,
                    "workflow_family": candidate.workflow_family,
                    "score": candidate.score,
                    "matched_terms": list(candidate.matched_terms),
                    "rationale": candidate.rationale,
                }
                for candidate in candidates
            ],
            "prompt_recommendation": None,
            "backend_recommendation": None,
            "semantic_recommendation": semantic,
            "blocked_reason": "Workflow evidence was weak or tied; route needs clarification.",
        }
    task_family = WORKFLOW_TASK_FAMILIES.get(selected.workflow_key)
    prompt_recommendation = recommend_prompt_family(
        objective=objective,
        workflow_key=selected.workflow_key,
        prompt_registry_path=prompt_registry_path,
        workflow_registry_path=workflow_registry_path,
    )
    backend_recommendation = _recommend_backend_for_task_family(task_family, surface=surface)
    return {
        "objective": objective,
        "selected_workflow": {
            "workflow_key": selected.workflow_key,
            "workflow_family": selected.workflow_family,
            "score": selected.score,
            "rationale": selected.rationale,
        },
        "workflow_candidates": [
            {
                "workflow_key": candidate.workflow_key,
                "workflow_family": candidate.workflow_family,
                "score": candidate.score,
                "matched_terms": list(candidate.matched_terms),
                "rationale": candidate.rationale,
            }
            for candidate in candidates
        ],
        "prompt_recommendation": prompt_recommendation,
        "backend_recommendation": backend_recommendation,
    }


def _select_prompt_template(
    objective: str, workflow_key: str, templates: list[dict[str, Any]]
) -> str | None:
    objective_words = _word_set(objective)
    best_id: str | None = None
    best_score = -1

    for template in templates:
        template_id = str(template.get("id", "")).strip()
        if not template_id:
            continue
        score = 0
        classification = str(template.get("classification", "")).lower()
        if workflow_key == "academic_paper_v1" and classification in {
            "research",
            "content_writing",
        }:
            score += 3
        tags = template.get("tags") or []
        if isinstance(tags, list):
            score += len(
                objective_words & {str(tag).lower() for tag in tags if isinstance(tag, str)}
            )
        if score > best_score:
            best_score = score
            best_id = template_id
    return best_id


def _normalize_prompt(
    state: dict[str, Any],
    *,
    objective: str,
    workflow_key: str,
    surface: str,
    prompt_registry_path: Path,
) -> dict[str, Any]:
    templates = _load_prompt_templates(prompt_registry_path)
    template_id = _select_prompt_template(objective, workflow_key, templates)
    strategy_bundle: dict[str, Any] | None = None
    task_family = WORKFLOW_TASK_FAMILIES.get(workflow_key)
    if task_family:
        try:
            strategy_bundle = compile_execution_strategy(
                objective=objective,
                task_family=task_family,
                surface=surface,
            )
        except StrategySelectionError:
            strategy_bundle = None
    normalized = (
        f"Objective: {objective.strip()}\n"
        f"Workflow: {workflow_key}\n"
        "Deliverable: Provide structured output that preserves factual meaning and explicit evidence references."
    )
    if strategy_bundle:
        normalized += (
            f"\nStrategy: {strategy_bundle['strategy_id']} "
            f"v{strategy_bundle['strategy_version']} ({strategy_bundle['surface']})"
        )
    if template_id:
        normalized += f"\nTemplate: {template_id}"
    agent_rules = state.get("agent_rules") or []
    if agent_rules:
        normalized += "\nAgent rules: " + "; ".join(
            str(rule.get("title")) for rule in agent_rules[:6]
        )
    state["template_id"] = template_id
    state["execution_strategy"] = strategy_bundle
    state["normalized_prompt"] = normalized
    return {
        "template_id": template_id,
        "strategy_id": strategy_bundle.get("strategy_id") if strategy_bundle else None,
        "normalized_prompt": normalized,
    }


def _retrieve_style_profile(vault_root: Path | None) -> tuple[dict[str, Any], list[str]]:
    fallback = {
        "tone": "direct-academic",
        "formality": "high",
        "sentence_rhythm": "varied",
        "avoid": ["generic filler", "unsupported claims", "overstated certainty"],
    }
    if vault_root is None or not vault_root.exists():
        return fallback, ["Vault unavailable; used deterministic fallback style profile."]

    notes: list[str] = []
    sampled = 0
    for path in sorted(vault_root.rglob("*.md")):
        notes.append(str(path.relative_to(vault_root)))
        sampled += 1
        if sampled >= 5:
            break

    profile = {
        **fallback,
        "source": "obsidian-corpus",
        "sampled_notes": sampled,
    }
    if sampled == 0:
        notes.append("No markdown notes found; fallback profile retained.")
    return profile, notes


def _generate_academic_draft(state: dict[str, Any], objective: str) -> str:
    draft = "\n".join(
        [
            f"# Working Title: {objective}",
            "",
            "## Introduction",
            "This paper frames the objective and stakes with a focused thesis [1].",
            "",
            "## Literature Review",
            "Relevant prior work establishes the current baseline and unresolved constraints [2].",
            "",
            "## Analysis",
            "The argument is developed in ordered claims tied to explicit evidence and scoped assumptions [3].",
            "",
            "## Conclusion",
            "The final section summarizes findings, limitations, and next validation steps [4].",
            "",
            "## References",
            "[1] Source placeholder.",
            "[2] Source placeholder.",
            "[3] Source placeholder.",
            "[4] Source placeholder.",
        ]
    )
    state["draft_text"] = draft
    return draft


def _humanize_draft(state: dict[str, Any]) -> str:
    draft = str(state.get("draft_text", "")).strip()
    if not draft:
        return ""

    lines = []
    for raw_line in draft.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line.startswith("#") or not line:
            lines.append(raw_line)
            continue
        line = line.replace("This paper", "The paper")
        line = line.replace("The final section", "The conclusion")
        lines.append(line)

    humanized = "\n".join(lines)
    state["humanized_text"] = humanized
    return humanized


def _validate_structure(text: str) -> dict[str, Any]:
    required = [
        "## Introduction",
        "## Literature Review",
        "## Analysis",
        "## Conclusion",
        "## References",
    ]
    missing = [heading for heading in required if heading not in text]
    return {
        "passed": len(missing) == 0,
        "issues": [f"Missing required heading: {heading}" for heading in missing],
    }


def _validate_citations(text: str) -> dict[str, Any]:
    markers = re.findall(r"\[[0-9]+\]", text)
    passed = len(markers) > 0
    issues = [] if passed else ["No citation markers found in final output."]
    return {
        "passed": passed,
        "issues": issues,
        "citation_marker_count": len(markers),
    }


def _validate_meaning_preservation(draft_text: str, humanized_text: str) -> dict[str, Any]:
    draft_tokens = _word_set(draft_text)
    final_tokens = _word_set(humanized_text)
    if not draft_tokens:
        return {
            "passed": False,
            "issues": ["Draft text missing for meaning-preservation check."],
            "overlap_ratio": 0.0,
        }
    overlap_ratio = len(draft_tokens & final_tokens) / len(draft_tokens)
    passed = overlap_ratio >= 0.55
    issues = [] if passed else [f"Keyword overlap ratio below threshold: {overlap_ratio:.2f}"]
    return {
        "passed": passed,
        "issues": issues,
        "overlap_ratio": round(overlap_ratio, 3),
    }


def _validate_scope(objective: str, output_text: str) -> dict[str, Any]:
    objective_tokens = _word_set(objective)
    output_tokens = _word_set(output_text)
    overlap = objective_tokens & output_tokens
    passed = len(overlap) > 0
    issues = (
        [] if passed else ["Output does not reference objective terms and appears out-of-scope."]
    )
    return {
        "passed": passed,
        "issues": issues,
        "overlap_tokens": sorted(overlap),
    }


def _execute_learned_workflow_skill(
    skill: SkillSpec,
    *,
    state: dict[str, Any],
    context: WorkflowExecutionContext,
) -> dict[str, Any]:
    normalized_prompt = str(state.get("normalized_prompt") or context.objective).strip()
    evidence = [
        invariant
        for invariant in skill.invariants
        if invariant.lower().startswith("use the learned pattern")
        or invariant.lower().startswith("return explicit evidence")
    ]
    result_text = "\n".join(
        [
            f"Objective: {context.objective.strip()}",
            f"Skill: {skill.key}",
            f"Purpose: {skill.purpose}",
            "",
            "Execution contract:",
            normalized_prompt,
            "",
            "Result:",
            "Apply the learned workflow pattern to produce an evidence-backed, scope-bounded response.",
        ]
    )
    state["result_text"] = result_text
    state["learned_workflow_skill"] = skill.key
    state["learned_workflow_evidence"] = evidence
    return {
        "result_text": result_text,
        "evidence": evidence,
    }


def _execute_skill(
    skill: SkillSpec,
    stage: StageSpec,
    *,
    state: dict[str, Any],
    context: WorkflowExecutionContext,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if skill.key == "prompt_library_normalizer":
        prompt_path = (
            Path(context.prompt_registry_path)
            if context.prompt_registry_path
            else DEFAULT_PROMPT_REGISTRY
        )
        output = _normalize_prompt(
            state,
            objective=context.objective,
            workflow_key=context.workflow_key,
            surface=context.surface,
            prompt_registry_path=prompt_path,
        )
        return output, None

    if skill.key == "agentize_intent_compiler":
        packet = agentize_request(context.objective)
        packet_json = packet.to_dict()
        state["agentized_task_packet"] = packet_json
        state["normalized_prompt"] = packet.to_json()
        return {
            "packet_id": packet.packet_id,
            "execution_mode": packet.execution_mode.mode.value,
            "classifications": [
                classification.value for classification in packet.task_classifications
            ],
        }, None

    if skill.key == "obsidian_corpus_retriever":
        vault_candidate = context.vault_root
        vault_path = Path(vault_candidate).expanduser() if vault_candidate else None
        style_profile, evidence_notes = _retrieve_style_profile(vault_path)
        state["style_profile"] = style_profile
        state["evidence_notes"] = evidence_notes
        return {"style_profile": style_profile, "evidence_notes": evidence_notes}, None

    if skill.key == "academic_draft_generator":
        draft = _generate_academic_draft(state, context.objective)
        return {"draft_text": draft}, None

    if skill.key == "personal_corpus_humanizer":
        humanized = _humanize_draft(state)
        return {"humanized_text": humanized}, None

    if skill.key == "personalized_humanizer_classifier":
        mode = classify_writing_task(context.objective)
        state["personalized_humanizer_mode"] = mode
        return {"mode": mode}, None

    if skill.key == "personalized_voice_retriever":
        state["personalized_humanizer_examples"] = []
        return {"evidence_refs": []}, None

    if skill.key == "personalized_voice_packet_builder":
        mode = cast(
            VoiceMode,
            state.get("personalized_humanizer_mode") or classify_writing_task(context.objective),
        )
        profile_path = ROOT / "config" / "personalized-humanizer" / "profile.json"
        profile = _load_json(profile_path)
        packet = build_voice_packet(profile, mode=mode, examples=[])
        packet_json = {
            "mode": packet.mode,
            "profile_version": packet.profile_version,
            "tone": packet.tone,
            "rules": list(packet.rules),
            "anti_rules": list(packet.anti_rules),
            "evidence_refs": list(packet.evidence_refs),
            "confidence": packet.confidence,
        }
        state["personalized_voice_packet"] = packet
        state["personalized_voice_packet_json"] = packet_json
        return {"voice_packet": packet_json}, None

    if skill.key == "personalized_humanizer_transformer":
        packet = state.get("personalized_voice_packet")
        if packet is None:
            profile = _load_json(ROOT / "config" / "personalized-humanizer" / "profile.json")
            mode = classify_writing_task(context.objective)
            packet = build_voice_packet(profile, mode=mode, examples=[])
            state["personalized_voice_packet"] = packet
        humanized = transform_text(context.objective, packet)
        state["humanized_text"] = humanized
        return {"humanized_text": humanized}, None

    if skill.key == "personalized_humanizer_quality_checker":
        packet = state.get("personalized_voice_packet")
        if packet is None:
            profile = _load_json(ROOT / "config" / "personalized-humanizer" / "profile.json")
            mode = classify_writing_task(context.objective)
            packet = build_voice_packet(profile, mode=mode, examples=[])
            state["personalized_voice_packet"] = packet
        scorecard, risks = score_quality(
            context.objective,
            str(state.get("humanized_text") or context.objective),
            packet,
        )
        state["personalized_humanizer_scorecard"] = scorecard
        state["personalized_humanizer_risks"] = list(risks)
        return {}, {
            "validation_key": skill.key,
            "passed": scorecard["meaning_preservation"] >= 3
            and scorecard["over_personalization_risk"] <= 1,
            "issues": list(risks),
            "scorecard": scorecard,
        }

    if skill.key == "personalized_humanizer_feedback_collector":
        return {
            "feedback_policy": "Collect user approval, edits, or rejection as evidence; do not mutate profile.",
            "candidate_update_required": False,
        }, None

    if skill.key == "structure_checker":
        result = _validate_structure(
            str(state.get("humanized_text") or state.get("draft_text") or "")
        )
        return {}, {"validation_key": skill.key, **result}

    if skill.key == "citation_checker":
        result = _validate_citations(
            str(state.get("humanized_text") or state.get("draft_text") or "")
        )
        return {}, {"validation_key": skill.key, **result}

    if skill.key == "meaning_preservation_checker":
        result = _validate_meaning_preservation(
            str(state.get("draft_text", "")),
            str(state.get("humanized_text") or state.get("draft_text") or ""),
        )
        return {}, {"validation_key": skill.key, **result}

    if skill.key == "tmcp_expertise_compiler":
        packet = state.get("tmcp_packet")
        if not isinstance(packet, dict):
            raise ValueError("tmcp_expertise_compiler requires context.tmcp_packet")
        state["expertise_packet"] = packet
        return {"expertise_packet": packet}, {
            "validation_key": "tmcp_packet_compiled",
            "passed": True,
            "issues": [],
        }

    if skill.key == "expert_rubric_synthesizer":
        packet = state.get("expertise_packet") or state.get("tmcp_packet")
        if not isinstance(packet, dict):
            raise ValueError("expert_rubric_synthesizer requires expertise_packet")
        rubric = synthesize_rubric(
            packet=packet,
            run_id=context.run_id or "expert-review-preview",
            objective=context.objective,
        )
        state["expert_rubric"] = rubric
        return {"rubric": rubric}, None

    if skill.key == "expert_evidence_auditor":
        rubric = state.get("expert_rubric")
        if not isinstance(rubric, dict):
            raise ValueError("expert_evidence_auditor requires expert_rubric")
        evidence_items = state.get("review_evidence_items", [])
        audit_report = build_audit_report(
            rubric=rubric,
            evidence_items=evidence_items if isinstance(evidence_items, list) else [],
            run_id=context.run_id or "expert-review-preview",
        )
        state["expert_audit_report"] = audit_report
        return {"audit_report": audit_report}, None

    if skill.key == "expert_remediation_planner":
        audit_report = state.get("expert_audit_report")
        if not isinstance(audit_report, dict):
            raise ValueError("expert_remediation_planner requires expert_audit_report")
        remediation_plan = build_remediation_plan(
            audit_report=audit_report,
            run_id=context.run_id or "expert-review-preview",
        )
        state["expert_remediation_plan"] = remediation_plan
        return {"remediation_plan": remediation_plan}, None

    if skill.key == "expert_implementation_handoff_builder":
        remediation_plan = state.get("expert_remediation_plan")
        if not isinstance(remediation_plan, dict):
            raise ValueError(
                "expert_implementation_handoff_builder requires expert_remediation_plan"
            )
        run_id = context.run_id or "expert-review-preview"
        handoff = build_implementation_handoff(
            remediation_plan=remediation_plan,
            run_id=run_id,
            selected_slice_id=context.selected_slice_id,
        )
        output_dir = Path(context.repo_path or ".") / ".aios" / "reviews" / run_id
        paths = write_review_artifacts(
            output_dir=output_dir,
            expertise_packet=state.get("expertise_packet") or state.get("tmcp_packet") or {},
            rubric=state.get("expert_rubric") or {},
            audit_report=state.get("expert_audit_report") or {},
            remediation_plan=remediation_plan,
            implementation_handoff=handoff,
        )
        state["expert_implementation_handoff"] = handoff
        state["expert_review_artifact_paths"] = {key: str(path) for key, path in paths.items()}
        return {
            "implementation_handoff": handoff,
            "artifact_paths": state["expert_review_artifact_paths"],
        }, None

    if skill.key == "tmcp_packet_compiled":
        packet = state.get("expertise_packet") or state.get("tmcp_packet")
        passed = isinstance(packet, dict) and bool(packet.get("selected_nodes"))
        issues = [] if passed else ["TMCP expertise packet is missing selected nodes."]
        return {}, {"validation_key": "tmcp_packet_compiled", "passed": passed, "issues": issues}

    if skill.key == "rubric_dimensions_present":
        rubric = state.get("expert_rubric")
        return {}, validate_rubric(rubric if isinstance(rubric, dict) else {})

    if skill.key == "findings_have_evidence":
        audit_report = state.get("expert_audit_report")
        return {}, validate_audit_report(audit_report if isinstance(audit_report, dict) else {})

    if skill.key == "remediation_has_verification":
        remediation_plan = state.get("expert_remediation_plan")
        return {}, validate_remediation_plan(
            remediation_plan if isinstance(remediation_plan, dict) else {}
        )

    if skill.key == "scope_check":
        result = _validate_scope(
            context.objective,
            str(
                state.get("humanized_text")
                or state.get("draft_text")
                or state.get("result_text")
                or state.get("normalized_prompt")
                or ""
            ),
        )
        return {}, {"validation_key": skill.key, **result}

    if skill.key.endswith("_executor"):
        return _execute_learned_workflow_skill(skill, state=state, context=context), None

    return {}, None


def _build_stage_evaluation_summary(
    *,
    stage_key: str,
    skill_reports: list[dict[str, Any]],
    validations: list[dict[str, Any]],
    stage_issues: list[str],
    stage_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    del skill_reports
    findings = stage_findings or []
    blocker_count = len([finding for finding in findings if finding.get("level") == "blocker"])
    warning_count = len([finding for finding in findings if finding.get("level") == "warning"])
    passed_validations = len([row for row in validations if row.get("passed", False)])
    total_validations = len(validations)
    outcome = "completed"
    if blocker_count > 0:
        outcome = "blocked"
    elif stage_issues or any(not row.get("passed", False) for row in validations):
        outcome = "failed"
    return {
        "stage_key": stage_key,
        "passed_validations": passed_validations,
        "total_validations": total_validations,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "stage_finding_ids": [str(finding.get("id")) for finding in findings if finding.get("id")],
        "outcome": outcome,
    }


def _expand_tmcp_packet_for_stage(
    *,
    conn: sqlite3.Connection | None,
    context: WorkflowExecutionContext,
    stage: StageSpec,
    run_state: dict[str, Any],
) -> dict[str, Any] | None:
    current_packet = run_state.get("tmcp_packet")
    stage_phase = _TMCP_STAGE_PHASES.get(stage.kind)
    if conn is None or stage_phase is None or not isinstance(current_packet, dict):
        return None
    if current_packet.get("phase") == stage_phase:
        return None
    expansion = expand_tmcp_packet_for_requirement_change(
        conn,
        current_packet=current_packet,
        objective=context.objective,
        project_path=context.repo_path or current_packet.get("project_path"),
        context_receipt_id=current_packet.get("context_receipt_id"),
        run_id=context.run_id,
        invocation_id=context.invocation_id,
        session_id=context.session_id,
        phase=stage_phase,
        domain=current_packet.get("domain"),
        reason=f"workflow stage {stage.key} ({stage.kind}) requires {stage_phase} behavior",
    )
    run_state["tmcp_packet"] = expansion["active_packet"]
    expansion_summary = {
        **expansion,
        "stage_key": stage.key,
        "stage_kind": stage.kind,
        "stage_phase": stage_phase,
    }
    run_state.setdefault("tmcp_packet_expansions", []).append(expansion_summary)
    return expansion_summary


def execute_workflow(
    context: WorkflowExecutionContext,
    *,
    workflow_registry_path: Path | None = None,
    skill_registry_path: Path | None = None,
    conn: sqlite3.Connection | None = None,
    stage_artifact_root: Path | None = None,
) -> dict[str, Any]:
    started_at = _now_iso()
    workflows = load_workflow_registry(workflow_registry_path)
    skills = load_skill_registry(skill_registry_path)
    binding_errors = validate_workflow_bindings(workflows, skills)
    if binding_errors:
        raise ValueError("Workflow/skill registry validation failed: " + "; ".join(binding_errors))

    workflow = workflows.get(context.workflow_key)
    if workflow is None:
        raise ValueError(f"Unknown workflow key: {context.workflow_key}")
    rtk_rules = load_compression_rules()
    workflow_modes = rtk_rules.get("workflow_modes", {})
    workflow_rtk_mode = "compressed"
    if isinstance(workflow_modes, dict):
        if context.workflow_key == "failure-recovery":
            workflow_rtk_mode = str(workflow_modes.get("debugging", "adaptive"))
        elif context.workflow_key == "implementation-delivery":
            workflow_rtk_mode = str(workflow_modes.get("code_generation", "compressed"))

    run_state: dict[str, Any] = {
        "objective": context.objective,
        "workflow_key": workflow.key,
        "rtk_mode": workflow_rtk_mode,
        "agent_rules": [{"title": rule.title, "body": rule.body} for rule in load_agent_rules()],
        "tmcp_packet": context.tmcp_packet,
        "review_evidence_items": list(context.evidence_items),
        "selected_slice_id": context.selected_slice_id,
    }
    stages_report: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    unresolved: list[str] = []
    stage_evaluations: list[dict[str, Any]] = []
    validation_execution_map: dict[str, dict[str, Any]] = {}

    for stage in workflow.stages:
        stage_started = _now_iso()
        skill_reports: list[dict[str, Any]] = []
        stage_issues: list[str] = []
        stage_validations: list[dict[str, Any]] = []
        stage_tmcp_expansion = _expand_tmcp_packet_for_stage(
            conn=conn,
            context=context,
            stage=stage,
            run_state=run_state,
        )

        for skill_key in stage.required_skills:
            spec = skills[skill_key]
            output, validation = _execute_skill(
                spec,
                stage,
                state=run_state,
                context=context,
            )
            skill_reports.append(
                {
                    "skill_key": skill_key,
                    "execution_mode": spec.execution_mode,
                    "status": "completed",
                    "output_keys": sorted(output.keys()),
                    "source_path": spec.source_path,
                    "installed_name": spec.installed_name,
                }
            )
            if validation is not None:
                validations.append(validation)
                stage_validations.append(validation)
                if not validation.get("passed", False):
                    stage_issues.extend(validation.get("issues", []))

        stage_status = "completed" if not stage_issues else "failed"
        stage_findings: list[dict[str, Any]] = []
        if conn is not None and context.run_id:
            criteria_context = success_criteria.infer_context(
                objective=context.objective,
                prompt_classifications=[workflow.workflow_family, workflow.key],
                changed_files=[],
                skills=stage.required_skills,
            )
            criteria_context["workflow_key"] = workflow.key
            criteria_context["stage_key"] = stage.key
            criteria_context["stage_kind"] = stage.kind
            criteria = success_criteria.resolve_applicable_criteria(
                registry=success_criteria.load_registry(),
                context=criteria_context,
                skill_map=success_criteria.load_skill_map(),
            )
            findings = success_criteria.evaluate_stage_findings(
                criteria=criteria,
                context=criteria_context,
                stage_key=stage.key,
                stage_kind=stage.kind,
                run_state=run_state,
            )
            stage_eval_summary = success_criteria.persist_stage_findings(
                conn,
                run_id=context.run_id,
                stage_key=stage.key,
                stage_kind=stage.kind,
                findings=findings,
                artifact_root=stage_artifact_root or success_criteria.ARTIFACTS_DIR,
            )
            stage_eval_summary["stage_key"] = stage.key
            stage_eval_summary["stage_kind"] = stage.kind
            if stage_eval_summary["blocker_count"] > 0:
                stage_status = "failed"
            elif stage_eval_summary["warning_count"] > 0 and stage_status == "completed":
                stage_status = "warning"
            try:
                rows = conn.execute(
                    """
                    SELECT id, level, summary
                    FROM success_criteria_stage_findings
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (context.run_id, stage.key),
                ).fetchall()
                stage_findings = [
                    {"id": row[0], "level": row[1], "summary": row[2]} for row in rows
                ]
            except sqlite3.OperationalError:
                stage_findings = []
        stage_eval_summary = _build_stage_evaluation_summary(
            stage_key=stage.key,
            skill_reports=skill_reports,
            validations=stage_validations,
            stage_issues=stage_issues,
            stage_findings=stage_findings,
        )
        if stage_eval_summary["outcome"] in {"blocked", "failed"}:
            stage_status = "failed"
        elif stage_eval_summary["warning_count"] > 0 and stage_status == "completed":
            stage_status = "warning"
        stage_evaluations.append(stage_eval_summary)
        if stage_issues:
            unresolved.extend(stage_issues)

        if stage.kind == "validate":
            stage_passed = stage_eval_summary["outcome"] not in {"blocked", "failed"}
            for skill_report in skill_reports:
                skill_key = skill_report.get("skill_key")
                if not skill_key or skill_report.get("status") != "completed":
                    continue
                validation_execution_map[str(skill_key)] = {
                    "validation_key": str(skill_key),
                    "passed": stage_passed,
                    "issues": list(stage_issues),
                    "source": "validate_stage_skill_execution",
                    "stage_key": stage.key,
                    "stage_outcome": stage_eval_summary["outcome"],
                }

        stages_report.append(
            {
                "stage_key": stage.key,
                "kind": stage.kind,
                "status": stage_status,
                "rtk_mode": workflow_rtk_mode
                if stage.kind in {"generate", "validate", "finalize"}
                else "compressed",
                "skills": skill_reports,
                "issues": stage_issues,
                "tmcp_expansion": stage_tmcp_expansion,
                "stage_evaluation": stage_eval_summary,
                "started_at": stage_started,
                "ended_at": _now_iso(),
            }
        )

    required_validation_map = {
        row["validation_key"]: row
        for row in validations
        if isinstance(row, dict) and row.get("validation_key")
    }
    for key, row in validation_execution_map.items():
        required_validation_map.setdefault(key, row)
    missing_validations = [
        key for key in workflow.required_validations if key not in required_validation_map
    ]
    for key in missing_validations:
        unresolved.append(f"Required validation did not run: {key}")

    failed_required = [
        key
        for key in workflow.required_validations
        if not required_validation_map.get(key, {}).get("passed", False)
    ]

    status = "completed"
    if unresolved or failed_required:
        status = "failed"

    report = {
        "report_id": f"workflow-report-{uuid.uuid4()}",
        "run_id": context.run_id,
        "invocation_id": context.invocation_id,
        "workflow_key": workflow.key,
        "workflow_name": workflow.name,
        "objective": context.objective,
        "status": status,
        "stages": stages_report,
        "validations": validations,
        "stage_evaluations": stage_evaluations,
        "required_validations": list(workflow.required_validations),
        "failed_required_validations": failed_required,
        "unresolved_issues": unresolved,
        "artifacts": {
            "template_id": run_state.get("template_id"),
            "execution_strategy": run_state.get("execution_strategy"),
            "normalized_prompt": run_state.get("normalized_prompt"),
            "style_profile": run_state.get("style_profile"),
            "evidence_notes": run_state.get("evidence_notes", []),
            "agent_rules": run_state.get("agent_rules", []),
            "draft_text": run_state.get("draft_text"),
            "humanized_text": run_state.get("humanized_text"),
            "result_text": run_state.get("result_text"),
            "learned_workflow_skill": run_state.get("learned_workflow_skill"),
            "learned_workflow_evidence": run_state.get("learned_workflow_evidence", []),
            "agentized_task_packet": run_state.get("agentized_task_packet"),
            "tmcp_packet": run_state.get("tmcp_packet"),
            "tmcp_packet_expansions": run_state.get("tmcp_packet_expansions", []),
            "expertise_packet": run_state.get("expertise_packet"),
            "expert_rubric": run_state.get("expert_rubric"),
            "expert_audit_report": run_state.get("expert_audit_report"),
            "expert_remediation_plan": run_state.get("expert_remediation_plan"),
            "expert_implementation_handoff": run_state.get("expert_implementation_handoff"),
            "expert_review_artifact_paths": run_state.get("expert_review_artifact_paths", {}),
        },
        "rtk": {
            "interface": rtk_rules.get(
                "interface",
                'rtk_run(command: string, mode: "compressed" | "raw" | "adaptive")',
            ),
            "default_mode": rtk_rules.get("default_mode", "compressed"),
            "workflow_mode": workflow_rtk_mode,
            "preserve": rtk_rules.get("preserve", []),
            "fallbacks": rtk_rules.get("fallbacks", {}),
        },
        "created_at": _now_iso(),
        "started_at": started_at,
        "ended_at": _now_iso(),
    }
    return report


def summarize_execution_report(report: dict[str, Any]) -> str:
    workflow_key = str(report.get("workflow_key", "unknown"))
    status = str(report.get("status", "unknown"))
    stage_count = len(report.get("stages", []))
    validation_rows = report.get("validations", [])
    passed_count = sum(1 for row in validation_rows if row.get("passed", False))
    total_validations = len(validation_rows)
    return (
        f"Workflow {workflow_key} finished with status={status}; "
        f"stages={stage_count}; validations={passed_count}/{total_validations} passed."
    )
