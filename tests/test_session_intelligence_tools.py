from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.session_intelligence_tools import (  # noqa: E402
    codex_workflow_skill_payload,
    planning_state_payload,
    quality_ladder_payload,
    repo_closeout_payload,
    repo_inspect_payload,
    service_probe_payload,
    ship_guard_payload,
)


def _dict(payload: dict[str, object], key: str) -> dict[str, object]:
    return cast(dict[str, object], payload[key])


def _list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], payload[key])


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.PIPE, text=True)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "aios@example.local")
    _git(repo, "config", "user.name", "AIOS Tests")
    (repo / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
    (repo / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "lint": "eslint .",
                    "test": "vitest run",
                    "typecheck": "tsc --noEmit",
                },
                "packageManager": "pnpm@10.0.0",
            }
        ),
        encoding="utf-8",
    )
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    (repo / ".planning").mkdir()
    (repo / ".planning" / "STATE.md").write_text("## Next\nShip safely.\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")
    (repo / "src.py").write_text("print('dirty')\n", encoding="utf-8")
    return repo


def test_repo_inspect_reports_git_package_and_context_summary(sample_repo: Path) -> None:
    payload = repo_inspect_payload(sample_repo, include_processes=False)
    repo = _dict(payload, "repo")
    git = _dict(payload, "git")
    package = _dict(payload, "package")
    files = _dict(payload, "files")
    recommendations = _list(payload, "recommendations")

    assert payload["schema"] == "aios-repo-inspect-v0.1"
    assert repo["root"] == str(sample_repo)
    assert git["is_repo"] is True
    assert git["dirty"] is True
    assert package["manager"] == "pnpm"
    assert "pyproject.toml" in cast(list[str], files["root_markers"])
    assert recommendations[0]["tool"] == "aios quality ladder"


def test_repo_closeout_reports_deterministic_git_state(sample_repo: Path) -> None:
    (sample_repo / "README.md").write_text("# Sample\n\nChanged.\n", encoding="utf-8")
    (sample_repo / "new.txt").write_text("new\n", encoding="utf-8")

    payload = repo_closeout_payload(sample_repo)
    git = _dict(payload, "git")
    diff_stat = _dict(payload, "diff_stat")

    assert payload["schema"] == "aios-repo-closeout-v0.1"
    assert payload["repo"] == str(sample_repo)
    assert git["branch"] in {"master", "main"}
    assert isinstance(git["head"], str)
    assert len(cast(str, git["head"])) == 40
    assert git["dirty"] is True
    assert git["dirty_files"] == [" M README.md", "?? new.txt", "?? src.py"]
    assert cast(list[str], diff_stat["lines"])[-1].strip().endswith("insertions(+)")
    assert cast(list[dict[str, object]], git["recent_commits"])[0]["title"] == "initial"


def test_quality_ladder_plans_python_and_js_commands_without_running(sample_repo: Path) -> None:
    payload = quality_ladder_payload(sample_repo, profile="auto")

    commands = [step["command"] for step in _list(payload, "steps")]
    execution = _dict(payload, "execution")
    assert payload["schema"] == "aios-quality-ladder-plan-v0.1"
    assert "uv run ruff check ." in commands
    assert "uv run basedpyright" in commands
    assert "pnpm lint" in commands
    assert execution["mode"] == "plan_only"


def test_ship_guard_is_review_gated_and_blocks_dirty_push(sample_repo: Path) -> None:
    payload = ship_guard_payload(sample_repo)
    review_gate = _dict(payload, "review_gate")
    decision = _dict(payload, "decision")

    assert payload["schema"] == "aios-ship-guard-v0.1"
    assert review_gate["requires_explicit_action"] is True
    assert decision["ready"] is False
    assert "working tree has uncommitted changes" in cast(list[str], decision["blockers"])


def test_service_probe_builds_local_process_diagnostics() -> None:
    payload = service_probe_payload(ports=[65535], names=["unlikely-aios-test-process"])
    probes = _list(payload, "probes")

    assert payload["schema"] == "aios-service-probe-v0.1"
    assert probes[0]["kind"] == "tcp_port"
    assert probes[0]["port"] == 65535
    assert probes[0]["listening"] is False
    assert probes[1]["kind"] == "process_name"


def test_workflow_skill_payload_is_review_gated_skill_candidate() -> None:
    payload = codex_workflow_skill_payload()
    promotion = _dict(payload, "promotion")
    skill = _dict(payload, "skill")
    steps = cast(list[dict[str, object]], skill["steps"])

    assert payload["schema"] == "aios-codex-workflow-skill-v0.1"
    assert promotion["review_gated"] is True
    assert skill["name"] == "codex-tier-one-delivery"
    assert steps[0]["name"] == "orient"


def test_planning_state_reads_state_and_planning_markers(sample_repo: Path) -> None:
    payload = planning_state_payload(sample_repo)
    state = _dict(payload, "state")
    planning = _dict(payload, "planning")
    decision = _dict(payload, "decision")

    assert payload["schema"] == "aios-planning-state-v0.1"
    assert state["exists"] is True
    assert planning["exists"] is True
    assert decision["ready_for_agent_work"] is True


def test_session_intelligence_tool_cli_json(
    sample_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = run_cli(["--json", "repo", "inspect", "--repo", str(sample_repo)])

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["data"]["schema"] == "aios-repo-inspect-v0.1"


def test_repo_closeout_cli_prints_stable_human_report(
    sample_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (sample_repo / "README.md").write_text("# Sample\n\nChanged.\n", encoding="utf-8")

    exit_code = run_cli(["repo", "closeout", "--repo", str(sample_repo), "--commits", "1"])

    assert exit_code == EXIT_OK
    output = capsys.readouterr().out.splitlines()
    assert output[0] == "AIOS Repo Closeout"
    assert output[1] == f"repo: {sample_repo}"
    assert output[2] in {"branch: master", "branch: main"}
    assert output[3].startswith("head: ")
    assert output[4] == "dirty: true"
    assert output[5:] == [
        "dirty_files:",
        " M README.md",
        "?? src.py",
        "diff_stat:",
        "README.md | 2 ++",
        "1 file changed, 2 insertions(+)",
        "recent_commits:",
        "initial",
    ]


def test_quality_ladder_cli_json(sample_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_cli(["--json", "quality", "ladder", "--repo", str(sample_repo)])

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["execution"]["mode"] == "plan_only"


def test_ship_guard_cli_json(sample_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_cli(["--json", "ship", "guard", "--repo", str(sample_repo)])

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["review_gate"]["requires_explicit_action"] is True


def test_service_probe_cli_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_cli(["--json", "service", "probe", "--port", "65535"])

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["probes"][0]["kind"] == "tcp_port"


def test_workflow_skill_cli_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_cli(["--json", "workflow-skill", "codex"])

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["promotion"]["review_gated"] is True


def test_planning_state_cli_json(sample_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_cli(["--json", "planning", "state", "--repo", str(sample_repo)])

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["schema"] == "aios-planning-state-v0.1"
