from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_SPECS_PATH = ROOT / "config" / "execution-strategies" / "task-specs.json"
DEFAULT_STRATEGIES_PATH = ROOT / "config" / "execution-strategies" / "strategies.json"
DEFAULT_MODEL_ROUTING_POLICY_PATH = (
    ROOT / "config" / "execution-strategies" / "model-routing-policy.json"
)
DEFAULT_DX_ROUTING_POLICY_PATH = ROOT / "config" / "developer-experience" / "routing-policy.json"

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

REQUIRED_MODEL_ROUTING_FIELDS = {
    "version",
    "policy_id",
    "status",
    "governing_rule",
    "valid_statuses",
    "model_tiers",
    "reasoning_levels",
    "direct_execution_policy",
    "subagent_preference_policy",
    "agent_roles",
    "routing_categories",
    "telemetry_schema",
    "marginal_value_definition",
    "benchmark_plan",
    "learning_policy",
}

REQUIRED_AGENT_ROLES = {"orchestrator", "explorer", "implementer", "reviewer", "specialist"}
REQUIRED_BENCHMARK_CLASSES = {
    "simple_docs_edit",
    "small_bug_fix",
    "mechanical_refactor",
    "test_creation",
    "repo_mapping",
    "architecture_audit",
    "security_sensitive_review",
    "multi_file_feature_implementation",
    "ui_polish_task",
    "prompt_rule_improvement_task",
}
REQUIRED_TELEMETRY_FIELDS = {
    "task_id",
    "task_category",
    "subagent_type",
    "model_used",
    "reasoning_level_used",
    "input_tokens",
    "output_tokens",
    "tool_calls",
    "wall_clock_ms",
    "retry_count",
    "tests_passed",
    "lint_typecheck_passed",
    "reviewer_defects_found",
    "human_intervention_required",
    "result_status",
    "estimated_task_complexity",
    "final_quality_score",
    "cost_estimate",
    "model_choice_notes",
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


@dataclass(frozen=True)
class StrategyCandidate:
    strategy_id: str
    task_family: str
    surface: str
    status: str
    strategy_version: str
    rank: int


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise StrategySelectionError(f"Expected object JSON at {path}")
    return loaded


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


def load_model_routing_policy(path: Path | None = None) -> dict[str, Any]:
    policy = _load_json(path or DEFAULT_MODEL_ROUTING_POLICY_PATH)
    return policy


def load_developer_experience_routing_policy(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or DEFAULT_DX_ROUTING_POLICY_PATH)


def validate_model_routing_policy(policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_MODEL_ROUTING_FIELDS - set(policy)
    if missing:
        errors.append(f"Model routing policy missing fields: {', '.join(sorted(missing))}")
        return errors

    valid_statuses = policy.get("valid_statuses", [])
    if not isinstance(valid_statuses, list):
        errors.append("Model routing policy valid_statuses must be a list.")
        status_set: set[str] = set()
    else:
        status_set = {str(status) for status in valid_statuses}
    required_statuses = {"experimental", "candidate", "approved", "deprecated"}
    missing_statuses = required_statuses - status_set
    if missing_statuses:
        errors.append(
            "Model routing policy valid_statuses missing: "
            + ", ".join(sorted(missing_statuses))
        )

    if str(policy.get("status", "")) not in status_set:
        errors.append(f"Model routing policy has unsupported status: {policy.get('status')}")

    model_tiers = {
        str(row.get("tier"))
        for row in policy.get("model_tiers", [])
        if isinstance(row, dict) and row.get("tier")
    }
    if not {"cheap", "mid", "strong"} <= model_tiers:
        errors.append("Model routing policy must define cheap, mid, and strong model tiers.")

    reasoning_levels = {
        str(item) for item in policy.get("reasoning_levels", []) if isinstance(item, str)
    }
    if not {"low", "medium", "high"} <= reasoning_levels:
        errors.append("Model routing policy must define low, medium, and high reasoning levels.")

    agent_roles = {
        str(row.get("role"))
        for row in policy.get("agent_roles", [])
        if isinstance(row, dict) and row.get("role")
    }
    missing_roles = REQUIRED_AGENT_ROLES - agent_roles
    if missing_roles:
        errors.append("Model routing policy missing agent roles: " + ", ".join(sorted(missing_roles)))

    categories = policy.get("routing_categories", [])
    if not isinstance(categories, list) or not categories:
        errors.append("Model routing policy routing_categories must be a non-empty list.")
    else:
        for row in categories:
            if not isinstance(row, dict):
                errors.append("Model routing category rows must be objects.")
                continue
            category = str(row.get("category", "<unknown>"))
            for field in (
                "default_model_tier",
                "default_reasoning",
                "preferred_agent_role",
                "execution_bias",
                "risk_level",
                "status",
            ):
                if field not in row:
                    errors.append(f"Routing category {category} missing {field}.")
            if str(row.get("default_model_tier", "")) not in model_tiers:
                errors.append(f"Routing category {category} references unknown model tier.")
            if str(row.get("default_reasoning", "")) not in reasoning_levels:
                errors.append(f"Routing category {category} references unknown reasoning level.")
            if str(row.get("preferred_agent_role", "")) not in agent_roles:
                errors.append(f"Routing category {category} references unknown agent role.")
            if str(row.get("status", "")) not in status_set:
                errors.append(f"Routing category {category} has unsupported status.")

    direct_policy = policy.get("direct_execution_policy", {})
    if not isinstance(direct_policy, dict) or not direct_policy.get("allowed_when"):
        errors.append("Model routing policy must define direct execution exceptions.")

    subagent_policy = policy.get("subagent_preference_policy", {})
    if not isinstance(subagent_policy, dict) or not subagent_policy.get("prefer_when"):
        errors.append("Model routing policy must define subagent preference signals.")
    elif str(subagent_policy.get("default_execution_mode", "")) != "orchestrated_subagents":
        errors.append("Model routing policy default execution mode must be orchestrated_subagents.")

    telemetry = policy.get("telemetry_schema", {})
    telemetry_fields = set(_as_string_list(telemetry.get("run_fields") if isinstance(telemetry, dict) else []))
    missing_telemetry = REQUIRED_TELEMETRY_FIELDS - telemetry_fields
    if missing_telemetry:
        errors.append(
            "Model routing telemetry schema missing fields: "
            + ", ".join(sorted(missing_telemetry))
        )

    marginal_value = policy.get("marginal_value_definition", {})
    if not isinstance(marginal_value, dict) or "additional_cost" not in str(
        marginal_value.get("formula", "")
    ):
        errors.append("Model routing policy must define marginal value against added cost.")

    benchmark = policy.get("benchmark_plan", {})
    task_classes = set(
        _as_string_list(benchmark.get("task_classes") if isinstance(benchmark, dict) else [])
    )
    missing_benchmarks = REQUIRED_BENCHMARK_CLASSES - task_classes
    if missing_benchmarks:
        errors.append(
            "Model routing benchmark plan missing task classes: "
            + ", ".join(sorted(missing_benchmarks))
        )
    matrix = benchmark.get("model_reasoning_matrix", []) if isinstance(benchmark, dict) else []
    if not isinstance(matrix, list) or len(matrix) < 5:
        errors.append("Model routing benchmark plan must define the expected comparison matrix.")

    learning_policy = policy.get("learning_policy", {})
    if not isinstance(learning_policy, dict):
        errors.append("Model routing learning_policy must be an object.")
    elif _as_int(learning_policy.get("minimum_evidence_runs_before_default_change")) < 2:
        errors.append("Model routing default changes require repeated evidence.")

    return errors


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


def list_strategy_candidates(
    *,
    task_family: str,
    task_specs_path: Path | None = None,
    strategies_path: Path | None = None,
) -> list[StrategyCandidate]:
    specs = load_task_specs(task_specs_path)
    catalog = load_strategy_catalog(strategies_path)
    errors = validate_strategy_catalog(specs, catalog)
    if errors:
        raise StrategySelectionError("Strategy catalog validation failed: " + "; ".join(errors))
    if task_family not in specs:
        raise StrategySelectionError(f"Unknown task family: {task_family}")

    status_order = catalog.get("valid_statuses")
    if not isinstance(status_order, list):
        status_order = DEFAULT_STATUS_ORDER

    candidates: list[StrategyCandidate] = []
    rows = catalog.get("strategies", [])
    if not isinstance(rows, list):
        return candidates

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("task_family", "")) != task_family:
            continue
        status = str(row.get("status", ""))
        if status in {"deprecated", "rolled_back"}:
            continue
        surface = str(row.get("surface", ""))
        candidates.append(
            StrategyCandidate(
                strategy_id=str(row.get("strategy_id", "")),
                task_family=task_family,
                surface=surface,
                status=status,
                strategy_version=str(row.get("strategy_version", "0")),
                rank=_status_rank(status, status_order),
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.rank,
            tuple(-value for value in _strategy_version_key(candidate.strategy_version)),
            candidate.surface,
        )
    )
    return candidates


def recommend_execution_surface(
    *,
    task_family: str,
    preferred_surfaces: tuple[str, ...] = ("codex", "claude_code"),
    task_specs_path: Path | None = None,
    strategies_path: Path | None = None,
) -> dict[str, Any]:
    candidates = list_strategy_candidates(
        task_family=task_family,
        task_specs_path=task_specs_path,
        strategies_path=strategies_path,
    )
    if not candidates:
        raise StrategySelectionError(f"No strategy candidates found for task_family={task_family}")

    ordered: list[StrategyCandidate] = []
    for surface in preferred_surfaces:
        ordered.extend(candidate for candidate in candidates if candidate.surface == surface)
    ordered.extend(candidate for candidate in candidates if candidate not in ordered)

    selected = ordered[0]
    alternatives = [candidate for candidate in ordered[1:]]
    return {
        "task_family": task_family,
        "selected_surface": selected.surface,
        "selected_strategy_id": selected.strategy_id,
        "alternatives": [
            {
                "surface": candidate.surface,
                "strategy_id": candidate.strategy_id,
                "status": candidate.status,
            }
            for candidate in alternatives
        ],
        "rationale": (
            f"Selected {selected.surface} because it is the highest-ranked available surface "
            f"for task_family={task_family} within the preferred surface order {list(preferred_surfaces)}."
        ),
    }


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


def ensure_model_selection_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS model_selection_records (
          id TEXT PRIMARY KEY,
          task_id TEXT NOT NULL,
          phase TEXT,
          task_type TEXT NOT NULL,
          selected_model TEXT NOT NULL,
          reasoning_level TEXT NOT NULL,
          selection_reason TEXT NOT NULL,
          fallback_model TEXT,
          tokens_used INTEGER,
          cost_estimate REAL,
          latency_ms INTEGER,
          outcome TEXT,
          caveat TEXT,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_model_selection_records_task
          ON model_selection_records(task_id, created_at DESC)
        """
    )


def record_model_selection(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    phase: str | None,
    task_type: str,
    selected_model: str,
    reasoning_level: str,
    selection_reason: str,
    fallback_model: str | None = None,
    tokens_used: int | None = None,
    cost_estimate: float | None = None,
    latency_ms: int | None = None,
    outcome: str | None = None,
    caveat: str | None = None,
) -> str:
    ensure_model_selection_schema(conn)
    record_id = f"model-selection-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO model_selection_records (
          id, task_id, phase, task_type, selected_model, reasoning_level,
          selection_reason, fallback_model, tokens_used, cost_estimate,
          latency_ms, outcome, caveat, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            task_id,
            phase,
            task_type,
            selected_model,
            reasoning_level,
            selection_reason,
            fallback_model,
            tokens_used,
            cost_estimate,
            latency_ms,
            outcome,
            caveat,
            _now_iso(),
        ),
    )
    return record_id


def list_model_selection_records(
    conn: sqlite3.Connection, *, task_id: str | None = None
) -> list[dict[str, Any]]:
    ensure_model_selection_schema(conn)
    params: tuple[str, ...] = ()
    where = ""
    if task_id:
        where = "WHERE task_id = ?"
        params = (task_id,)
    return [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT *
            FROM model_selection_records
            {where}
            ORDER BY created_at DESC
            LIMIT 100
            """,
            params,
        ).fetchall()
    ]


