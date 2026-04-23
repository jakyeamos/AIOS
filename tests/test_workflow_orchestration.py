from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.workflow_orchestration import (  # noqa: E402
    WorkflowExecutionContext,
    execute_workflow,
    load_skill_registry,
    load_workflow_registry,
    summarize_execution_report,
    validate_workflow_bindings,
)


def test_registry_bindings_are_valid() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    errors = validate_workflow_bindings(workflows, skills)
    assert errors == []
    assert "academic_paper_v1" in workflows


def test_execute_academic_workflow_with_validations(tmp_path: Path) -> None:
    prompt_registry = tmp_path / "prompt-registry.json"
    prompt_registry.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "content_writing",
                        "classification": "content_writing",
                        "tags": ["paper", "academic", "citations"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    (vault_root / "style.md").write_text("Use direct transitions and explicit claims.\n", encoding="utf-8")

    context = WorkflowExecutionContext(
        objective="Write an academic paper about retrieval quality and citation fidelity",
        workflow_key="academic_paper_v1",
        vault_root=str(vault_root),
        prompt_registry_path=str(prompt_registry),
        run_id="run-1",
        invocation_id="invoke-1",
    )

    report = execute_workflow(context)
    assert report["status"] == "completed"
    assert report["workflow_key"] == "academic_paper_v1"
    assert len(report["stages"]) >= 6

    validations = {row["validation_key"]: row for row in report["validations"]}
    assert validations["structure_checker"]["passed"] is True
    assert validations["citation_checker"]["passed"] is True
    assert validations["meaning_preservation_checker"]["passed"] is True

    artifacts = report["artifacts"]
    assert artifacts["template_id"] == "content_writing"
    assert "## References" in artifacts["humanized_text"]

    summary = summarize_execution_report(report)
    assert "academic_paper_v1" in summary
    assert "status=completed" in summary


def test_unknown_workflow_raises(tmp_path: Path) -> None:
    context = WorkflowExecutionContext(
        objective="Any objective",
        workflow_key="does_not_exist",
    )

    with pytest.raises(ValueError, match="Unknown workflow key"):
        execute_workflow(context)
