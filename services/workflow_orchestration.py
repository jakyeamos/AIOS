from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_REGISTRY = ROOT / "config" / "workflows" / "registry.json"
DEFAULT_SKILL_REGISTRY = ROOT / "config" / "workflows" / "skills.json"
DEFAULT_PROMPT_REGISTRY = ROOT / "prompts" / "registry.json"


@dataclass(frozen=True)
class StageSpec:
    key: str
    kind: str
    required_skills: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowSpec:
    key: str
    name: str
    purpose: str
    trigger_hints: tuple[str, ...]
    output_contract: tuple[str, ...]
    required_validations: tuple[str, ...]
    stages: tuple[StageSpec, ...]


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


@dataclass(frozen=True)
class WorkflowExecutionContext:
    objective: str
    workflow_key: str
    repo_path: str | None = None
    vault_root: str | None = None
    prompt_registry_path: str | None = None
    run_id: str | None = None
    invocation_id: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return loaded


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
            required_skills = row.get("required_skills") or []
            if not isinstance(required_skills, list):
                raise ValueError(f"Workflow {key} stage required_skills must be a list.")
            stages.append(
                StageSpec(
                    key=str(row.get("key", "")).strip(),
                    kind=str(row.get("kind", "")).strip(),
                    required_skills=tuple(str(skill).strip() for skill in required_skills if str(skill).strip()),
                )
            )
        registry[key] = WorkflowSpec(
            key=key,
            name=str(item.get("name", key)),
            purpose=str(item.get("purpose", "")),
            trigger_hints=tuple(str(hint) for hint in item.get("trigger_hints", []) if isinstance(hint, str)),
            output_contract=tuple(str(row) for row in item.get("output_contract", []) if isinstance(row, str)),
            required_validations=tuple(
                str(row) for row in item.get("required_validations", []) if isinstance(row, str)
            ),
            stages=tuple(stages),
        )
    return registry


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
            allowed_stages=tuple(str(stage) for stage in item.get("allowed_stages", []) if isinstance(stage, str)),
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
            invariants=tuple(str(row) for row in item.get("invariants", []) if isinstance(row, str)),
            failure_conditions=tuple(
                str(row) for row in item.get("failure_conditions", []) if isinstance(row, str)
            ),
            side_effects=tuple(str(row) for row in item.get("side_effects", []) if isinstance(row, str)),
            execution_mode=str(item.get("execution_mode", "deterministic")),
        )
    return registry


def validate_workflow_bindings(
    workflows: dict[str, WorkflowSpec],
    skills: dict[str, SkillSpec],
) -> list[str]:
    errors: list[str] = []
    for workflow in workflows.values():
        seen_stage_keys: set[str] = set()
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
                    errors.append(f"Workflow {workflow.key} stage {stage.key} references unknown skill {skill_key}.")
                    continue
                if stage.kind not in spec.allowed_stages:
                    errors.append(
                        f"Workflow {workflow.key} stage {stage.key} kind {stage.kind} is not allowed for skill {skill_key}."
                    )

        if workflow.required_validations:
            validate_stage = next((stage for stage in workflow.stages if stage.kind == "validate"), None)
            if validate_stage is None:
                errors.append(f"Workflow {workflow.key} declares required validations without a validate stage.")
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
    return errors


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9]{4,}", text.lower()))


