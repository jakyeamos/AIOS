from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GSD_PHASE_REGISTRY = ROOT / "config" / "planning" / "gsd-workflow-phases.json"


@dataclass(frozen=True)
class PlanningWorkflowDetection:
    source_invocation: str
    workflow: str
    phase: str
    handoff_target: str
    output_format: str
    matched_alias: str | None
    slash_overrides: tuple[str, ...]
    signals: tuple[str, ...]
    rationale: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def load_gsd_phase_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or DEFAULT_GSD_PHASE_REGISTRY
    with registry_path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("GSD phase registry must be a JSON object.")
    phases = loaded.get("phases")
    if not isinstance(phases, dict) or not phases:
        raise ValueError("GSD phase registry must define a non-empty phases object.")
    return loaded


def detect_planning_workflow(
    text: str,
    *,
    registry_path: Path | None = None,
    source_invocation: str | None = None,
) -> PlanningWorkflowDetection:
    registry = load_gsd_phase_registry(registry_path)
    objective = _normalize_text(text)
    slash_overrides = _slash_overrides(objective, registry)
    source = source_invocation or _source_invocation(objective)

    gsd_match = _match_gsd_phase(objective, registry)
    if gsd_match is not None:
        phase, alias, output_format = gsd_match
        return PlanningWorkflowDetection(
            source_invocation="slash_command" if _looks_like_slash(alias) else source,
            workflow=str(registry.get("workflow", {}).get("id", "gsd")),
            phase=phase,
            handoff_target=str(registry.get("workflow", {}).get("handoff_target", "gsd")),
            output_format=output_format,
            matched_alias=alias,
            slash_overrides=slash_overrides,
            signals=("configured_gsd_alias",),
            rationale=(
                f"Matched configured GSD phase alias {alias!r}; slash commands are treated as "
                "invocation hints and overrides while the structured workflow remains GSD."
            ),
        )

    audit_match = _audit_to_implementation(objective)
    if audit_match:
        return _generic_detection(
            source_invocation="audit_to_implementation_prompt",
            output_format="audit_to_implementation_plan",
            slash_overrides=slash_overrides,
            signals=("audit_to_implementation",),
            rationale="Detected audit/review findings being converted into implementation work.",
        )

    prompt_generation_match = _generated_implementation_prompt(objective)
    if prompt_generation_match:
        return _generic_detection(
            source_invocation="generated_implementation_prompt",
            output_format="implementation_prompt_plan",
            slash_overrides=slash_overrides,
            signals=("generated_implementation_prompt",),
            rationale="Detected a request to generate an implementation prompt or plan prompt.",
        )

    cli_match = _cli_shaped(objective) or source == "cli_routing"
    if cli_match:
        return _generic_detection(
            source_invocation="cli_routing",
            output_format="execution_symmetric_plan",
            slash_overrides=slash_overrides,
            signals=("cli_shaped_planning_context",),
            rationale="Detected CLI-shaped routing context for planning.",
        )

    planning_match = _natural_language_planning(objective)
    if planning_match:
        return _generic_detection(
            source_invocation=source,
            output_format="execution_symmetric_plan",
            slash_overrides=slash_overrides,
            signals=("natural_language_planning",),
            rationale="Detected natural-language planning intent.",
        )

    return PlanningWorkflowDetection(
        source_invocation=source,
        workflow="unknown",
        phase="unknown",
        handoff_target="none",
        output_format="unknown",
        matched_alias=None,
        slash_overrides=slash_overrides,
        signals=(),
        rationale="No planning workflow phase signal was detected.",
    )


def _generic_detection(
    *,
    source_invocation: str,
    output_format: str,
    slash_overrides: tuple[str, ...],
    signals: tuple[str, ...],
    rationale: str,
) -> PlanningWorkflowDetection:
    return PlanningWorkflowDetection(
        source_invocation=source_invocation,
        workflow="aios",
        phase="plan",
        handoff_target="aios",
        output_format=output_format,
        matched_alias=None,
        slash_overrides=slash_overrides,
        signals=signals,
        rationale=rationale,
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _alias_pattern(alias: str) -> re.Pattern[str]:
    normalized = re.escape(_normalize_text(alias))
    normalized = normalized.replace(r"\ ", r"[\s_-]+")
    return re.compile(rf"(?<![a-z0-9]){normalized}(?![a-z0-9])")


def _looks_like_slash(value: str) -> bool:
    return value.startswith("/")


def _match_gsd_phase(objective: str, registry: dict[str, Any]) -> tuple[str, str, str] | None:
    phases = registry.get("phases", {})
    if not isinstance(phases, dict):
        return None
    for phase, spec in phases.items():
        if not isinstance(spec, dict):
            continue
        aliases = spec.get("aliases", [])
        if not isinstance(aliases, list):
            continue
        for alias_value in aliases:
            alias = str(alias_value).strip().lower()
            if alias and _alias_pattern(alias).search(objective):
                return (
                    str(phase),
                    alias,
                    str(spec.get("output_format", f"gsd_ready_{phase}_plan")),
                )
    return None


def _slash_overrides(objective: str, registry: dict[str, Any]) -> tuple[str, ...]:
    overrides = registry.get("slash_overrides", {})
    if not isinstance(overrides, dict):
        return ()
    matched: list[str] = []
    for command, row in overrides.items():
        if _alias_pattern(str(command).lower()).search(objective):
            key = row.get("key") if isinstance(row, dict) else None
            matched.append(str(key or command).strip("/").replace("-", "_"))
    return tuple(dict.fromkeys(item for item in matched if item))


def _source_invocation(objective: str) -> str:
    if "/" in objective and re.search(r"(^|\s)/[a-z0-9_-]+", objective):
        return "slash_command"
    if _cli_shaped(objective):
        return "cli_routing"
    return "natural_language_planning"


def _natural_language_planning(objective: str) -> bool:
    planning_terms = {
        "plan",
        "planning",
        "roadmap",
        "implementation plan",
        "phase plan",
        "design the work",
    }
    return any(term in objective for term in planning_terms)


def _audit_to_implementation(objective: str) -> bool:
    audit_terms = {"audit", "review", "findings", "gap analysis"}
    implementation_terms = {"implement", "fix", "remediate", "address", "turn into"}
    return any(term in objective for term in audit_terms) and any(
        term in objective for term in implementation_terms
    )


def _generated_implementation_prompt(objective: str) -> bool:
    prompt_terms = {
        "implementation prompt",
        "execution prompt",
        "generate a prompt",
        "write a prompt",
    }
    implementation_terms = {"implement", "build", "code", "execute"}
    return any(term in objective for term in prompt_terms) and any(
        term in objective for term in implementation_terms
    )


def _cli_shaped(objective: str) -> bool:
    return bool(
        re.search(
            r"(^|\s)aios\s+(start-work|harness-brief|packet\s+generate|recommend-workflow)",
            objective,
        )
    )
