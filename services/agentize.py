from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_REGISTRY = ROOT / "prompts" / "registry.json"


class TaskClassification(StrEnum):
    AUDIT = "audit"
    IMPLEMENT = "implement"
    DEBUG = "debug"
    REFACTOR = "refactor"
    TEST_GENERATION = "test_generation"
    RESEARCH = "research"
    PLANNING = "planning"
    PRD_GENERATION = "prd_generation"
    UI_UX_IMPROVEMENT = "ui_ux_improvement"
    WRITING = "writing"
    HUMANIZING = "humanizing"
    MIGRATION = "migration"
    ARCHITECTURE_CLEANUP = "architecture_cleanup"
    SECURITY_REVIEW = "security_review"
    OBSERVABILITY_IMPROVEMENT = "observability_improvement"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"
    REPO_MAINTENANCE = "repo_maintenance"
    DOCUMENTATION = "documentation"
    EVALUATION_DESIGN = "evaluation_design"


class ExecutionMode(StrEnum):
    SINGLE_AGENT_EXECUTION = "single_agent_execution"
    SUB_AGENT_DRIVEN_DEVELOPMENT = "sub_agent_driven_development"
    ORCHESTRATOR_EVALUATOR_LOOP = "orchestrator_evaluator_loop"
    TDD_FIRST_IMPLEMENTATION = "tdd_first_implementation"
    RESEARCH_FIRST_IMPLEMENTATION = "research_first_implementation"
    AUDIT_ONLY = "audit_only"
    PLAN_ONLY = "plan_only"
    IMPLEMENT_AFTER_AUDIT = "implement_after_audit"
    DESIGN_REVIEW_BEFORE_CODE = "design_review_before_code"
    SAFE_PATCH_MODE = "safe_patch_mode"
    HIGH_AUTONOMY_MODE = "high_autonomy_mode"
    APPROVAL_GATED_MODE = "approval_gated_mode"


