from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.quality_gates import run_gate, validate_commit_quality_gate  # noqa: E402


def _write_registry(path: Path, repo_root: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "knownGates": ["trusted_tests", "architecture", "pre_cr"],
                "projects": [
                    {
                        "projectId": "demo",
                        "roots": [str(repo_root)],
                        "preCommitRequired": True,
                        "gates": {
                            "trusted_tests": {
                                "preCommitCommands": [["python", "--version"]],
                                "fullCommands": [["python", "--version"]],
                            }
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_registered_source_commit_requires_local_contract(tmp_path: Path) -> None:
    registry = tmp_path / "quality-gates.json"
    _write_registry(registry, tmp_path)

    findings = validate_commit_quality_gate(
        tmp_path,
        ["src/app.ts"],
        registry_path=registry,
        run=False,
    )

    assert findings
    assert findings[0].rule == "aios-quality-gate-missing"


def test_contract_rejects_unknown_gate_ids(tmp_path: Path) -> None:
    registry = tmp_path / "quality-gates.json"
    _write_registry(registry, tmp_path)
    (tmp_path / ".aios-quality-gate.json").write_text(
        json.dumps(
            {
                "version": 1,
                "projectId": "demo",
                "preCommitGates": ["trusted_tests", "raw_shell"],
            }
        ),
        encoding="utf-8",
    )

    findings = validate_commit_quality_gate(
        tmp_path,
        ["src/app.ts"],
        registry_path=registry,
        run=False,
    )

    assert {finding.rule for finding in findings} == {"aios-quality-gate-unknown"}


def test_run_gate_executes_registry_argv_not_repo_shell(tmp_path: Path, monkeypatch) -> None:
    registry = tmp_path / "quality-gates.json"
    _write_registry(registry, tmp_path)
    seen: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(command)
        assert "shell" not in kwargs
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_gate(
        project_id="demo",
        gate_id="trusted_tests",
        mode="pre-commit",
        repo_root=tmp_path,
        registry_path=registry,
    )

    assert result["status"] == "pass"
    assert seen == [["python", "--version"]]
