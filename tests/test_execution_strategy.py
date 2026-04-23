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
    load_strategy_catalog,
    load_task_specs,
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
