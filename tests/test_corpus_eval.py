from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios-corpus-eval.cjs"
AIOS = ROOT / "bin" / "aios.py"


def _json_from_stdout(stdout: str) -> dict:
    start = stdout.find("{")
    assert start >= 0, stdout
    return json.loads(stdout[start:])


def test_corpus_harness_self_test() -> None:
    completed = subprocess.run(
        ["node", str(SCRIPT), "--self-test"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "self-test passed" in completed.stdout


def test_prompt_suite_dry_run_filters_to_applicable_commands() -> None:
    completed = subprocess.run(
        ["node", str(SCRIPT), "--dry-run", "--sample", "--suite", "prompt-library"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = _json_from_stdout(completed.stdout)
    assert payload["plannedCount"] == 2
    assert {plan["mode"] for plan in payload["plans"]} == {"migrated", "scratch-real"}
    assert all(plan["suite"] == "prompt-library" for plan in payload["plans"])


def test_aios_corpus_wrapper_passes_through_flags() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(AIOS),
            "corpus",
            "run",
            "--dry-run",
            "--sample",
            "--suite",
            "prompt-library",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = _json_from_stdout(completed.stdout)
    assert payload["selection"]["suite"] == "prompt-library"
    assert payload["plannedCount"] == 2
