from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.execution_strategy import (  # noqa: E402
    StrategySelectionError,
    build_strategy_registry_snapshot,
    compile_execution_strategy,
    list_strategy_candidates,
    load_strategy_catalog,
    load_task_specs,
    recommend_execution_surface,
    validate_strategy_catalog,
)


def test_catalog_validation_and_snapshot() -> None:
    task_specs = load_task_specs(ROOT / "config" / "execution-strategies" / "task-specs.json")
    strategy_catalog = load_strategy_catalog(ROOT / "config" / "execution-strategies" / "strategies.json")

    errors = validate_strategy_catalog(task_specs, strategy_catalog)
    assert errors == []

    snapshot = build_strategy_registry_snapshot(task_specs, strategy_catalog)
    selected = snapshot["strategy_selection"]
    assert len(selected) == 2
    surfaces = {row["surface"] for row in selected}
    assert surfaces == {"claude_code", "codex"}


def test_compile_execution_strategy_for_codex() -> None:
    compiled = compile_execution_strategy(
        objective="Audit the current implementation and ship a scoped fix with tests",
        task_family="audit_and_implement",
        surface="codex",
        task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
        strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
    )

    assert compiled["strategy_id"] == "audit_and_implement_codex_v1"
    assert compiled["strategy_status"] == "validated"
    assert "Task Family: audit_and_implement" in compiled["compiled_instruction"]


def test_compile_unknown_task_family_raises() -> None:
    with pytest.raises(StrategySelectionError, match="Unknown task family"):
        compile_execution_strategy(
            objective="irrelevant",
            task_family="not_real",
            surface="codex",
            task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
            strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
        )


def test_list_strategy_candidates_prefers_validated_entries() -> None:
    candidates = list_strategy_candidates(
        task_family="audit_and_implement",
        task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
        strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
    )

    assert [candidate.surface for candidate in candidates] == ["claude_code", "codex"]
    assert all(candidate.status == "validated" for candidate in candidates)


def test_recommend_execution_surface_prefers_codex_first() -> None:
    recommendation = recommend_execution_surface(
        task_family="audit_and_implement",
        preferred_surfaces=("codex", "claude_code"),
        task_specs_path=ROOT / "config" / "execution-strategies" / "task-specs.json",
        strategies_path=ROOT / "config" / "execution-strategies" / "strategies.json",
    )

    assert recommendation["selected_surface"] == "codex"
    assert recommendation["selected_strategy_id"] == "audit_and_implement_codex_v1"
    assert recommendation["alternatives"][0]["surface"] == "claude_code"
