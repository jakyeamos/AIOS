from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_SPECS_PATH = ROOT / "config" / "execution-strategies" / "task-specs.json"
DEFAULT_STRATEGIES_PATH = ROOT / "config" / "execution-strategies" / "strategies.json"

VALID_SURFACES = {"claude_code", "codex"}
DEFAULT_STATUS_ORDER = [
    "validated",
    "canary",
    "shadow",
    "experimental",
    "draft",
    "watchlist",
    "deprecated",
    "rolled_back",
]

REQUIRED_TASK_SPEC_FIELDS = {
    "task_family",
    "task_intent_description",
    "required_inputs",
    "optional_inputs",
    "output_contract",
    "hard_constraints",
    "quality_rubric_profile",
    "default_context_requirements",
}

REQUIRED_STRATEGY_FIELDS = {
    "strategy_id",
    "strategy_version",
    "task_family",
    "surface",
    "status",
    "command_adapter_version",
    "skill_bundle_version",
    "context_profile_version",
    "validation_profile_version",
    "model_profile",
    "execution_mode",
    "token_budget_class",
    "expected_repo_scope",
    "safety_scope",
    "rollout_policy",
    "change_hypothesis",
    "created_at",
    "created_by",
}


class StrategySelectionError(ValueError):
    pass


@dataclass(frozen=True)
class TaskSpec:
    task_family: str
    task_intent_description: str
    required_inputs: list[dict[str, str]]
    optional_inputs: list[dict[str, str]]
    output_contract: list[str]
    hard_constraints: list[str]
    quality_rubric_profile: dict[str, int]
    default_context_requirements: list[str]


@dataclass(frozen=True)
class StrategyBundle:
    strategy_id: str
    strategy_version: str
    task_family: str
    surface: str
    status: str
    command_adapter_version: str
    skill_bundle_version: str
    context_profile_version: str
    validation_profile_version: str
    model_profile: dict[str, Any]
    execution_mode: str
    token_budget_class: str
    expected_repo_scope: str
    safety_scope: str
    rollout_policy: dict[str, Any]
    parent_strategy_id: str | None
    change_hypothesis: str
    created_at: str
    created_by: str


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise StrategySelectionError(f"Expected object JSON at {path}")
    return loaded


def load_task_specs(path: Path | None = None) -> dict[str, TaskSpec]:
    catalog = _load_json(path or DEFAULT_TASK_SPECS_PATH)
    rows = catalog.get("task_specs")
    if not isinstance(rows, list):
        raise StrategySelectionError("Task spec catalog must define a task_specs list.")

    specs: dict[str, TaskSpec] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        missing = REQUIRED_TASK_SPEC_FIELDS - set(row)
        if missing:
            raise StrategySelectionError(
                f"Task spec missing required fields: {', '.join(sorted(missing))}"
            )
        spec = TaskSpec(
            task_family=str(row["task_family"]),
            task_intent_description=str(row["task_intent_description"]),
            required_inputs=[
                {str(name): str(desc) for name, desc in entry.items()}
                for entry in row.get("required_inputs", [])
                if isinstance(entry, dict)
            ],
            optional_inputs=[
                {str(name): str(desc) for name, desc in entry.items()}
                for entry in row.get("optional_inputs", [])
                if isinstance(entry, dict)
            ],
            output_contract=[str(item) for item in row.get("output_contract", [])],
            hard_constraints=[str(item) for item in row.get("hard_constraints", [])],
            quality_rubric_profile={
                str(name): int(weight)
                for name, weight in row.get("quality_rubric_profile", {}).items()
            },
            default_context_requirements=[
                str(item) for item in row.get("default_context_requirements", [])
            ],
        )
        specs[spec.task_family] = spec
    return specs


def load_strategy_catalog(path: Path | None = None) -> dict[str, Any]:
    catalog = _load_json(path or DEFAULT_STRATEGIES_PATH)
    strategies = catalog.get("strategies")
    if not isinstance(strategies, list):
        raise StrategySelectionError("Strategy catalog must define a strategies list.")
    return catalog


