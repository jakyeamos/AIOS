from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from services.agent_rules import load_agent_rules
from services.execution_strategy import (
    StrategySelectionError,
    compile_execution_strategy,
    recommend_execution_surface,
)
from services.personalized_humanizer import (
    VoiceMode,
    build_voice_packet,
    classify_writing_task,
    score_quality,
    transform_text,
)
from services.rtk_integration import load_compression_rules

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW_REGISTRY = ROOT / "config" / "workflows" / "registry.json"
DEFAULT_SKILL_REGISTRY = ROOT / "config" / "workflows" / "skills.json"
DEFAULT_PROMPT_REGISTRY = ROOT / "prompts" / "registry.json"
WORKFLOW_TASK_FAMILIES = {
    "implementation-delivery": "audit_and_implement",
    "failure-recovery": "audit_and_implement",
}


@dataclass(frozen=True)
class StageSpec:
    key: str
    kind: str
    required_skills: tuple[str, ...]


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
            workflow_family=str(item.get("workflow_family", WORKFLOW_TASK_FAMILIES.get(key, key))),
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
            source_path=str(item["source_path"]) if item.get("source_path") else None,
            installed_name=str(item["installed_name"]) if item.get("installed_name") else None,
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


def rank_workflow_candidates(
    objective: str,
    *,
    workflow_registry_path: Path | None = None,
) -> list[WorkflowRouteCandidate]:
    workflows = load_workflow_registry(workflow_registry_path)
    objective_tokens = _tokenize(objective)
    implementation_tokens = {"implement", "build", "feature", "refactor", "fix", "ship", "tests"}
    recovery_tokens = {"debug", "broken", "failure", "regression", "crash"}
    analysis_tokens = {"review", "audit", "analyze", "architecture", "strategy"}
    candidates: list[WorkflowRouteCandidate] = []

    for workflow in workflows.values():
        matched_terms = sorted(
            {
                hint.lower()
                for hint in workflow.trigger_hints
                if hint.lower() in objective.lower() or _tokenize(hint) & objective_tokens
            }
        )
        score = len(matched_terms)
        if workflow.workflow_family == "audit_and_implement" and implementation_tokens & objective_tokens:
            score += 3
        if workflow.workflow_family == "failure_recovery" and recovery_tokens & objective_tokens:
            score += 3
        if workflow.workflow_family == "audit_only" and analysis_tokens & objective_tokens:
            score += 2
            if implementation_tokens & objective_tokens or recovery_tokens & objective_tokens:
                score -= 2
        if workflow.workflow_family == "content_generation" and {
            "paper",
            "essay",
            "citations",
            "academic",
        } & objective_tokens:
            score += 2
        if workflow.workflow_family == "writing_transformation" and {
            "humanize",
            "rewrite",
            "voice",
            "outreach",
            "prompt",
            "creative",
        } & objective_tokens:
            score += 3
        if score <= 0:
            continue
        candidates.append(
            WorkflowRouteCandidate(
                workflow_key=workflow.key,
                workflow_family=workflow.workflow_family,
                score=score,
                matched_terms=tuple(matched_terms),
                rationale=(
                    f"Matched trigger hints {matched_terms or ['<implicit>']} for workflow_family={workflow.workflow_family}."
                ),
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.workflow_key))
    return candidates


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
    objective_tokens = _tokenize(objective)
    ranked: list[tuple[int, dict[str, Any]]] = []

    for template in templates:
        prompt_family = str(template.get("prompt_family", "")).strip()
        if not prompt_family:
            continue
        score = 0
        applicable = template.get("applicable_workflow_families") or []
        if isinstance(applicable, list) and workflow.workflow_family in {str(row) for row in applicable}:
            score += 4
        classification = str(template.get("classification", "")).lower()
        if workflow.workflow_family == "failure_recovery" and classification == "debug":
            score += 2
        if workflow.workflow_family == "audit_only" and classification == "plan":
            score += 2
        tags = template.get("tags") or []
        if isinstance(tags, list):
            score += len(objective_tokens & {str(tag).lower() for tag in tags if isinstance(tag, str)})
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
            "route_status": str(template.get("route_status", "candidate")),
        }
        for _, template in ranked[1:3]
    ]
    return {
        "workflow_key": workflow_key,
        "workflow_family": workflow.workflow_family,
        "prompt_family": str(selected.get("prompt_family", "")),
        "template_id": str(selected.get("id", "")),
        "route_status": str(selected.get("route_status", "candidate")),
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
) -> dict[str, Any]:
    candidates = rank_workflow_candidates(objective, workflow_registry_path=workflow_registry_path)
    if not candidates:
        return {
            "objective": objective,
            "selected_workflow": None,
            "workflow_candidates": [],
            "prompt_recommendation": None,
            "backend_recommendation": None,
        }

    selected = candidates[0]
    task_family = WORKFLOW_TASK_FAMILIES.get(selected.workflow_key)
    prompt_recommendation = recommend_prompt_family(
        objective=objective,
        workflow_key=selected.workflow_key,
        prompt_registry_path=prompt_registry_path,
        workflow_registry_path=workflow_registry_path,
    )
    backend_recommendation = (
        recommend_execution_surface(task_family=task_family, preferred_surfaces=(surface, "claude_code"))
        if task_family
        else None
    )
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
        normalized += "\nAgent rules: " + "; ".join(str(rule.get("title")) for rule in agent_rules[:6])
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
        prompt_path = Path(context.prompt_registry_path) if context.prompt_registry_path else DEFAULT_PROMPT_REGISTRY
        output = _normalize_prompt(
            state,
            objective=context.objective,
            workflow_key=context.workflow_key,
            surface=context.surface,
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
        "agent_rules": [
            {"title": rule.title, "body": rule.body}
            for rule in load_agent_rules()
        ],
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
                    "source_path": spec.source_path,
                    "installed_name": spec.installed_name,
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
                "rtk_mode": workflow_rtk_mode if stage.kind in {"generate", "validate", "finalize"} else "compressed",
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
