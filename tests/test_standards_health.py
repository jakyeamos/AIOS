from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import get_args

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.standards_health import (  # noqa: E402
    Provenance,
    _evaluate_known_standard,
    ensure_standards_health_schema,
    evaluate_and_record,
    load_registry,
)

DELT_01_DOMAINS = {
    "architecture",
    "testing",
    "maintainability",
    "security",
    "ux",
    "observability",
    "documentation",
    "launch_readiness",
    "agent_readiness",
    "standards_compliance",
}
NEW_STANDARD_IDS = {
    "maintainability.dead_code_signal",
    "ux.operator_clarity",
    "launch_readiness.deployable",
    "agent_readiness.handoff_packet",
    "standards_compliance.profile_attached",
}


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


def _production_registry_payload() -> dict[str, object]:
    with (ROOT / "config" / "standards" / "registry.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _production_registry_copy(tmp_path: Path) -> Path:
    registry_path = tmp_path / "registry.json"
    _write_registry(registry_path, _production_registry_payload())
    return registry_path


def _standard_by_id(tmp_path: Path, standard_id: str):
    _, standards = load_registry(_production_registry_copy(tmp_path))
    return next(standard for standard in standards if standard.id == standard_id)


def test_registry_covers_all_delt_01_domains(tmp_path: Path) -> None:
    _, standards = load_registry(_production_registry_copy(tmp_path))
    domains = {standard.domain for standard in standards}

    assert DELT_01_DOMAINS.issubset(domains)
    assert {
        "architecture",
        "code_quality",
        "testing",
        "security",
        "observability",
        "documentation",
        "workflow_agent_control",
        "release_ci_discipline",
        "product_readiness",
        "experimentation",
        "maintainability",
        "ux",
        "launch_readiness",
        "agent_readiness",
        "standards_compliance",
    }.issubset(domains)


def test_registry_profile_version_bumped_to_2026_06_0(tmp_path: Path) -> None:
    profile, standards = load_registry(_production_registry_copy(tmp_path))
    new_standards = {
        standard.id: standard for standard in standards if standard.id in NEW_STANDARD_IDS
    }

    assert profile["version"] == "2026.06.0"
    assert profile["default_attached_version"] == "2026.04.0"
    assert set(new_standards) == NEW_STANDARD_IDS
    assert all(standard.version == "2026.06.0" for standard in new_standards.values())
    assert all(standard.introduced_version == "2026.06.0" for standard in new_standards.values())


def test_new_standards_have_required_fields(tmp_path: Path) -> None:
    _, standards = load_registry(_production_registry_copy(tmp_path))
    new_standards = {
        standard.id: standard for standard in standards if standard.id in NEW_STANDARD_IDS
    }

    for standard in new_standards.values():
        assert standard.title
        assert standard.description
        assert standard.weight > 0
        assert standard.severity_if_missing >= 1
        assert standard.remediation_playbook["summary"]
        assert float(standard.remediation_playbook["effort"]) > 0
        assert float(standard.remediation_playbook["leverage"]) > 0
        assert standard.applicability["projects"]
        assert standard.waiver_policy


def test_profile_domains_list_contains_all_ten_delt01_domains(tmp_path: Path) -> None:
    profile, _ = load_registry(_production_registry_copy(tmp_path))

    assert DELT_01_DOMAINS.issubset(set(profile["domains"]))


def test_evaluator_returns_unknown_for_maintainability_dead_code_signal(tmp_path: Path) -> None:
    conn = _base_conn()
    status, reason, confidence, measured_state, evidence, evaluator_type = _evaluate_known_standard(
        conn,
        project_id="proj",
        standard=_standard_by_id(tmp_path, "maintainability.dead_code_signal"),
        repo_path=ROOT,
    )

    assert status == "unknown"
    assert "manual" in reason or "standards-override" in reason
    assert 0.0 <= confidence <= 0.5
    assert measured_state == {"required_tool": "vulture_or_knip"}
    assert evidence == []
    assert evaluator_type in {"auto", "manual"}


def test_evaluator_returns_unknown_for_each_new_domain(tmp_path: Path) -> None:
    conn = _base_conn()

    for standard_id in NEW_STANDARD_IDS:
        status, reason, *_ = _evaluate_known_standard(
            conn,
            project_id="proj",
            standard=_standard_by_id(tmp_path, standard_id),
            repo_path=ROOT,
        )
        assert status == "unknown"
        assert reason


def test_agent_readiness_evaluator_flips_to_pass_when_briefing_packet_present(
    tmp_path: Path,
) -> None:
    conn = _base_conn()
    standard = _standard_by_id(tmp_path, "agent_readiness.handoff_packet")

    status_without_packet, *_ = _evaluate_known_standard(
        conn,
        project_id="proj",
        standard=standard,
        repo_path=ROOT,
    )
    assert status_without_packet == "unknown"

    conn.execute(
        """
        CREATE TABLE briefing_packets (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            selected_standards_json TEXT NOT NULL DEFAULT '[]',
            selected_criteria_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT '2026-05-24T00:00:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO briefing_packets (
            id, project_id, selected_standards_json, selected_criteria_json, created_at
        )
        VALUES (
            'packet-1', 'proj', '["architecture.boundary_enforcement"]',
            '["testing-trust"]', '2026-05-24T00:00:00Z'
        )
        """
    )

    status, reason, confidence, measured_state, evidence, evaluator_type = _evaluate_known_standard(
        conn,
        project_id="proj",
        standard=standard,
        repo_path=ROOT,
    )
    assert status == "pass"
    assert "standards and criteria" in reason
    assert confidence >= 0.6
    assert measured_state["selected_standards_count"] == 1
    assert measured_state["selected_criteria_count"] == 1
    assert evidence == ["briefing_packets"]
    assert evaluator_type == "auto"


def test_standards_compliance_evaluator_returns_pass_when_profile_attached_and_coverage_high(
    tmp_path: Path,
) -> None:
    conn = _base_conn()
    standard = _standard_by_id(tmp_path, "standards_compliance.profile_attached")

    status_without_profile, *_ = _evaluate_known_standard(
        conn,
        project_id="missing",
        standard=standard,
        repo_path=ROOT,
    )
    assert status_without_profile == "unknown"

    conn.execute(
        """
        INSERT INTO project_standards_profiles (
            project_id, profile_id, attached_version, latest_version, migration_mode
        )
        VALUES ('proj', 'aios-core', '2026.06.0', '2026.06.0', 'current')
        """
    )
    conn.execute(
        """
        INSERT INTO standards_health_snapshots (
            id, project_id, profile_id, attached_version, latest_version, standards_version,
            overall_score, weighted_delta, max_penalty, unmet_standards_count,
            critical_delta_count, regression_count, unknown_count, unknown_coverage,
            evaluation_confidence, domain_scores_json, score_explain_json, migration_json,
            created_at
        )
        VALUES (
            'snapshot-low', 'proj', 'aios-core', '2026.06.0', '2026.06.0', '2026.06.0',
            90.0, 1.0, 10.0, 1, 0, 0, 1, 0.2, 0.9, '{}', '{}', '{}',
            '2026-05-24T00:00:00Z'
        )
        """
    )

    status, _, confidence, measured_state, *_ = _evaluate_known_standard(
        conn,
        project_id="proj",
        standard=standard,
        repo_path=ROOT,
    )
    assert status == "pass"
    assert confidence == 0.85
    assert measured_state["unknown_coverage"] == 0.2

    conn.execute(
        """
        INSERT INTO standards_health_snapshots (
            id, project_id, profile_id, attached_version, latest_version, standards_version,
            overall_score, weighted_delta, max_penalty, unmet_standards_count,
            critical_delta_count, regression_count, unknown_count, unknown_coverage,
            evaluation_confidence, domain_scores_json, score_explain_json, migration_json,
            created_at
        )
        VALUES (
            'snapshot-mid', 'proj', 'aios-core', '2026.06.0', '2026.06.0', '2026.06.0',
            70.0, 3.0, 10.0, 3, 1, 0, 3, 0.5, 0.7, '{}', '{}', '{}',
            '2026-05-24T00:01:00Z'
        )
        """
    )
    partial_status, *_ = _evaluate_known_standard(
        conn,
        project_id="proj",
        standard=standard,
        repo_path=ROOT,
    )
    assert partial_status == "partial"


def test_compute_score_emits_all_ten_delt01_domains(tmp_path: Path) -> None:
    registry_path = _production_registry_copy(tmp_path)
    conn = _base_conn()
    conn.execute(
        """
        INSERT INTO project_standards_profiles (
            project_id, profile_id, attached_version, latest_version, migration_mode
        )
        VALUES ('proj', 'aios-core', '2026.06.0', '2026.06.0', 'current')
        """
    )

    evaluate_and_record(conn, project_id="proj", registry_path=registry_path)
    conn.commit()

    row = conn.execute(
        "SELECT domain_scores_json FROM standards_health_snapshots ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    domain_scores = json.loads(row[0])
    assert DELT_01_DOMAINS.issubset(set(domain_scores))


def test_provenance_import_from_capability_truth_succeeds() -> None:
    assert set(get_args(Provenance)) == {"confirmed", "inferred", "missing", "contradictory"}


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

    snapshot_row = conn.execute(
        "SELECT migration_json FROM standards_health_snapshots LIMIT 1"
    ).fetchone()
    assert snapshot_row is not None
    migration = json.loads(snapshot_row[0])
    assert migration["attached_version"] == "1.0.0"
    assert migration["latest_version"] == "2.0.0"
    assert migration["migration_delta_count"] == 1

    statuses = dict(
        conn.execute("SELECT standard_id, status FROM standards_assessments").fetchall()
    )
    assert statuses["s.current"] == "pass"
    assert statuses["s.new"] == "not_applicable"
