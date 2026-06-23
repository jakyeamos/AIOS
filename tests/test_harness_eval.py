from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import harness_eval  # noqa: E402

CONFIG = ROOT / "docs" / "aios" / "harness-eval" / "config.json"
DX_FIXTURES = ROOT / "config" / "agent-eval" / "developer-experience-fixtures.json"
AIOS = ROOT / "bin" / "aios.py"


def _json_from_stdout(stdout: str) -> dict:
    start = stdout.find("{")
    assert start >= 0, stdout
    return json.loads(stdout[start:])


def test_load_harness_eval_config_lists_initial_categories() -> None:
    config = harness_eval.load_harness_eval_config(CONFIG)

    assert config.eval_name == "aios_harness_eval_v0"
    assert {fixture.category for fixture in config.fixtures} == {
        "approval-gates",
        "context-routing",
        "false-completion",
        "recovery",
        "writebacks",
    }


def test_load_harness_fixture_reads_expected_artifacts() -> None:
    config = harness_eval.load_harness_eval_config(CONFIG)
    fixture = harness_eval.load_harness_fixture(config.fixtures[0].path)

    assert fixture.task_markdown.startswith("#")
    assert fixture.expected_context_packets
    assert fixture.expected_gates
    assert fixture.expected_success_criteria
    assert fixture.runs["aios_shadow"]["harness"]["name"] == "AIOS"


def test_context_precision_recall_and_gate_accuracy_distinguish_harnesses() -> None:
    fixture = harness_eval.load_harness_fixture(
        ROOT / "tests" / "fixtures" / "harness-eval" / "context-routing"
    )

    aios_score = harness_eval.score_harness_run(fixture, fixture.runs["aios_shadow"])
    baseline_score = harness_eval.score_harness_run(fixture, fixture.runs["baseline_minimal"])

    assert aios_score.dimensions["context_precision"] == 1.0
    assert aios_score.dimensions["context_recall"] == 1.0
    assert baseline_score.dimensions["context_precision"] < 1.0
    assert baseline_score.dimensions["context_recall"] < 1.0
    assert "context_recall" in baseline_score.failed_dimensions


def test_false_completion_is_caught_when_tests_fail() -> None:
    fixture = harness_eval.load_harness_fixture(
        ROOT / "tests" / "fixtures" / "harness-eval" / "false-completion"
    )

    aios_score = harness_eval.score_harness_run(fixture, fixture.runs["aios_shadow"])
    baseline_score = harness_eval.score_harness_run(fixture, fixture.runs["baseline_minimal"])

    assert aios_score.dimensions["false_completion_caught"] is True
    assert baseline_score.dimensions["false_completion_caught"] is False
    assert "false_completion_caught" in baseline_score.failed_dimensions


def test_suite_scores_all_fixture_runs() -> None:
    result = harness_eval.score_suite(CONFIG)

    assert result.totals["fixture_count"] == 5
    assert result.totals["run_count"] == 10
    assert result.totals["failed_run_count"] >= 1
    assert result.results[0].evidence_path.endswith(".json")


def test_load_developer_experience_fixture_registry_covers_required_scenarios() -> None:
    config = harness_eval.load_developer_experience_fixtures(DX_FIXTURES)

    assert config.eval_name == "developer_experience_pack_eval_v0"
    assert config.category == "developer-experience"
    assert config.spec_path == ROOT / "docs" / "evals" / "developer-experience-pack-eval.md"
    assert {fixture.id for fixture in config.fixtures} == {
        "poor_onboarding_repo",
        "public_cli_change",
        "typescript_package_boundary_change",
    }
    assert "record_before_after_metrics_or_mark_not_measured" in config.criteria
    assert all(
        {"available", "unavailable"} <= set(fixture.second_brain_modes)
        for fixture in config.fixtures
    )


def test_developer_experience_fixtures_encode_capability_discipline() -> None:
    config = harness_eval.load_developer_experience_fixtures(DX_FIXTURES)
    fixtures = {fixture.id: fixture for fixture in config.fixtures}

    poor_onboarding = fixtures["poor_onboarding_repo"]
    assert poor_onboarding.expected_capabilities == ["dx_optimizer", "docs_writer"]
    assert "typescript_specialist" in poor_onboarding.forbidden_capabilities
    assert "improve_readme_clarity_without_marketing_fluff" in poor_onboarding.criteria

    public_cli = fixtures["public_cli_change"]
    assert public_cli.expected_capabilities == ["interface_dx_reviewer", "docs_writer"]
    assert "typescript_specialist" in public_cli.forbidden_capabilities
    assert (
        "invoke_security_review_only_for_contextual_shell_network_filesystem_risk"
        in public_cli.criteria
    )

    typescript_boundary = fixtures["typescript_package_boundary_change"]
    assert typescript_boundary.expected_capabilities == [
        "typescript_specialist",
        "spec_fidelity_coder",
    ]
    assert (
        "invoke_typescript_specialist_only_when_api_or_type_surface_justifies_it"
        in typescript_boundary.criteria
    )


def test_developer_experience_fixture_summary_is_machine_readable() -> None:
    summary = harness_eval.developer_experience_fixture_summary(DX_FIXTURES)

    assert summary["category"] == "developer-experience"
    assert summary["fixture_count"] == 3
    assert summary["criteria_count"] >= 12
    assert summary["required_scenarios_present"] is True


def test_harness_eval_cli_emits_json_envelope() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(AIOS),
            "--json",
            "harness-eval",
            "run",
            "--config",
            str(CONFIG),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = _json_from_stdout(completed.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "harness-eval-run"
    assert payload["data"]["totals"]["fixture_count"] == 5
    assert payload["data"]["totals"]["run_count"] == 10
