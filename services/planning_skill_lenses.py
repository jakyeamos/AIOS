from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from services.workflow_orchestration import DEFAULT_SKILL_REGISTRY, SkillSpec, load_skill_registry

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_PLANNING_LENS_REGISTRY = ROOT / "config" / "planning" / "skill-planning-lenses.json"


@dataclass(frozen=True)
class SkillPlanningLens:
    skill_key: str
    planning_behavior: str
    constraints: tuple[str, ...]
    validation_gates: tuple[str, ...]
    reviewable_artifacts: tuple[str, ...]
    output_expectations: tuple[str, ...]
    source_skill_purpose: str
    source_invariants: tuple[str, ...]
    source_failure_conditions: tuple[str, ...]
    disallowed_outputs: tuple[str, ...]
    planning_mode_only: bool = True

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillPlanningLensSelection:
    lenses: tuple[SkillPlanningLens, ...]
    unknown_requests: tuple[str, ...]
    rationale: str

    def to_json(self) -> dict[str, Any]:
        return {
            "lenses": [lens.to_json() for lens in self.lenses],
            "unknown_requests": list(self.unknown_requests),
            "rationale": self.rationale,
        }


def load_skill_planning_lens_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or DEFAULT_SKILL_PLANNING_LENS_REGISTRY
    with registry_path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("Skill planning lens registry must be a JSON object.")
    lenses = loaded.get("skill_lenses")
    if not isinstance(lenses, dict) or not lenses:
        raise ValueError("Skill planning lens registry must define non-empty skill_lenses.")
    return loaded


def select_skill_planning_lenses(
    requests: tuple[str, ...],
    *,
    lens_registry_path: Path | None = None,
    skill_registry_path: Path | None = None,
) -> SkillPlanningLensSelection:
    lens_registry = load_skill_planning_lens_registry(lens_registry_path)
    skill_registry = load_skill_registry(skill_registry_path or DEFAULT_SKILL_REGISTRY)
    skill_keys = _resolve_skill_requests(requests, lens_registry, skill_registry)

    lenses: list[SkillPlanningLens] = []
    unknown: list[str] = []
    for request, skill_key in skill_keys:
        if skill_key is None:
            unknown.append(request)
            continue
        lenses.append(
            build_skill_planning_lens(
                skill_key,
                lens_registry=lens_registry,
                skill_registry=skill_registry,
            )
        )
    deduped = tuple({lens.skill_key: lens for lens in lenses}.values())
    return SkillPlanningLensSelection(
        lenses=deduped,
        unknown_requests=tuple(dict.fromkeys(unknown)),
        rationale=f"Selected {len(deduped)} skill planning lens(es) from {len(requests)} request(s).",
    )


def build_skill_planning_lens(
    skill_key: str,
    *,
    lens_registry: dict[str, Any] | None = None,
    skill_registry: dict[str, SkillSpec] | None = None,
) -> SkillPlanningLens:
    lens_registry = lens_registry or load_skill_planning_lens_registry()
    skill_registry = skill_registry or load_skill_registry()
    skill = skill_registry.get(skill_key)
    if skill is None:
        raise ValueError(f"Unknown skill: {skill_key}")
    lens_config = _skill_lens_config(lens_registry, skill_key)
    disallowed = _tuple(lens_registry.get("default_disallowed_outputs"))
    return SkillPlanningLens(
        skill_key=skill.key,
        planning_behavior=str(lens_config.get("planning_behavior") or _default_behavior(skill)),
        constraints=_tuple(lens_config.get("constraints")) + _source_constraints(skill),
        validation_gates=_tuple(lens_config.get("validation_gates")),
        reviewable_artifacts=_tuple(lens_config.get("reviewable_artifacts")),
        output_expectations=_tuple(lens_config.get("output_expectations")),
        source_skill_purpose=skill.purpose,
        source_invariants=skill.invariants,
        source_failure_conditions=skill.failure_conditions,
        disallowed_outputs=disallowed,
    )


def _resolve_skill_requests(
    requests: tuple[str, ...],
    lens_registry: dict[str, Any],
    skill_registry: dict[str, SkillSpec],
) -> tuple[tuple[str, str | None], ...]:
    aliases = lens_registry.get("request_aliases", {})
    if not isinstance(aliases, dict):
        aliases = {}
    rows: list[tuple[str, str | None]] = []
    for request in requests:
        normalized = _normalize(request)
        if normalized in skill_registry:
            rows.append((request, normalized))
            continue
        alias_match = _alias_match(normalized, aliases)
        if alias_match:
            rows.append((request, alias_match))
            continue
        rows.append((request, None))
    return tuple(rows)


def _skill_lens_config(registry: dict[str, Any], skill_key: str) -> dict[str, Any]:
    lenses = registry.get("skill_lenses", {})
    if not isinstance(lenses, dict):
        return {}
    row = lenses.get(skill_key, {})
    return row if isinstance(row, dict) else {}


def _alias_match(request: str, aliases: dict[str, Any]) -> str | None:
    for alias, skill_key in aliases.items():
        normalized_alias = _normalize(alias)
        if normalized_alias == request or normalized_alias in request:
            return str(skill_key)
    return None


def _source_constraints(skill: SkillSpec) -> tuple[str, ...]:
    constraints: list[str] = []
    for invariant in skill.invariants:
        constraints.append(f"Preserve skill invariant during planning: {invariant}")
    for failure in skill.failure_conditions:
        constraints.append(f"Plan mitigation for skill failure condition: {failure}")
    return tuple(constraints)


def _default_behavior(skill: SkillSpec) -> str:
    return (
        f"Use {skill.key} in planning mode by translating its purpose, invariants, "
        "failure conditions, side effects, and output schema into plan constraints."
    )


def _tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