def validate_strategy_catalog(
    task_specs: dict[str, TaskSpec],
    strategy_catalog: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    valid_statuses = strategy_catalog.get("valid_statuses")
    status_set = set(valid_statuses) if isinstance(valid_statuses, list) else set(DEFAULT_STATUS_ORDER)

    adapters = {
        str(row.get("version", "")): row
        for row in strategy_catalog.get("command_adapters", [])
        if isinstance(row, dict)
    }
    skill_bundles = {
        str(row.get("version", "")): row
        for row in strategy_catalog.get("skill_bundles", [])
        if isinstance(row, dict)
    }
    context_profiles = {
        str(row.get("version", "")): row
        for row in strategy_catalog.get("context_profiles", [])
        if isinstance(row, dict)
    }
    validation_profiles = {
        str(row.get("version", "")): row
        for row in strategy_catalog.get("validation_profiles", [])
        if isinstance(row, dict)
    }

    per_family_surface: dict[str, set[str]] = {}
    for row in strategy_catalog.get("strategies", []):
        if not isinstance(row, dict):
            errors.append("Strategy row must be an object.")
            continue

        missing = REQUIRED_STRATEGY_FIELDS - set(row)
        if missing:
            errors.append(
                "Strategy {id} missing fields: {fields}".format(
                    id=row.get("strategy_id", "<unknown>"),
                    fields=", ".join(sorted(missing)),
                )
            )
            continue

        strategy_id = str(row.get("strategy_id", ""))
        surface = str(row.get("surface", ""))
        status = str(row.get("status", ""))
        task_family = str(row.get("task_family", ""))

        if surface not in VALID_SURFACES:
            errors.append(f"Strategy {strategy_id} has unsupported surface: {surface}")
        if status not in status_set:
            errors.append(f"Strategy {strategy_id} has unsupported status: {status}")
        if task_family not in task_specs:
            errors.append(f"Strategy {strategy_id} references unknown task family: {task_family}")

        adapter_version = str(row.get("command_adapter_version", ""))
        adapter = adapters.get(adapter_version)
        if adapter is None:
            errors.append(f"Strategy {strategy_id} references unknown adapter version: {adapter_version}")
        else:
            adapter_surface = str(adapter.get("surface", ""))
            if adapter_surface != surface:
                errors.append(
                    f"Strategy {strategy_id} surface {surface} does not match adapter surface {adapter_surface}."
                )

        if str(row.get("skill_bundle_version", "")) not in skill_bundles:
            errors.append(
                f"Strategy {strategy_id} references unknown skill bundle: {row.get('skill_bundle_version')}"
            )
        if str(row.get("context_profile_version", "")) not in context_profiles:
            errors.append(
                f"Strategy {strategy_id} references unknown context profile: {row.get('context_profile_version')}"
            )
        if str(row.get("validation_profile_version", "")) not in validation_profiles:
            errors.append(
                f"Strategy {strategy_id} references unknown validation profile: {row.get('validation_profile_version')}"
            )

        if status not in {"deprecated", "rolled_back"}:
            per_family_surface.setdefault(task_family, set()).add(surface)

    for task_family in task_specs:
        surfaces = per_family_surface.get(task_family, set())
        if "claude_code" not in surfaces:
            errors.append(f"Task family {task_family} has no active claude_code strategy.")
        if "codex" not in surfaces:
            errors.append(f"Task family {task_family} has no active codex strategy.")

    return errors


def _status_rank(status: str, status_order: list[str]) -> int:
    try:
        return status_order.index(status)
    except ValueError:
        return len(status_order)


def _strategy_version_key(version: str) -> tuple[int, ...]:
    parts = []
    for token in version.split("."):
        if token.isdigit():
            parts.append(int(token))
    return tuple(parts) if parts else (0,)


def _select_strategy(
    strategy_catalog: dict[str, Any],
    *,
    task_family: str,
    surface: str,
) -> StrategyBundle:
    status_order = strategy_catalog.get("valid_statuses")
    if not isinstance(status_order, list):
        status_order = DEFAULT_STATUS_ORDER

    candidates: list[dict[str, Any]] = []
    for row in strategy_catalog.get("strategies", []):
        if not isinstance(row, dict):
            continue
        if str(row.get("task_family", "")) != task_family:
            continue
        if str(row.get("surface", "")) != surface:
            continue
        if str(row.get("status", "")) in {"deprecated", "rolled_back"}:
            continue
        candidates.append(row)

    if not candidates:
        raise StrategySelectionError(
            f"No strategy candidates found for task_family={task_family} surface={surface}"
        )

    candidates.sort(
        key=lambda row: (
            _status_rank(str(row.get("status", "")), status_order),
            tuple(-value for value in _strategy_version_key(str(row.get("strategy_version", "0")))),
        )
    )
    selected = candidates[0]

    return StrategyBundle(
        strategy_id=str(selected["strategy_id"]),
        strategy_version=str(selected["strategy_version"]),
        task_family=str(selected["task_family"]),
        surface=str(selected["surface"]),
        status=str(selected["status"]),
        command_adapter_version=str(selected["command_adapter_version"]),
        skill_bundle_version=str(selected["skill_bundle_version"]),
        context_profile_version=str(selected["context_profile_version"]),
        validation_profile_version=str(selected["validation_profile_version"]),
        model_profile=dict(selected.get("model_profile", {})),
        execution_mode=str(selected["execution_mode"]),
        token_budget_class=str(selected["token_budget_class"]),
        expected_repo_scope=str(selected["expected_repo_scope"]),
        safety_scope=str(selected["safety_scope"]),
        rollout_policy=dict(selected.get("rollout_policy", {})),
        parent_strategy_id=(
            str(selected["parent_strategy_id"])
            if selected.get("parent_strategy_id") is not None
            else None
        ),
        change_hypothesis=str(selected["change_hypothesis"]),
        created_at=str(selected["created_at"]),
        created_by=str(selected["created_by"]),
    )


def _flatten_inputs(rows: list[dict[str, str]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        names.extend(row.keys())
    return names


def compile_execution_strategy(
    *,
    objective: str,
    task_family: str,
    surface: str,
    task_specs_path: Path | None = None,
    strategies_path: Path | None = None,
) -> dict[str, Any]:
    specs = load_task_specs(task_specs_path)
    catalog = load_strategy_catalog(strategies_path)
    errors = validate_strategy_catalog(specs, catalog)
    if errors:
        raise StrategySelectionError("Strategy catalog validation failed: " + "; ".join(errors))

    task_spec = specs.get(task_family)
    if task_spec is None:
        raise StrategySelectionError(f"Unknown task family: {task_family}")

    strategy = _select_strategy(catalog, task_family=task_family, surface=surface)

    adapters = {
        str(row.get("version", "")): row
        for row in catalog.get("command_adapters", [])
        if isinstance(row, dict)
    }
    skill_bundles = {
        str(row.get("version", "")): row
        for row in catalog.get("skill_bundles", [])
        if isinstance(row, dict)
    }
    context_profiles = {
        str(row.get("version", "")): row
        for row in catalog.get("context_profiles", [])
        if isinstance(row, dict)
    }
    validation_profiles = {
        str(row.get("version", "")): row
        for row in catalog.get("validation_profiles", [])
        if isinstance(row, dict)
    }

    adapter = adapters[strategy.command_adapter_version]
    skill_bundle = skill_bundles[strategy.skill_bundle_version]
    context_profile = context_profiles[strategy.context_profile_version]
    validation_profile = validation_profiles[strategy.validation_profile_version]

    rubric_lines = [
        f"- {key}: {weight}"
        for key, weight in sorted(task_spec.quality_rubric_profile.items())
    ]
    instruction = "\n".join(
        [
            f"Task Family: {task_spec.task_family}",
            f"Intent: {task_spec.task_intent_description}",
            f"Surface: {surface}",
            f"User Objective: {objective}",
            "",
            "Required Inputs:",
            *[f"- {name}" for name in _flatten_inputs(task_spec.required_inputs)],
            "",
            "Output Contract:",
            *[f"- {item}" for item in task_spec.output_contract],
            "",
            "Hard Constraints:",
            *[f"- {item}" for item in task_spec.hard_constraints],
            "",
            "Quality Rubric Weights:",
            *rubric_lines,
            "",
            "Adapter Guidance:",
            f"- {str(adapter.get('template', '')).strip()}",
        ]
    ).strip()

    return {
        "task_family": task_spec.task_family,
        "surface": surface,
        "strategy_id": strategy.strategy_id,
        "strategy_version": strategy.strategy_version,
        "strategy_status": strategy.status,
        "execution_mode": strategy.execution_mode,
        "command_adapter_version": strategy.command_adapter_version,
        "skill_bundle_version": strategy.skill_bundle_version,
        "context_profile_version": strategy.context_profile_version,
        "validation_profile_version": strategy.validation_profile_version,
        "model_profile": strategy.model_profile,
        "rollout_policy": strategy.rollout_policy,
        "hard_constraints": task_spec.hard_constraints,
        "output_contract": task_spec.output_contract,
        "validation_profile": validation_profile,
        "context_profile": context_profile,
        "skill_bundle": skill_bundle,
        "compiled_instruction": instruction,
    }


def build_strategy_registry_snapshot(
    task_specs: dict[str, TaskSpec],
    strategy_catalog: dict[str, Any],
) -> dict[str, Any]:
    errors = validate_strategy_catalog(task_specs, strategy_catalog)
    if errors:
        raise StrategySelectionError("Strategy catalog validation failed: " + "; ".join(errors))

    rows: list[dict[str, Any]] = []
    for family in sorted(task_specs):
        for surface in sorted(VALID_SURFACES):
            selected = _select_strategy(strategy_catalog, task_family=family, surface=surface)
            rows.append(
                {
                    "task_family": family,
                    "surface": surface,
                    "strategy_id": selected.strategy_id,
                    "strategy_version": selected.strategy_version,
                    "status": selected.status,
                    "execution_mode": selected.execution_mode,
                }
            )

    return {
        "task_family_count": len(task_specs),
        "strategy_selection": rows,
    }
