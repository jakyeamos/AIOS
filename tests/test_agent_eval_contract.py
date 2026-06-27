# ruff: noqa: E402

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_eval_contract import (
    CONTEXT_PROFILES,
    HARNESS_DIMENSION_NAMES,
    normalize_external_result,
    validate_context_profile,
    validate_harness_fixture_components,
    validate_priority,
)
from services.eval_run_service import create_eval_run, create_eval_task


def test_agent_eval_contract_import_does_not_import_aios_services() -> None:
    for module_name in list(sys.modules):
        if module_name == "agent_eval_contract" or module_name.startswith("agent_eval_contract."):
            del sys.modules[module_name]
        if module_name == "services" or module_name.startswith("services."):
            del sys.modules[module_name]

    imported = importlib.import_module("agent_eval_contract")

    assert "external_clean_room" in imported.CONTEXT_PROFILES
    assert "services" not in sys.modules
    assert not any(module_name.startswith("services.") for module_name in sys.modules)


def test_contract_validates_context_profile_and_priority() -> None:
    validate_context_profile("peer_portable_context_packet")
    validate_priority("critical")

    with pytest.raises(ValueError, match="Invalid context_profile"):
        validate_context_profile("private_magic")

    with pytest.raises(ValueError, match="Invalid priority"):
        validate_priority("urgent")


def test_eval_service_uses_contract_context_profile_validation(tmp_path: Path) -> None:
    import sqlite3

    root = Path(__file__).resolve().parents[1]
    conn = sqlite3.connect(tmp_path / "eval.db")
    conn.row_factory = sqlite3.Row
    conn.executescript((root / "schema.sql").read_text(encoding="utf-8"))
    task_id = create_eval_task(
        conn,
        repo_id="repo",
        source="controlled_benchmark",
        start_sha="abc123",
        context_profile="peer_repo_only",
        task_type="feature",
        prompt_summary="Test shared contract validation.",
        acceptance_criteria=[],
        success_criteria_files=[],
    )

    with pytest.raises(ValueError, match="Invalid context_profile"):
        create_eval_run(
            conn,
            task_id=task_id,
            condition="contract",
            mode="controlled",
            harness="pytest",
            model="gpt-5",
            context_profile="not_real",
        )


def test_harness_fixture_contract_rejects_malformed_fixture() -> None:
    with pytest.raises(ValueError, match="expected_gates entries need id and expected_decision"):
        validate_harness_fixture_components(
            task_markdown="# Task",
            expected_context_packets=["global.testing"],
            expected_gates=[{"id": "approval"}],
            expected_success_criteria=["test-quality"],
            golden_outcome_markdown="# Outcome",
            scoring={},
            runs={"aios_shadow": {"harness": {"name": "AIOS"}}},
        )


def test_external_result_normalization_matches_contract() -> None:
    normalized = normalize_external_result(
        {"success": False, "tests_run": ["pytest"], "duration_ms": 10},
        eval_task_id="task-1",
        harness="terminal-bench",
        model="gpt-5",
    )

    assert normalized["context_profile"] == "external_clean_room"
    assert normalized["final_status"] == "failed"
    assert normalized["tests_run"] == ["pytest"]
    assert set(CONTEXT_PROFILES) >= {"external_clean_room", "peer_repo_only"}
    assert "false_completion_caught" in HARNESS_DIMENSION_NAMES
