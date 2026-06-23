from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.planning_lenses import (  # noqa: E402
    load_planning_lens_registry,
    select_planning_lenses,
)


def _keys(selection: object) -> set[str]:
    return {lens.key for lens in selection.lenses}


def test_selects_lenses_from_task_type() -> None:
    selection = select_planning_lenses(task_types=("feature_implementation",))

    keys = _keys(selection)
    assert "product-requirements" in keys
    assert "architecture" in keys
    assert "testing" in keys
    assert "validation-strategy" in keys
    assert "executor-readiness" in keys


def test_selects_gsd_plan_phase_lenses_from_workflow_context() -> None:
    selection = select_planning_lenses(workflow="gsd", phase="plan")

    keys = _keys(selection)
    assert "executor-readiness" in keys
    assert "constraint-preservation" in keys
    assert "artifact-definition" in keys
    assert "validation-strategy" in keys
    assert "escalation-clarity" in keys
    assert any("workflow_phase:gsd:plan" in lens.sources for lens in selection.lenses)


def test_requested_lenses_supplement_automatic_selection() -> None:
    selection = select_planning_lenses(
        task_types=("code_refactor",),
        requested_lenses=("observability", "not-a-lens"),
    )

    keys = _keys(selection)
    assert "code-quality" in keys
    assert "maintainability" in keys
    assert "observability" in keys
    assert selection.unknown_requested_lenses == ("not-a-lens",)


def test_high_risk_required_safety_lenses_are_preserved_with_manual_requests() -> None:
    selection = select_planning_lenses(
        task_types=("feature_implementation",),
        risk_level="high_risk",
        requested_lenses=("documentation",),
    )

    keys = _keys(selection)
    for required in {
        "risk-management",
        "rollback-safety",
        "escalation-clarity",
        "threat-modeling",
        "least-privilege",
        "secrets-safety",
    }:
        assert required in keys
        lens = next(item for item in selection.lenses if item.key == required)
        assert lens.required is True
    assert "documentation" in keys


def test_registry_aliases_can_use_underscore_task_types(tmp_path: Path) -> None:
    registry_path = tmp_path / "planning-lenses.json"
    registry_path.write_text(
        json.dumps(
            {
                "lenses": {
                    "custom-lens": {
                        "purpose": "Custom test lens",
                        "standard_refs": [],
                    }
                },
                "task_type_mappings": {"custom_task": ["custom-lens"]},
            }
        ),
        encoding="utf-8",
    )

    selection = select_planning_lenses(
        task_types=("custom_task",),
        registry_path=registry_path,
    )

    assert _keys(selection) == {"custom-lens"}


def test_registry_validation_requires_lenses(tmp_path: Path) -> None:
    registry_path = tmp_path / "invalid.json"
    registry_path.write_text(json.dumps({"lenses": {}}), encoding="utf-8")

    try:
        load_planning_lens_registry(registry_path)
    except ValueError as exc:
        assert "non-empty lenses" in str(exc)
    else:
        raise AssertionError("Expected invalid registry to fail validation")
