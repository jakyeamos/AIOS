from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.standards_health import evaluate_and_record, ensure_standards_health_schema  # noqa: E402


def _base_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          repo_path TEXT NOT NULL,
          obsidian_path TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('proj', 'Project', '.', '.', 'active')
        """
    )
    ensure_standards_health_schema(conn)
    return conn


def _write_registry(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_scoring_penalty_model_with_regression_unknown_and_waiver(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    _write_registry(
        registry_path,
        {
            "profile": {
                "id": "test-profile",
                "title": "Test Profile",
                "version": "1.0.0",
                "default_attached_version": "1.0.0",
                "domains": ["testing"],
            },
            "standards": [
                {
                    "id": "s.pass",
                    "title": "Pass",
                    "description": "",
                    "domain": "testing",
                    "weight": 10,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
                {
                    "id": "s.partial",
                    "title": "Partial",
                    "description": "",
                    "domain": "testing",
                    "weight": 10,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
                {
                    "id": "s.fail",
                    "title": "Fail",
                    "description": "",
                    "domain": "testing",
                    "weight": 10,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
                {
                    "id": "s.regressed",
                    "title": "Regressed",
                    "description": "",
                    "domain": "testing",
                    "weight": 10,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
                {
                    "id": "s.unknown",
                    "title": "Unknown",
                    "description": "",
                    "domain": "testing",
                    "weight": 10,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
                {
                    "id": "s.waived",
                    "title": "Waived",
                    "description": "",
                    "domain": "testing",
                    "weight": 10,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
                {
                    "id": "s.future",
                    "title": "Future",
                    "description": "",
                    "domain": "testing",
                    "weight": 10,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "2.0.0",
                    "introduced_version": "2.0.0",
                },
            ],
        },
    )

    conn = _base_conn()
    result = evaluate_and_record(
        conn,
        project_id="proj",
        project_name="Project",
        registry_path=registry_path,
        overrides={
            "s.pass": {"status": "pass", "reason": "pass"},
            "s.partial": {"status": "partial", "reason": "partial"},
            "s.fail": {"status": "fail", "reason": "fail"},
            "s.regressed": {"status": "fail", "reason": "regressed", "regression_flag": True},
            "s.unknown": {"status": "unknown", "reason": "unknown"},
            "s.waived": {
                "status": "waived",
                "reason": "waived",
                "waiver_rationale": "accepted tradeoff",
                "waiver_owner": "owner",
                "waiver_review_at": "2026-05-01",
            },
        },
    )
    conn.commit()

    assert result["health_score"] == 53.33
    assert result["regression_count"] == 1
    assert result["unknown_count"] == 1
    assert result["critical_delta_count"] == 4

    snapshot = conn.execute(
        "SELECT overall_score, max_penalty, weighted_delta FROM standards_health_snapshots LIMIT 1"
    ).fetchone()
    assert snapshot is not None
    assert snapshot[0] == 53.33
    assert snapshot[1] == 75.0
    assert snapshot[2] == 35.0


def test_delta_prioritization_and_backfill_task_generation(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    _write_registry(
        registry_path,
        {
            "profile": {
                "id": "test-profile",
                "title": "Test Profile",
                "version": "1.0.0",
                "default_attached_version": "1.0.0",
                "domains": ["architecture", "testing"],
            },
            "standards": [
                {
                    "id": "s.foundation",
                    "title": "Foundation",
                    "description": "",
                    "domain": "architecture",
                    "weight": 8,
                    "severity_if_missing": 5,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 3, "leverage": 1.4},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                    "metadata": {"foundational": True},
                },
                {
                    "id": "s.quick",
                    "title": "Quick",
                    "description": "",
                    "domain": "testing",
                    "weight": 4,
                    "severity_if_missing": 3,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 1, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
            ],
        },
    )

    conn = _base_conn()
    result = evaluate_and_record(
        conn,
        project_id="proj",
        registry_path=registry_path,
        overrides={
            "s.foundation": {"status": "fail", "reason": "needs foundational work"},
            "s.quick": {"status": "partial", "reason": "small cleanup"},
        },
    )
    conn.commit()

    assert result["delta_item_count"] == 2
    assert result["backfill_task_count"] == 2

    delta_rows = conn.execute(
        "SELECT standard_id, priority_bucket FROM standards_delta_items ORDER BY priority_score DESC"
    ).fetchall()
    bucket_by_standard = {row[0]: row[1] for row in delta_rows}
    assert bucket_by_standard["s.foundation"] == "foundational"
    assert bucket_by_standard["s.quick"] == "quick_wins"

    task_rows = conn.execute(
        "SELECT standard_id, status, priority_bucket FROM standards_backfill_tasks ORDER BY priority_score DESC"
    ).fetchall()
    assert len(task_rows) == 2
    task_by_standard = {row[0]: (row[1], row[2]) for row in task_rows}
    assert task_by_standard["s.foundation"][0] == "open"
    assert task_by_standard["s.foundation"][1] == "foundational"


def test_version_migration_delta_is_visible(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    _write_registry(
        registry_path,
        {
            "profile": {
                "id": "test-profile",
                "title": "Test Profile",
                "version": "2.0.0",
                "default_attached_version": "1.0.0",
                "domains": ["documentation"],
            },
            "standards": [
                {
                    "id": "s.current",
                    "title": "Current",
                    "description": "",
                    "domain": "documentation",
                    "weight": 2,
                    "severity_if_missing": 2,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 1, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "1.0.0",
                    "introduced_version": "1.0.0",
                },
                {
                    "id": "s.new",
                    "title": "New",
                    "description": "",
                    "domain": "documentation",
                    "weight": 6,
                    "severity_if_missing": 4,
                    "evaluation_method": "manual",
                    "expected_state": {},
                    "remediation_playbook": {"effort": 2, "leverage": 1.0},
                    "blocking_dependencies": [],
                    "version": "2.0.0",
                    "introduced_version": "2.0.0",
                },
            ],
        },
    )

    conn = _base_conn()
    evaluate_and_record(
        conn,
        project_id="proj",
        registry_path=registry_path,
        overrides={"s.current": {"status": "pass", "reason": "met"}},
    )
    conn.commit()

    snapshot_row = conn.execute("SELECT migration_json FROM standards_health_snapshots LIMIT 1").fetchone()
    assert snapshot_row is not None
    migration = json.loads(snapshot_row[0])
    assert migration["attached_version"] == "1.0.0"
    assert migration["latest_version"] == "2.0.0"
    assert migration["migration_delta_count"] == 1

    statuses = dict(conn.execute("SELECT standard_id, status FROM standards_assessments").fetchall())
    assert statuses["s.current"] == "pass"
    assert statuses["s.new"] == "not_applicable"
