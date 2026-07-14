from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "aios-ui" / "fixtures" / "v2-vertical-slice-fixtures.json"
REQUIRED_STATES = {"healthy", "empty", "blocked", "failed", "needs_review", "closed"}


def _load_document() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_v2_fixture_document_covers_the_vertical_state_contract() -> None:
    document = _load_document()
    assert document["schema_version"] == "aios-v2-vertical-fixtures-v0.1"
    assert document["owner"] == "python-control-plane"
    fixtures = document["fixtures"]
    assert isinstance(fixtures, list)
    assert {fixture["state"] for fixture in fixtures} == REQUIRED_STATES


def test_v2_fixture_references_are_internally_consistent() -> None:
    document = _load_document()
    fixtures = document["fixtures"]
    assert isinstance(fixtures, list)

    for fixture in fixtures:
        evidence = fixture["evidence"]
        approvals = fixture["approvals"]
        run = fixture["run"]
        assert isinstance(evidence, list)
        assert isinstance(approvals, list)
        assert isinstance(run, dict)
        evidence_ids = {item["id"] for item in evidence}
        approval_ids = {item["id"] for item in approvals}
        assert set(run["evidence_ids"]).issubset(evidence_ids)
        assert set(run["approval_ids"]).issubset(approval_ids)
        assert fixture["route"]["authority"] == "python-control-plane"
        assert fixture["projection"]["next_action"] is None or fixture["run"]["next_action_id"]
