from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.quality_gate_audit import (  # noqa: E402
    GateAuditEvent,
    append_gate_audit_event,
    build_gate_audit_event,
    dedupe_fingerprint,
    quality_gate_decision,
    redact_secrets,
)


def test_build_event_has_schema_and_stable_fingerprint(tmp_path: Path) -> None:
    event = build_gate_audit_event(
        repo_root=tmp_path,
        gate="AIOS",
        event_type="commit_blocked",
        severity="error",
        category="test",
        rule_id="tests.failed",
        rule_name="Tests failed",
        decision="block",
        summary="Commit blocked because tests failed.",
        evidence=[{"file": "tests/test_app.py", "line_start": 4, "reason": "failure"}],
        failure_pattern="tests failed in changed area",
        required_fix="Fix the failing test.",
        learning_lesson="Run the touched test before committing.",
    )

    assert event["schema_version"] == "1.0"
    assert event["repo"] == tmp_path.name
    assert event["gate"] == "AIOS"
    assert event["dedupe_fingerprint"] == dedupe_fingerprint(
        "AIOS",
        "tests.failed",
        ["tests/test_app.py"],
        "tests failed in changed area",
    )
    assert event["event_id"]


def test_append_event_writes_jsonl_summary_and_learning_lessons(tmp_path: Path) -> None:
    event: GateAuditEvent = build_gate_audit_event(
        repo_root=tmp_path,
        gate="Pre-CR",
        event_type="iteration_forced",
        severity="error",
        category="test",
        rule_id="pre-cr.coverage",
        rule_name="Changed-line coverage",
        decision="force_iteration",
        summary="Pre-CR forced iteration because changed-line coverage was 42%.",
        evidence=[{"file": "src/app.ts", "line_start": 12, "reason": "uncovered changed line"}],
        failure_pattern="changed lines lacked coverage",
        root_cause_hypothesis="Implementation changed behavior before adding focused tests.",
        required_fix="Add focused coverage for changed lines.",
        learning_lesson="Add or update tests for changed lines before running Pre-CR.",
    )

    append_gate_audit_event(tmp_path, event)
    append_gate_audit_event(tmp_path, event)

    audit_dir = tmp_path / ".aios" / "audit"
    rows = [
        json.loads(line)
        for line in (audit_dir / "gate-events.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert len(rows) == 2
    assert rows[0]["summary"] == "Pre-CR forced iteration because changed-line coverage was 42%."
    assert "Current run outcome" in (audit_dir / "gate-summary.md").read_text(encoding="utf-8")
    lessons = (audit_dir / "learning-lessons.md").read_text(encoding="utf-8")
    assert "changed lines lacked coverage" in lessons
    assert "Seen: 2 times" in lessons


def test_redacts_secret_values() -> None:
    text = 'apiKey = "sk_live_1234567890abcdef" and token: "ghp_1234567890abcdef"'

    redacted = redact_secrets(text)

    assert "sk_live_1234567890abcdef" not in redacted
    assert "ghp_1234567890abcdef" not in redacted
    assert "[REDACTED]" in redacted


def test_quality_gate_decision_blocks_main_and_dev_environment(tmp_path: Path) -> None:
    assert quality_gate_decision(tmp_path, branch="main", env={}) == "block"
    assert quality_gate_decision(tmp_path, branch="develop", env={}) == "block"
    assert (
        quality_gate_decision(
            tmp_path,
            branch="feature/hoopscout",
            env={"AIOS_DEV_ENVIRONMENT": "1"},
        )
        == "block"
    )


def test_quality_gate_decision_warns_on_unprotected_feature_branch(tmp_path: Path) -> None:
    assert quality_gate_decision(tmp_path, branch="feature/hoopscout", env={}) == "warn"
    assert (
        quality_gate_decision(
            tmp_path,
            branch="main",
            env={"AIOS_QUALITY_GATE_MODE": "warn"},
        )
        == "warn"
    )
