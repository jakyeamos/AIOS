# ruff: noqa: E402

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_eval_contract import (
    CONTEXT_PROFILES,
    HARNESS_DIMENSION_NAMES,
    load_release_metadata,
    load_sample,
    normalize_external_result,
    render_eval_template,
    supported_template_ids,
    validate_all_samples,
    validate_context_profile,
    validate_eval_template,
    validate_harness_fixture_components,
    validate_priority,
    validate_release_metadata,
    validate_template_directory,
)
from agent_eval_contract.fixture_runner import write_contract_fixture_bundle

from services.eval_run_service import create_eval_run, create_eval_task
from services.harness_eval import DIMENSION_NAMES


def _pop_cached_modules(prefixes: tuple[str, ...]) -> dict[str, Any]:
    removed: dict[str, Any] = {}
    for module_name in list(sys.modules):
        if any(
            module_name == prefix or module_name.startswith(f"{prefix}.") for prefix in prefixes
        ):
            removed[module_name] = sys.modules.pop(module_name)
    return removed


def _restore_cached_modules(removed: dict[str, Any]) -> None:
    # Later tests patch services.* by dotted path; leaving purged modules out
    # of sys.modules would split module identity between patch target and the
    # already-imported functions under test.
    sys.modules.update(removed)


def test_agent_eval_contract_import_does_not_import_aios_services() -> None:
    removed = _pop_cached_modules(("agent_eval_contract", "services"))
    try:
        imported = importlib.import_module("agent_eval_contract")
        direct_url = importlib.metadata.distribution("agent-eval-contract").read_text(
            "direct_url.json"
        )

        assert "clean_room" in imported.CONTEXT_PROFILES
        assert direct_url is not None
        assert "file:///Users/jakyeamos/agent-eval-contract" in direct_url
        assert "services" not in sys.modules
        assert not any(module_name.startswith("services.") for module_name in sys.modules)
    finally:
        _restore_cached_modules(removed)


def test_contract_validates_context_profile_and_priority() -> None:
    validate_context_profile("tool_augmented")
    validate_priority("critical")

    with pytest.raises(ValueError, match="Invalid context_profile"):
        validate_context_profile("private_magic")

    with pytest.raises(ValueError, match="Invalid priority"):
        validate_priority("urgent")


def test_eval_service_validates_aios_context_profile_vocabulary(tmp_path: Path) -> None:
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

    assert normalized.context_profile == "clean_room"
    assert normalized.final_status == "failed"
    assert normalized.checks == ["pytest"]
    assert normalized.duration_ms == 10
    assert set(CONTEXT_PROFILES) >= {"clean_room", "repo_only"}
    assert "task_success" in HARNESS_DIMENSION_NAMES
    assert "false_completion_caught" in DIMENSION_NAMES


def test_eval_template_validator_accepts_checked_in_templates() -> None:
    template_root = ROOT / "docs" / "evals" / "templates"

    validated = validate_template_directory(template_root)

    assert set(validated) == set(supported_template_ids())


def test_eval_template_validator_rejects_missing_section() -> None:
    with pytest.raises(ValueError, match="missing required sections"):
        validate_eval_template(
            "failure-record",
            "# Eval Failure Record\n\n## Identifiers\n\n- Failure ID:\n",
        )


def test_eval_template_renderer_produces_valid_portable_templates() -> None:
    for template_id in supported_template_ids():
        validate_eval_template(template_id, render_eval_template(template_id))


def test_agent_eval_contract_bundled_samples_validate() -> None:
    validated = validate_all_samples()

    assert "eval_task" in validated
    assert load_sample("eval_run")["context_profile"] == "repo_only"


def test_agent_eval_contract_release_metadata_validates() -> None:
    metadata = load_release_metadata()

    validate_release_metadata(metadata)

    assert metadata["package_name"] == "agent-eval-contract"
    public_surfaces = metadata["public_surfaces"]
    out_of_scope = metadata["out_of_scope"]
    assert isinstance(public_surfaces, list)
    assert isinstance(out_of_scope, list)
    assert "fixture bundle generation" in public_surfaces
    assert "private workflow vocabulary" in out_of_scope


def test_clean_room_contract_runner_does_not_import_aios_services() -> None:
    removed = _pop_cached_modules(("agent_eval_contract", "services"))
    try:
        imported = importlib.import_module("agent_eval_contract")
        result = imported.run_clean_room_contract_check(
            template_root=ROOT / "docs" / "evals" / "templates"
        )

        assert result["ok"] is True
        assert result["template_count"] == 5
        assert result["sample_count"] == 5
        assert "services" not in sys.modules
        assert not any(module_name.startswith("services.") for module_name in sys.modules)
    finally:
        _restore_cached_modules(removed)


def test_fixture_bundle_writer_produces_non_aios_artifacts(tmp_path: Path) -> None:
    result = write_contract_fixture_bundle(tmp_path)
    metadata = result["metadata"]
    assert isinstance(metadata, dict)
    clean_room_check = metadata["clean_room_check"]
    assert isinstance(clean_room_check, dict)

    assert clean_room_check["ok"] is True
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "samples" / "eval_task.json").exists()
    assert (tmp_path / "templates" / "major-task-eval.md").exists()
    assert (tmp_path / "schemas" / "eval_run.schema.json").exists()
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["package"] == (
        "agent-eval-contract"
    )


def test_fixture_runner_cli_works_outside_aios_cwd(tmp_path: Path) -> None:
    output_dir = tmp_path / "bundle"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_eval_contract.fixture_runner",
            "--output-dir",
            str(output_dir),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads(completed.stdout)
    assert manifest["metadata"]["clean_room_check"]["ok"] is True
    assert manifest["metadata"]["clean_room_check"]["sample_count"] == 5
    assert (output_dir / "manifest.json").exists()
