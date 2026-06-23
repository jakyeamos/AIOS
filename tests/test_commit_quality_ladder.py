from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.commit_quality_ladder import (  # noqa: E402
    _handler_before_send_findings,
    check_confident_event_loop_ordering,
    check_global_standards_inventory,
    check_quality_gate_registry,
    check_standards_health_registry,
    check_success_criteria_registry,
)


def test_handler_before_send_is_blocked() -> None:
    text = """
const worker = new Worker("worker.js");
worker.addEventListener("message", handleResponse);
worker.postMessage({ type: "run" });
"""

    findings = _handler_before_send_findings("src/worker.ts", text)

    assert findings
    assert "send first" in findings[0]


def test_handler_before_send_can_document_real_runtime_reason() -> None:
    text = """
const worker = new Worker("worker.js");
// aios-quality: allow handler-before-send: worker can synchronously replay queued messages.
worker.addEventListener("message", handleResponse);
worker.postMessage({ type: "run" });
"""

    findings = _handler_before_send_findings("src/worker.ts", text)

    assert findings == []


def test_event_loop_check_ignores_non_code_files(tmp_path: Path) -> None:
    (tmp_path / ".githooks").mkdir()
    (tmp_path / ".githooks" / "pre-commit").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (tmp_path / "note.md").write_text(
        'worker.addEventListener("message", handleResponse)\nworker.postMessage({})\n',
        encoding="utf-8",
    )

    result = check_confident_event_loop_ordering(tmp_path, ["note.md"])

    assert result.status == "pass"


def test_global_standards_inventory_requires_acceptance_criteria(tmp_path: Path) -> None:
    standards = tmp_path / "aios" / "context" / "standards"
    standards.mkdir(parents=True)
    (standards / "global.test.md").write_text(
        """---
id: global.test
title: Test
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Test standard.
applies_when:
  - all_tasks
tags:
  - test
---
Body.
""",
        encoding="utf-8",
    )

    result = check_global_standards_inventory(tmp_path)

    assert result.status == "fail"
    assert "missing Acceptance Criteria" in result.evidence[0]


def test_success_criteria_registry_requires_existing_paths(tmp_path: Path) -> None:
    registry = tmp_path / "config" / "success-criteria"
    registry.mkdir(parents=True)
    (registry / "registry.json").write_text(
        json.dumps(
            {
                "criteria": [
                    {
                        "id": "missing",
                        "title": "Missing",
                        "path": "spec/success-criteria/missing.md",
                        "scope": "global",
                        "blocking": True,
                        "evaluation_method": "heuristic",
                        "applies_when": {"task_types": ["*"], "domains": ["*"]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = check_success_criteria_registry(tmp_path)

    assert result.status == "fail"
    assert "path missing" in result.evidence[0]


def test_standards_health_registry_requires_valid_rows(tmp_path: Path) -> None:
    registry = tmp_path / "config" / "standards"
    registry.mkdir(parents=True)
    (registry / "registry.json").write_text(
        json.dumps(
            {
                "profile": {"id": "aios-core"},
                "standards": [
                    {
                        "id": "bad.standard",
                        "domain": "maintainability",
                        "severity_if_missing": "severe",
                        "expected_state": {},
                        "remediation_playbook": {},
                        "applicability": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = check_standards_health_registry(tmp_path)

    assert result.status == "fail"
    assert "invalid severity_if_missing" in result.evidence[0]


def test_quality_gate_registry_requires_aios_contract(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "quality-gates.json").write_text(
        json.dumps(
            {
                "version": 1,
                "knownGates": ["trusted_tests", "architecture", "pre_cr"],
                "projects": [],
            }
        ),
        encoding="utf-8",
    )

    result = check_quality_gate_registry(tmp_path)

    assert result.status == "fail"
    assert ".aios-quality-gate.json is missing" in result.detail