class ContextPriority(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class ExecutionModeSelection:
    mode: ExecutionMode
    reasoning: str


@dataclass(frozen=True)
class ContextRequirement:
    path: str
    reason: str
    priority: ContextPriority = ContextPriority.REQUIRED


@dataclass(frozen=True)
class VerificationStep:
    kind: str
    reason: str
    command: str | None = None
    required: bool = True


@dataclass(frozen=True)
class PromptPatternEvidence:
    template_id: str
    prompt_family: str | None
    role: str
    reason: str


@dataclass(frozen=True)
class OutputContract:
    summary_required: bool
    files_changed_required: bool
    tests_required: bool
    risks_required: bool
    standards_delta_required: bool
    learning_capture_required: bool
    format: tuple[str, ...]


@dataclass(frozen=True)
class AgentizedTaskPacket:
    packet_id: str
    original_request: str
    normalized_objective: str
    task_classifications: tuple[TaskClassification, ...]
    execution_mode: ExecutionModeSelection
    required_context: tuple[ContextRequirement, ...]
    relevant_skills: tuple[str, ...]
    relevant_success_criteria: tuple[str, ...]
    relevant_standards: tuple[str, ...]
    constraints: tuple[str, ...]
    non_goals: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]
    sub_agent_recommendations: tuple[str, ...]
    model_reasoning_recommendation: str
    verification_plan: tuple[VerificationStep, ...]
    acceptance_criteria: tuple[str, ...]
    expected_deliverables: tuple[str, ...]
    output_contract: OutputContract
    project_truth_file_update_requirements: tuple[str, ...]
    experiment_metadata: dict[str, object]
    prompt_pattern_evidence: tuple[PromptPatternEvidence, ...]
    prompt_library_role: str = "supporting_pattern_corpus"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tokens(text: str) -> set[str]:
    return {token.strip(".,:;!?()[]{}\"'`").lower() for token in text.split() if token.strip()}


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _dedupe(items: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def _classify(request: str) -> tuple[TaskClassification, ...]:
    lowered = request.lower()
    classes: list[TaskClassification] = []

    checks: tuple[tuple[TaskClassification, tuple[str, ...]], ...] = (
        (TaskClassification.SECURITY_REVIEW, ("security", "auth", "token", "secret", "permission")),
        (
            TaskClassification.DEBUG,
            ("debug", "bug", "failing", "failure", "fix", "regression", "broken", "error"),
        ),
        (TaskClassification.AUDIT, ("audit", "review", "inspect", "assess")),
        (
            TaskClassification.TEST_GENERATION,
            ("write tests", "add tests", "test", "coverage", "tdd"),
        ),
        (
            TaskClassification.UI_UX_IMPROVEMENT,
            ("ui", "ux", "visual", "interface", "design", "screen", "polish"),
        ),
        (
            TaskClassification.REFACTOR,
            ("refactor", "clean up", "cleanup", "without breaking behavior"),
        ),
        (TaskClassification.RESEARCH, ("research", "compare", "investigate", "library")),
        (TaskClassification.PLANNING, ("plan", "roadmap", "strategy", "turn this idea")),
        (TaskClassification.PRD_GENERATION, ("prd", "product requirements")),
        (TaskClassification.MIGRATION, ("migrate", "migration")),
        (TaskClassification.ARCHITECTURE_CLEANUP, ("architecture", "boundary", "layering")),
        (
            TaskClassification.OBSERVABILITY_IMPROVEMENT,
            ("observability", "logging", "tracing", "dashboard"),
        ),
        (
            TaskClassification.PERFORMANCE_IMPROVEMENT,
            ("performance", "latency", "slow", "optimize"),
        ),
        (
            TaskClassification.REPO_MAINTENANCE,
            ("repo", "repository", "dependencies", "maintenance"),
        ),
        (TaskClassification.DOCUMENTATION, ("docs", "documentation", "readme")),
        (TaskClassification.EVALUATION_DESIGN, ("eval", "evaluation", "score", "quality")),
        (TaskClassification.HUMANIZING, ("humanize", "like my style", "sound like me")),
        (TaskClassification.WRITING, ("write", "rewrite", "draft", "copy")),
        (TaskClassification.IMPLEMENT, ("implement", "build", "add", "ship", "create")),
    )
    for classification, phrases in checks:
        if _contains_any(lowered, phrases):
            classes.append(classification)

    if not classes:
        classes.append(TaskClassification.PLANNING)
    if TaskClassification.SECURITY_REVIEW in classes and TaskClassification.AUDIT not in classes:
        classes.append(TaskClassification.AUDIT)
    return tuple(dict.fromkeys(classes))


def _select_execution_mode(
    request: str,
    classifications: tuple[TaskClassification, ...],
) -> ExecutionModeSelection:
    lowered = request.lower()
    risky = _contains_any(
        lowered,
        ("auth", "authentication", "security policy", "database schema", "secrets"),
    )
    complex_repo = _contains_any(
        lowered, ("whole repo", "entire repo", "architecture", "multi-file", "migration")
    )
    implementation = TaskClassification.IMPLEMENT in classifications
    audit = TaskClassification.AUDIT in classifications

    if _contains_any(lowered, ("tests first", "tdd", "write tests first")):
        return ExecutionModeSelection(
            ExecutionMode.TDD_FIRST_IMPLEMENTATION,
            "The request explicitly asks for tests-first or test-heavy execution.",
        )
    if TaskClassification.TEST_GENERATION in classifications:
        return ExecutionModeSelection(
            ExecutionMode.TDD_FIRST_IMPLEMENTATION,
            "The request is test-generation heavy, so tests should define the expected behavior first.",
        )
    if risky:
        return ExecutionModeSelection(
            ExecutionMode.APPROVAL_GATED_MODE,
            "Risk-sensitive architecture, security, or schema language requires explicit review gates.",
        )
    if complex_repo and implementation:
        return ExecutionModeSelection(
            ExecutionMode.SUB_AGENT_DRIVEN_DEVELOPMENT,
            "The request spans repo or architecture context plus implementation, so decomposition and review are useful.",
        )
    if audit and implementation:
        return ExecutionModeSelection(
            ExecutionMode.IMPLEMENT_AFTER_AUDIT,
            "The request combines evaluation with code changes; audit findings should drive the patch scope.",
        )
    if audit and not implementation:
        return ExecutionModeSelection(
            ExecutionMode.AUDIT_ONLY,
            "The request asks for evaluation without a required patch.",
        )
    if TaskClassification.RESEARCH in classifications and not implementation:
        return ExecutionModeSelection(
            ExecutionMode.RESEARCH_FIRST_IMPLEMENTATION,
            "Research is the primary uncertainty before any implementation decision.",
        )
    if (
        TaskClassification.PLANNING in classifications
        and not implementation
        and _contains_any(lowered, ("plan", "roadmap", "strategy", "turn this idea"))
    ):
        return ExecutionModeSelection(
            ExecutionMode.PLAN_ONLY,
            "The request asks to turn intent into a plan rather than change files immediately.",
        )
    return ExecutionModeSelection(
        ExecutionMode.SINGLE_AGENT_EXECUTION,
        "The request appears bounded enough for one agent with normal verification.",
    )


def _context_plan(
    request: str, classifications: tuple[TaskClassification, ...]
) -> tuple[ContextRequirement, ...]:
    context: list[ContextRequirement] = [
        ContextRequirement(
            "PROJECT.md", "Project truth anchors AIOS behavior and required writebacks."
        ),
        ContextRequirement(
            "AGENTS.md", "Repository agent workflow contract and local constraints."
        ),
    ]
    if _contains_any(request.lower(), ("workflow", "agent", "skill", "prompt", "orchestrat")):
        context.extend(
            [
                ContextRequirement(
                    "config/workflows/registry.json",
                    "Workflow stages and bindings are registry-backed.",
                ),
                ContextRequirement(
                    "config/workflows/skills.json",
                    "Skill metadata and stage permissions live here.",
                ),
                ContextRequirement(
                    "aios/context/domains/agent-harnesses.md",
                    "Agent harness standards apply to prompt and skill changes.",
                ),
            ]
        )
    if TaskClassification.UI_UX_IMPROVEMENT in classifications:
        context.append(
            ContextRequirement(
                "aios/context/standards/global.design.md", "UI work needs design standards."
            )
        )
    if TaskClassification.SECURITY_REVIEW in classifications:
        context.append(
            ContextRequirement(
                "aios/context/standards/global.security.md",
                "Security asks need global security standards.",
            )
        )
    if (
        TaskClassification.TEST_GENERATION in classifications
        or TaskClassification.IMPLEMENT in classifications
    ):
        context.append(
            ContextRequirement(
                "aios/context/standards/global.testing.md",
                "Implementation needs executable verification.",
            )
        )
    if TaskClassification.REFACTOR in classifications:
        context.append(
            ContextRequirement(
                "aios/context/packets/maintainability.architecture-boundaries.md",
                "Refactors must preserve ownership and architecture boundaries.",
            )
        )
    if _contains_any(
        request.lower(), ("success", "criteria", "verify", "test", "workflow", "aios")
    ):
        context.append(
            ContextRequirement(
                "spec/success-criteria/index.md",
                "Success criteria should be attached before execution.",
            )
        )
    if _contains_any(request.lower(), ("prompt", "agentize", "template")):
        context.append(
            ContextRequirement(
                "prompts/registry.json",
                "Prompt patterns can be used as evidence, not routing authority.",
            )
        )
    return tuple(context)


# DEPRECATED: kept as fallback for one cycle, retire in phase 8.
def _standards(classifications: tuple[TaskClassification, ...]) -> tuple[str, ...]:
    standards = ["maintainability", "testing", "observability"]
    if TaskClassification.SECURITY_REVIEW in classifications:
        standards.append("security")
    if TaskClassification.UI_UX_IMPROVEMENT in classifications:
        standards.extend(["ui_polish", "accessibility"])
    if TaskClassification.REFACTOR in classifications:
        standards.extend(["preserve_existing_behavior", "architecture_boundaries"])
    if TaskClassification.PERFORMANCE_IMPROVEMENT in classifications:
        standards.append("performance")
    if TaskClassification.DOCUMENTATION in classifications:
        standards.append("truth_file_consistency")
    return _dedupe(standards)


# DEPRECATED: kept as fallback for one cycle, retire in phase 8.
def _success_criteria(classifications: tuple[TaskClassification, ...]) -> tuple[str, ...]:
    criteria = ["workflow-state-integrity", "testing-trust", "truth-file-consistency"]
    if TaskClassification.SECURITY_REVIEW in classifications:
        criteria.append("security-review")
    if TaskClassification.REFACTOR in classifications:
        criteria.append("repo-boundary-discipline")
    if TaskClassification.IMPLEMENT in classifications:
        criteria.append("execution-first-verification")
    return _dedupe(criteria)


def _verification_plan(
    classifications: tuple[TaskClassification, ...],
    mode: ExecutionModeSelection,
) -> tuple[VerificationStep, ...]:
    steps: list[VerificationStep] = []
    if mode.mode == ExecutionMode.AUDIT_ONLY:
        steps.extend(
            [
                VerificationStep(
                    "evidence_review", "Audit findings must cite inspected files or artifacts."
                ),
                VerificationStep(
                    "recommendation_review",
                    "Recommendations must separate blockers, warnings, and follow-ups.",
                ),
            ]
        )
    if (
        TaskClassification.IMPLEMENT in classifications
        or TaskClassification.REFACTOR in classifications
    ):
        steps.extend(
            [
                VerificationStep(
                    "unit_tests", "Changed behavior needs focused tests.", "uv run pytest -q"
                ),
                VerificationStep(
                    "lint", "Python and UI changes should satisfy lint gates where applicable."
                ),
                VerificationStep("typecheck", "Typed surfaces should remain valid."),
                VerificationStep("build", "Build or package checks catch integration failures."),
            ]
        )
    if TaskClassification.UI_UX_IMPROVEMENT in classifications:
        steps.append(
            VerificationStep(
                "visual_review", "UI work needs visual inspection across relevant viewports."
            )
        )
    if (
        TaskClassification.SECURITY_REVIEW in classifications
        or mode.mode == ExecutionMode.APPROVAL_GATED_MODE
    ):
        steps.extend(
            [
                VerificationStep(
                    "approval_gate",
                    "Risk-sensitive changes need explicit approval before promotion.",
                ),
                VerificationStep(
                    "rollback_plan", "Risk-sensitive changes need a rollback or revert path."
                ),
            ]
        )
    if not steps:
        steps.append(
            VerificationStep(
                "acceptance_review", "Confirm deliverables match the normalized objective."
            )
        )
    steps.append(
        VerificationStep(
            "project_truth_update", "Meaningful AIOS state changes require truth-file updates."
        )
    )
    return tuple(steps)


def _prompt_evidence(
    request: str,
    classifications: tuple[TaskClassification, ...],
    prompt_registry_path: Path,
) -> tuple[PromptPatternEvidence, ...]:
    if not prompt_registry_path.exists():
        return (
            PromptPatternEvidence(
                "missing_registry",
                None,
                "fallback_signal",
                "Prompt registry was unavailable; agentize can still produce a packet without static mapping.",
            ),
        )
    registry = json.loads(prompt_registry_path.read_text(encoding="utf-8"))
    templates = registry.get("templates", [])
    if not isinstance(templates, list):
        templates = []
    request_tokens = _tokens(request)
    classification_values = {classification.value for classification in classifications}
    scored: list[tuple[int, str, str | None, str]] = []
    for template in templates:
        if not isinstance(template, dict):
            continue
        template_id = str(template.get("id", "")).strip()
        if not template_id:
            continue
        score = 0
        template_classification = str(template.get("classification", "")).strip()
        if template_classification in classification_values:
            score += 3
        tags = template.get("tags", [])
        if isinstance(tags, list):
            score += len(request_tokens & {str(tag).lower() for tag in tags})
        prompt_family = template.get("prompt_family")
        prompt_family_text = str(prompt_family) if prompt_family is not None else None
        if score > 0:
            scored.append(
                (
                    score,
                    template_id,
                    prompt_family_text,
                    "Template metadata overlaps the request and can inform packet wording.",
                )
            )
    scored.sort(key=lambda row: (-row[0], row[1]))
    if not scored:
        return (
            PromptPatternEvidence(
                "generic_agentization",
                None,
                "agentization_pattern",
                "No static template matched; packet was generated from task semantics.",
            ),
        )
    return tuple(
        PromptPatternEvidence(template_id, prompt_family, "supporting_evidence", reason)
        for _, template_id, prompt_family, reason in scored[:3]
    )


def agentize_request(
    request: str,
    *,
    prompt_registry_path: Path | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
    changed_files: tuple[str, ...] | None = None,
    workflow_key: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> AgentizedTaskPacket:
    normalized = " ".join(request.strip().split())
    if not normalized:
        raise ValueError("Cannot agentize an empty request.")
    classifications = _classify(normalized)
    execution_mode = _select_execution_mode(normalized, classifications)
    prompt_path = prompt_registry_path or DEFAULT_PROMPT_REGISTRY
    skills = ["agentize_intent_compiler"]
    if TaskClassification.HUMANIZING in classifications:
        skills.append("personalized_humanizer_transformer")
    if TaskClassification.RESEARCH in classifications:
        skills.append("smart_search")
    if TaskClassification.UI_UX_IMPROVEMENT in classifications:
        skills.append("react_components")

    implementation_like = {
        TaskClassification.IMPLEMENT,
        TaskClassification.REFACTOR,
        TaskClassification.DEBUG,
        TaskClassification.TEST_GENERATION,
    }
    truth_requirements = (
        "Update PROJECT.md when architecture, workflow contracts, or shipped behavior changes.",
        "Record prompt-pattern or skill learnings as reviewable candidates rather than silently promoting them.",
    )
    acceptance = [
        "Packet preserves the original user intent.",
        "Execution mode includes concrete reasoning.",
        "Context plan is targeted and avoids full-repo loading by default.",
        "Verification requirements are explicit before execution.",
    ]
    if implementation_like & set(classifications):
        acceptance.append("Changed behavior is covered by tests or an explicit test gap.")
    standards_resolution = _resolve_packet_standards(
        project_id=project_id,
        project_name=project_name,
        objective=normalized,
        classifications=classifications,
        changed_files=changed_files,
        skills=tuple(skills),
        workflow_key=workflow_key,
        conn=conn,
    )

    return AgentizedTaskPacket(
        packet_id=f"agentized-{uuid.uuid4()}",
        original_request=request,
        normalized_objective=normalized,
        task_classifications=classifications,
        execution_mode=execution_mode,
        required_context=_context_plan(normalized, classifications),
        relevant_skills=tuple(skills),
        relevant_success_criteria=standards_resolution[0],
        relevant_standards=standards_resolution[1],
        constraints=(
            "Preserve existing behavior unless the packet explicitly authorizes behavior change.",
            "Prefer incremental, reviewable changes over broad rewrites.",
            "Do not promote prompt or skill learnings without evidence.",
        ),
        non_goals=(
            "Do not replace the prompt library with static one-to-one routing.",
            "Do not load unrelated repository context by default.",
        ),
        risks=(
            "Ambiguous user intent may require clarification before destructive or broad changes.",
            "Prompt-pattern evidence can bias execution if treated as authority instead of examples.",
        ),
        assumptions=(
            "Best-effort execution is acceptable when ambiguity is low and verification can catch mistakes.",
            "AIOS truth files are authoritative for meaningful architecture state changes.",
        ),
        sub_agent_recommendations=(
            (
                "Use bounded implementation/review sub-agents for independent repo slices."
                if execution_mode.mode == ExecutionMode.SUB_AGENT_DRIVEN_DEVELOPMENT
                else "No sub-agent required by default."
            ),
        ),
        model_reasoning_recommendation=(
            "Use higher reasoning for cross-system architecture, security, or migration work; use standard reasoning for bounded single-file tasks."
        ),
        verification_plan=_verification_plan(classifications, execution_mode),
        acceptance_criteria=tuple(acceptance),
        expected_deliverables=(
            "Agentized execution packet",
            "Verification result summary",
            "Learning/writeback recommendations when reusable patterns appear",
        ),
        output_contract=OutputContract(
            summary_required=True,
            files_changed_required=True,
            tests_required=True,
            risks_required=True,
            standards_delta_required=True,
            learning_capture_required=True,
            format=(
                "Summary",
                "Files changed",
                "Tests run",
                "Risks and gaps",
                "Truth-file and learning writebacks",
            ),
        ),
        project_truth_file_update_requirements=truth_requirements,
        experiment_metadata={
            "agentize_version": "0.1.0",
            "created_at": _now_iso(),
            "requires_static_template_mapping": False,
            "prompt_library_role": "supporting_pattern_corpus",
        },
        prompt_pattern_evidence=_prompt_evidence(normalized, classifications, prompt_path),
    )


def _resolve_packet_standards(
    *,
    project_id: str | None,
    project_name: str | None,
    objective: str,
    classifications: tuple[TaskClassification, ...],
    changed_files: tuple[str, ...] | None,
    skills: tuple[str, ...],
    workflow_key: str | None,
    conn: sqlite3.Connection | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    from services.success_criteria import resolve_task_standards  # noqa: PLC0415

    result = resolve_task_standards(
        project_id=project_id,
        project_name=project_name,
        objective=objective,
        prompt_classifications=[classification.value for classification in classifications],
        changed_files=changed_files,
        skills=skills,
        workflow_key=workflow_key,
        conn=conn,
    )
    criteria = tuple(str(row["id"]) for row in result.get("criteria", []) if isinstance(row, dict))
    standards = tuple(
        str(row["standard_id"]) for row in result.get("standards", []) if isinstance(row, dict)
    )
    if result.get("resolution_status") == "no_profile_attached":
        return criteria or _success_criteria(classifications), standards
    return criteria or _success_criteria(classifications), standards or _standards(classifications)


def ensure_agentize_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agentize_evaluations (
          id TEXT PRIMARY KEY,
          packet_id TEXT NOT NULL,
          original_request TEXT NOT NULL,
          transformed_request_json TEXT NOT NULL,
          selected_execution_mode TEXT NOT NULL,
          selected_skills_json TEXT NOT NULL DEFAULT '[]',
          selected_standards_json TEXT NOT NULL DEFAULT '[]',
          outcome_quality INTEGER,
          tests_passed INTEGER,
          user_correction TEXT,
          follow_up_required INTEGER NOT NULL DEFAULT 0,
          major_repair_required INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agentize_evaluations_packet
          ON agentize_evaluations(packet_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agentize_evaluations_mode
          ON agentize_evaluations(selected_execution_mode, created_at DESC)
        """
    )


def record_agentize_evaluation(
    conn: sqlite3.Connection,
    *,
    packet: AgentizedTaskPacket,
    outcome_quality: int | None,
    tests_passed: bool | None,
    user_correction: str | None,
    follow_up_required: bool,
    major_repair_required: bool,
) -> dict[str, object]:
    ensure_agentize_schema(conn)
    record = {
        "id": f"agentize-eval-{uuid.uuid4()}",
        "packet_id": packet.packet_id,
        "original_request": packet.original_request,
        "transformed_request_json": packet.to_json(),
        "selected_execution_mode": packet.execution_mode.mode.value,
        "selected_skills_json": json.dumps(list(packet.relevant_skills), sort_keys=True),
        "selected_standards_json": json.dumps(list(packet.relevant_standards), sort_keys=True),
        "outcome_quality": outcome_quality,
        "tests_passed": None if tests_passed is None else int(tests_passed),
        "user_correction": user_correction,
        "follow_up_required": int(follow_up_required),
        "major_repair_required": int(major_repair_required),
        "created_at": _now_iso(),
    }
    conn.execute(
        """
        INSERT INTO agentize_evaluations (
          id, packet_id, original_request, transformed_request_json, selected_execution_mode,
          selected_skills_json, selected_standards_json, outcome_quality, tests_passed,
          user_correction, follow_up_required, major_repair_required, created_at
        ) VALUES (
          :id, :packet_id, :original_request, :transformed_request_json, :selected_execution_mode,
          :selected_skills_json, :selected_standards_json, :outcome_quality, :tests_passed,
          :user_correction, :follow_up_required, :major_repair_required, :created_at
        )
        """,
        record,
    )
    return record
