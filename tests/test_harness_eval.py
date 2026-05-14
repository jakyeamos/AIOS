from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import harness_eval  # noqa: E402

CONFIG = ROOT / "docs" / "aios" / "harness-eval" / "config.json"
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
