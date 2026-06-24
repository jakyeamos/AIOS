from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.commit_quality_ladder import (  # noqa: E402
    LadderCheck,
    _handler_before_send_findings,
    check_aios_evidence_artifacts,
    check_aios_verifier_artifacts,
    check_confident_event_loop_ordering,
    check_global_standards_inventory,
    check_quality_gate_registry,
    check_quality_pipeline_includes_aios,
    check_standards_health_registry,
    check_success_criteria_registry,
    emit_ladder_audit,
    exit_code,
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
                "knownGates": ["test_quality", "architecture", "pre_cr"],
                "projects": [],
            }
        ),
        encoding="utf-8",
    )

    result = check_quality_gate_registry(tmp_path)

    assert result.status == "fail"
    assert ".aios-quality-gate.json is missing" in result.detail


def test_quality_gate_registry_requires_thermo_gate(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "quality-gates.json").write_text(
        json.dumps(
            {
                "version": 1,
                "knownGates": ["test_quality", "architecture", "pre_cr"],
                "projects": [
                    {
                        "projectId": "aios",
                        "gates": {
                            "test_quality": {"preCommitCommands": [["true"]]},
                            "architecture": {"preCommitCommands": [["true"]]},
                            "pre_cr": {"preCommitCommands": [["true"]]},
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".aios-quality-gate.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projectId": "aios",
                "preCommitGates": ["test_quality", "architecture", "pre_cr"],
            }
        ),
        encoding="utf-8",
    )

    result = check_quality_gate_registry(tmp_path)

    assert result.status == "fail"
    assert "known gate missing: thermo_nuclear_simplification" in result.evidence


def test_quality_pipeline_includes_thermo_gate_for_aios(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "quality-pipeline.json").write_text(
        json.dumps(
            {
                "standard": {
                    "gates": [
                        {"key": "lint"},
                        {"key": "test"},
                        {"key": "architecture"},
                        {"key": "pre_pr_readiness"},
                        {"key": "thermo_nuclear_simplification"},
                    ]
                },
                "projects": [
                    {
                        "project_id": "aios",
                        "gates": {
                            "lint": {},
                            "test": {},
                            "architecture": {},
                            "pre_pr_readiness": {},
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = check_quality_pipeline_includes_aios(tmp_path)

    assert result.status == "fail"
    assert "aios gate not configured: thermo_nuclear_simplification" in result.evidence


def test_success_criteria_registry_requires_thermo_spec_path(tmp_path: Path) -> None:
    registry = tmp_path / "config" / "success-criteria"
    registry.mkdir(parents=True)
    (registry / "registry.json").write_text(
        json.dumps(
            {
                "criteria": [
                    {
                        "id": "thermo-nuclear-simplification",
                        "title": "Thermo",
                        "path": "spec/success-criteria/thermo-nuclear-simplification.md",
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
    assert (
        "thermo-nuclear-simplification path missing: "
        "spec/success-criteria/thermo-nuclear-simplification.md"
    ) in result.evidence


def _create_evidence_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE evidence_artifacts (
          evidence_id TEXT PRIMARY KEY,
          task_id TEXT,
          run_id TEXT,
          session_id TEXT,
          phase TEXT,
          timestamp TEXT,
          agent TEXT,
          model TEXT,
          command TEXT,
          exit_code INTEGER,
          stdout_path TEXT,
          stderr_path TEXT,
          output_hash TEXT,
          parsed_summary TEXT,
          diff_hash TEXT,
          commit_hash TEXT,
          status TEXT,
          caveats_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT
        )
        """
    )


def _create_verifier_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE verifier_artifacts (
          verifier_id TEXT PRIMARY KEY,
          task_id TEXT,
          run_id TEXT,
          session_id TEXT,
          verifier_agent TEXT,
          model TEXT,
          inputs_reviewed_json TEXT NOT NULL DEFAULT '[]',
          checks_performed_json TEXT NOT NULL DEFAULT '[]',
          result TEXT NOT NULL,
          blocking_issues_json TEXT NOT NULL DEFAULT '[]',
          non_blocking_issues_json TEXT NOT NULL DEFAULT '[]',
          recommended_next_phase TEXT NOT NULL,
          evidence_refs_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT
        )
        """
    )


def test_aios_evidence_check_is_unknown_without_fresh_artifacts(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    _create_evidence_table(conn)
    conn.commit()
    conn.close()

    result = check_aios_evidence_artifacts(
        db_path=db_path,
        run_id="run-1",
        session_id="session-1",
    )

    assert result.status == "skip"
    assert "unknown" in result.detail


def test_aios_evidence_check_attaches_fresh_refs(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    _create_evidence_table(conn)
    conn.execute(
        """
        INSERT INTO evidence_artifacts (
          evidence_id, task_id, run_id, session_id, phase, timestamp, agent, model,
          command, exit_code, stdout_path, stderr_path, output_hash, parsed_summary,
          diff_hash, commit_hash, status, caveats_json, created_at
        )
        VALUES (
          'ev-1', 'task', 'run-1', 'session-1', 'verify', '2026-06-23T00:00:00Z',
          'codex', 'gpt', 'pnpm test', 0, NULL, NULL, 'abc', 'passed',
          NULL, NULL, 'pass', '[]', '2026-06-23T00:00:00Z'
        )
        """
    )
    conn.commit()
    conn.close()

    result = check_aios_evidence_artifacts(
        db_path=db_path,
        run_id="run-1",
        session_id="session-1",
    )

    assert result.status == "pass"
    assert result.evidence == ("evidence-artifact: ev-1 status=pass command=pnpm test",)


def test_ladder_audit_records_failed_checks(tmp_path: Path) -> None:
    emit_ladder_audit(
        tmp_path,
        [
            LadderCheck(
                "standards.context_validate",
                "Context standards validate",
                "fail",
                "Context compiler validation failed.",
                ("tools/context-compile.mjs failed",),
            )
        ],
        decision="block",
    )

    events_path = tmp_path / ".aios" / "audit" / "gate-events.jsonl"
    event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])

    assert event["gate"] == "AIOS"
    assert event["rule_id"] == "standards.context_validate"
    assert event["event_type"] == "commit_blocked"
    assert event["decision"] == "block"
    assert event["severity"] == "error"
    assert event["learning_lesson"]


def test_ladder_audit_warns_for_unprotected_branch_failures(tmp_path: Path) -> None:
    emit_ladder_audit(
        tmp_path,
        [
            LadderCheck(
                "standards.context_validate",
                "Context standards validate",
                "fail",
                "Context compiler validation failed.",
                ("tools/context-compile.mjs failed",),
            )
        ],
        decision="warn",
    )

    events_path = tmp_path / ".aios" / "audit" / "gate-events.jsonl"
    event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])

    assert event["decision"] == "warn"
    assert event["severity"] == "warning"
    assert "warning only" in event["summary"]


def test_ladder_exit_code_allows_warn_only_failures() -> None:
    checks = [
        LadderCheck(
            "standards.context_validate",
            "Context standards validate",
            "fail",
            "Context compiler validation failed.",
            (),
        )
    ]

    assert exit_code(checks, decision="warn") == 0
    assert exit_code(checks, decision="block") == 1


def test_aios_verifier_check_is_unknown_without_fresh_artifacts(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    _create_verifier_table(conn)
    conn.commit()
    conn.close()

    result = check_aios_verifier_artifacts(
        db_path=db_path,
        run_id="run-1",
        session_id="session-1",
    )

    assert result.status == "skip"
    assert "warn-only" in result.detail


def test_aios_verifier_check_attaches_fresh_refs(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    _create_verifier_table(conn)
    conn.execute(
        """
        INSERT INTO verifier_artifacts (
          verifier_id, task_id, run_id, session_id, verifier_agent, model,
          inputs_reviewed_json, checks_performed_json, result, blocking_issues_json,
          non_blocking_issues_json, recommended_next_phase, evidence_refs_json, created_at
        )
        VALUES (
          'ver-1', 'run-1', 'run-1', 'session-1', 'reviewer', 'gpt',
          '["task_spec", "changed_files", "evidence_artifacts"]', '["diff"]',
          'pass', '[]', '[]', 'closeout',
          '["evidence-artifact: ev-1 status=pass command=pnpm test"]',
          '2026-06-23T00:00:00Z'
        )
        """
    )
    conn.commit()
    conn.close()

    result = check_aios_verifier_artifacts(
        db_path=db_path,
        run_id="run-1",
        session_id="session-1",
    )

    assert result.status == "pass"
    assert result.evidence == ("verifier artifact: ver-1 result=pass next=closeout",)
