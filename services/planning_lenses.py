from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLANNING_LENS_REGISTRY = ROOT / "config" / "planning" / "planning-lenses.json"


@dataclass(frozen=True)
class PlanningLens:
    key: str
    purpose: str
    standard_refs: tuple[str, ...]
    required: bool = False
    sources: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanningLensSelection:
    lenses: tuple[PlanningLens, ...]
    unknown_requested_lenses: tuple[str, ...]
    rationale: str

    def to_json(self) -> dict[str, Any]:
        return {
            "lenses": [lens.to_json() for lens in self.lenses],
            "unknown_requested_lenses": list(self.unknown_requested_lenses),
            "rationale": self.rationale,
        }


def load_planning_lens_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or DEFAULT_PLANNING_LENS_REGISTRY
    with registry_path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("Planning lens registry must be a JSON object.")
    lenses = loaded.get("lenses")
    if not isinstance(lenses, dict) or not lenses:
        raise ValueError("Planning lens registry must define a non-empty lenses object.")
    return loaded


def select_planning_lenses(
    *,
    task_types: tuple[str, ...] = (),
    workflow: str | None = None,
    phase: str | None = None,
    risk_level: str | None = None,
    requested_lenses: tuple[str, ...] = (),
    registry_path: Path | None = None,
) -> PlanningLensSelection:
    registry = load_planning_lens_registry(registry_path)
    selected: dict[str, set[str]] = {}

    for task_type in task_types:
        for lens in _mapping_lenses(registry, "task_type_mappings", task_type):
            selected.setdefault(lens, set()).add(f"task_type:{task_type}")

    workflow_phase_key = _workflow_phase_key(workflow, phase)
    if workflow_phase_key:
        for mapped in _mapping_lenses(registry, "workflow_phase_mappings", workflow_phase_key):
            for lens in _expand_task_type_or_lens(registry, mapped):
                selected.setdefault(lens, set()).add(f"workflow_phase:{workflow_phase_key}")

    normalized_risk = _normalize_key(risk_level)
    if normalized_risk:
        for lens in _mapping_lenses(registry, "risk_level_mappings", normalized_risk):
            selected.setdefault(lens, set()).add(f"risk_level:{normalized_risk}")

    unknown_requested: list[str] = []
    for requested in requested_lenses:
        lens = _normalize_key(requested)
        if lens in _lens_specs(registry):
            selected.setdefault(lens, set()).add("requested")
        else:
            unknown_requested.append(lens)

    required = _required_safety_lenses(registry, normalized_risk)
    for lens in required:
        selected.setdefault(lens, set()).add(f"required_safety:{normalized_risk}")

    lens_rows = tuple(
        _lens_from_registry(registry, key, required=key in required, sources=tuple(sorted(sources)))
        for key, sources in sorted(selected.items())
    )
    return PlanningLensSelection(
        lenses=lens_rows,
        unknown_requested_lenses=tuple(dict.fromkeys(unknown_requested)),
        rationale=_rationale(
            task_types=task_types,
            workflow_phase_key=workflow_phase_key,
            risk_level=normalized_risk,
            requested_lenses=requested_lenses,
            required_count=len(required),
            selected_count=len(lens_rows),
        ),
    )


def _lens_specs(registry: dict[str, Any]) -> dict[str, Any]:
    lenses = registry.get("lenses", {})
    return lenses if isinstance(lenses, dict) else {}


def _mapping_lenses(registry: dict[str, Any], mapping_key: str, key: str | None) -> tuple[str, ...]:
    normalized = _normalize_key(key)
    if not normalized:
        return ()
    mappings = registry.get(mapping_key, {})
    if not isinstance(mappings, dict):
        return ()
    raw = mappings.get(normalized)
    if raw is None:
        raw = mappings.get(normalized.replace("-", "_"))
    if raw is None:
        raw = mappings.get(normalized.replace("_", "-"), ())
    if not isinstance(raw, list):
        return ()
    return tuple(_normalize_key(item) for item in raw if _normalize_key(item))


def _expand_task_type_or_lens(registry: dict[str, Any], key: str) -> tuple[str, ...]:
    if key in _lens_specs(registry):
        return (key,)
    expanded = _mapping_lenses(registry, "task_type_mappings", key)
    return expanded or (key,)


def _required_safety_lenses(registry: dict[str, Any], risk_level: str | None) -> frozenset[str]:
    required = registry.get("required_safety_lenses", {})
    if not isinstance(required, dict) or not risk_level:
        return frozenset()
    raw = required.get(risk_level)
    if raw is None:
        raw = required.get(risk_level.replace("-", "_"), ())
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(_normalize_key(item) for item in raw if _normalize_key(item))


def _lens_from_registry(
    registry: dict[str, Any], key: str, *, required: bool, sources: tuple[str, ...]
) -> PlanningLens:
    spec = _lens_specs(registry).get(key, {})
    if not isinstance(spec, dict):
        spec = {}
    refs = spec.get("standard_refs", ())
    standard_refs = tuple(str(item) for item in refs) if isinstance(refs, list) else ()
    return PlanningLens(
        key=key,
        purpose=str(spec.get("purpose", "")),
        standard_refs=standard_refs,
        required=required,
        sources=sources,
    )


def _workflow_phase_key(workflow: str | None, phase: str | None) -> str | None:
    normalized_workflow = _normalize_key(workflow)
    normalized_phase = _normalize_key(phase)
    if not normalized_workflow or not normalized_phase:
        return None
    return f"{normalized_workflow}:{normalized_phase}"


def _normalize_key(value: object) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def _rationale(
    *,
    task_types: tuple[str, ...],
    workflow_phase_key: str | None,
    risk_level: str | None,
    requested_lenses: tuple[str, ...],
    required_count: int,
    selected_count: int,
) -> str:
    sources = []
    if task_types:
        sources.append(f"task_types={','.join(task_types)}")
    if workflow_phase_key:
        sources.append(f"workflow_phase={workflow_phase_key}")
    if risk_level:
        sources.append(f"risk_level={risk_level}")
    if requested_lenses:
        sources.append(f"requested={','.join(requested_lenses)}")
    if required_count:
        sources.append(f"required_safety_lenses={required_count}")
    return f"Selected {selected_count} planning lens(es) from {', '.join(sources) or 'no signals'}."
