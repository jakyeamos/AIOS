from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.planning_workflow_detection import (  # noqa: E402
    detect_planning_workflow,
    load_gsd_phase_registry,
)


def test_gsd_plan_phase_alias_resolves_to_gsd_ready_plan() -> None:
    result = detect_planning_workflow("/gsdplanphase 20")

    assert result.workflow == "gsd"
    assert result.phase == "plan"
    assert result.handoff_target == "gsd"
    assert result.output_format == "gsd_ready_plan"
    assert result.source_invocation == "slash_command"
    assert result.matched_alias == "/gsdplanphase"


def test_natural_language_planning_resolves_to_aios_plan() -> None:
    result = detect_planning_workflow("Create an implementation plan for the routing update")

    assert result.workflow == "aios"
    assert result.phase == "plan"
    assert result.output_format == "execution_symmetric_plan"
    assert result.source_invocation == "natural_language_planning"
    assert result.signals == ("natural_language_planning",)


def test_slash_overrides_do_not_replace_workflow_detection() -> None:
    result = detect_planning_workflow("/no-subagents /gsdplanphase 20")

    assert result.workflow == "gsd"
    assert result.phase == "plan"
    assert result.slash_overrides == ("no_subagents",)
    assert "invocation hints and overrides" in result.rationale


def test_configured_alias_can_change_without_code_edits(tmp_path: Path) -> None:
    registry_path = tmp_path / "gsd-workflow-phases.json"
    registry_path.write_text(
        json.dumps(
            {
                "workflow": {"id": "gsd", "handoff_target": "gsd"},
                "phases": {
                    "plan": {
                        "output_format": "custom_gsd_plan",
                        "aliases": ["/custom-plan"],
                    }
                },
                "slash_overrides": {},
            }
        ),
        encoding="utf-8",
    )

    result = detect_planning_workflow("/custom-plan", registry_path=registry_path)

    assert result.workflow == "gsd"
    assert result.phase == "plan"
    assert result.output_format == "custom_gsd_plan"
    assert result.matched_alias == "/custom-plan"


def test_audit_to_implementation_prompt_is_detected() -> None:
    result = detect_planning_workflow("Turn the security audit findings into implementation fixes")

    assert result.workflow == "aios"
    assert result.phase == "plan"
    assert result.source_invocation == "audit_to_implementation_prompt"
    assert result.output_format == "audit_to_implementation_plan"


def test_generated_implementation_prompt_is_detected() -> None:
    result = detect_planning_workflow("Generate an implementation prompt to build the planner")

    assert result.workflow == "aios"
    assert result.phase == "plan"
    assert result.source_invocation == "generated_implementation_prompt"
    assert result.output_format == "implementation_prompt_plan"


def test_cli_shaped_context_is_detected() -> None:
    result = detect_planning_workflow('aios start-work "plan the next workflow update"')

    assert result.workflow == "aios"
    assert result.phase == "plan"
    assert result.source_invocation == "cli_routing"
    assert result.output_format == "execution_symmetric_plan"


def test_registry_validation_requires_phases(tmp_path: Path) -> None:
    registry_path = tmp_path / "invalid.json"
    registry_path.write_text(json.dumps({"phases": {}}), encoding="utf-8")

    try:
        load_gsd_phase_registry(registry_path)
    except ValueError as exc:
        assert "non-empty phases" in str(exc)
    else:
        raise AssertionError("Expected invalid registry to fail validation")