def _load_prompt_templates(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    loaded = _load_json(path)
    templates = loaded.get("templates")
    if not isinstance(templates, list):
        return []
    return [item for item in templates if isinstance(item, dict)]


def _select_prompt_template(objective: str, workflow_key: str, templates: list[dict[str, Any]]) -> str | None:
    objective_tokens = _tokenize(objective)
    best_id: str | None = None
    best_score = -1

    for template in templates:
        template_id = str(template.get("id", "")).strip()
        if not template_id:
            continue
        score = 0
        classification = str(template.get("classification", "")).lower()
        if workflow_key == "academic_paper_v1" and classification in {"research", "content_writing"}:
            score += 3
        tags = template.get("tags") or []
        if isinstance(tags, list):
            score += len(objective_tokens & {str(tag).lower() for tag in tags if isinstance(tag, str)})
        if score > best_score:
            best_score = score
            best_id = template_id
    return best_id


def _normalize_prompt(
    state: dict[str, Any],
    *,
    objective: str,
    workflow_key: str,
    prompt_registry_path: Path,
) -> dict[str, Any]:
    templates = _load_prompt_templates(prompt_registry_path)
    template_id = _select_prompt_template(objective, workflow_key, templates)
    normalized = (
        f"Objective: {objective.strip()}\n"
        f"Workflow: {workflow_key}\n"
        "Deliverable: Provide structured output that preserves factual meaning and explicit evidence references."
    )
    if template_id:
        normalized += f"\nTemplate: {template_id}"
    state["template_id"] = template_id
    state["normalized_prompt"] = normalized
    return {"template_id": template_id, "normalized_prompt": normalized}


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
    draft_tokens = _tokenize(draft_text)
    final_tokens = _tokenize(humanized_text)
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
    objective_tokens = _tokenize(objective)
    output_tokens = _tokenize(output_text)
    overlap = objective_tokens & output_tokens
    passed = len(overlap) > 0
    issues = [] if passed else ["Output does not reference objective terms and appears out-of-scope."]
    return {
        "passed": passed,
        "issues": issues,
        "overlap_tokens": sorted(overlap),
    }


def _execute_skill(
    skill: SkillSpec,
    stage: StageSpec,
    *,
    state: dict[str, Any],
    context: WorkflowExecutionContext,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if skill.key == "prompt_library_normalizer":
        prompt_path = Path(context.prompt_registry_path) if context.prompt_registry_path else DEFAULT_PROMPT_REGISTRY
        output = _normalize_prompt(
            state,
            objective=context.objective,
            workflow_key=context.workflow_key,
            prompt_registry_path=prompt_path,
        )
        return output, None

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

    if skill.key == "structure_checker":
        result = _validate_structure(str(state.get("humanized_text") or state.get("draft_text") or ""))
        return {}, {"validation_key": skill.key, **result}

    if skill.key == "citation_checker":
        result = _validate_citations(str(state.get("humanized_text") or state.get("draft_text") or ""))
        return {}, {"validation_key": skill.key, **result}

    if skill.key == "meaning_preservation_checker":
        result = _validate_meaning_preservation(
            str(state.get("draft_text", "")),
            str(state.get("humanized_text") or state.get("draft_text") or ""),
        )
        return {}, {"validation_key": skill.key, **result}

    if skill.key == "scope_check":
        result = _validate_scope(
            context.objective,
            str(state.get("humanized_text") or state.get("draft_text") or state.get("normalized_prompt") or ""),
        )
        return {}, {"validation_key": skill.key, **result}

    return {}, None


def execute_workflow(
    context: WorkflowExecutionContext,
    *,
    workflow_registry_path: Path | None = None,
    skill_registry_path: Path | None = None,
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

    run_state: dict[str, Any] = {
        "objective": context.objective,
        "workflow_key": workflow.key,
    }
    stages_report: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    unresolved: list[str] = []

    for stage in workflow.stages:
        stage_started = _now_iso()
        skill_reports: list[dict[str, Any]] = []
        stage_issues: list[str] = []

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
                }
            )
            if validation is not None:
                validations.append(validation)
                if not validation.get("passed", False):
                    stage_issues.extend(validation.get("issues", []))

        stage_status = "completed" if not stage_issues else "failed"
        if stage_issues:
            unresolved.extend(stage_issues)

        stages_report.append(
            {
                "stage_key": stage.key,
                "kind": stage.kind,
                "status": stage_status,
                "skills": skill_reports,
                "issues": stage_issues,
                "started_at": stage_started,
                "ended_at": _now_iso(),
            }
        )

    required_validation_map = {
        row["validation_key"]: row
        for row in validations
        if isinstance(row, dict) and row.get("validation_key")
    }
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
        "required_validations": list(workflow.required_validations),
        "failed_required_validations": failed_required,
        "unresolved_issues": unresolved,
        "artifacts": {
            "template_id": run_state.get("template_id"),
            "normalized_prompt": run_state.get("normalized_prompt"),
            "style_profile": run_state.get("style_profile"),
            "evidence_notes": run_state.get("evidence_notes", []),
            "draft_text": run_state.get("draft_text"),
            "humanized_text": run_state.get("humanized_text"),
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