def select_developer_experience_route(
    *,
    capability_id: str,
    task_signals: set[str],
    second_brain_available: bool,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    policy = load_developer_experience_routing_policy(policy_path)
    rules = policy.get("capability_rules", {})
    if not isinstance(rules, dict) or capability_id not in rules:
        raise StrategySelectionError(f"Unknown DX capability: {capability_id}")
    rule = rules[capability_id]
    if not isinstance(rule, dict):
        raise StrategySelectionError(f"Invalid DX capability rule: {capability_id}")

    if capability_id == "typescript_specialist" and "simple_non_typescript_work" in task_signals:
        return {
            "selected_capability": "dx_optimizer",
            "mode": "compact_audit",
            "reasoning_level": "low",
            "selection_reason": "Simple non-TypeScript work avoids TypeScript specialist routing.",
            "second_brain_available": second_brain_available,
            "second_brain_required": False,
            "human_gate_required": False,
        }

    mode = str(rule.get("default_mode", "compact_audit"))
    reasoning_level = str(rule.get("default_reasoning_level", "medium"))
    escalation_triggers = set(policy.get("escalation_triggers", []))
    matched_escalations = sorted(task_signals & escalation_triggers)
    if matched_escalations:
        reasoning_level = "high"
    human_gate_triggers = set(rule.get("human_gate_triggers", []))
    human_gate_required = bool(task_signals & human_gate_triggers)
    if "file_changes_requested" in task_signals and mode != "review_only":
        mode = "implementation"
    elif "repo_wide_dx_audit" in task_signals:
        mode = "full_audit"

    return {
        "selected_capability": capability_id,
        "mode": mode,
        "reasoning_level": reasoning_level,
        "selection_reason": _dx_selection_reason(
            capability_id=capability_id,
            mode=mode,
            reasoning_level=reasoning_level,
            matched_escalations=matched_escalations,
        ),
        "second_brain_available": second_brain_available,
        "second_brain_required": bool(
            (policy.get("second_brain_policy") or {}).get("peer_run_requires_second_brain")
        ),
        "human_gate_required": human_gate_required,
    }


def _dx_selection_reason(
    *,
    capability_id: str,
    mode: str,
    reasoning_level: str,
    matched_escalations: list[str],
) -> str:
    if matched_escalations:
        return (
            f"Selected {capability_id} in {mode} with {reasoning_level} reasoning because "
            f"escalation triggers matched: {', '.join(matched_escalations)}."
        )
    return (
        f"Selected {capability_id} in {mode} with {reasoning_level} reasoning "
        "from DX routing metadata."
    )
