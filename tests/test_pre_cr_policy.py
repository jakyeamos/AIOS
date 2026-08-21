from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "bin" / "user-commit-quality-gate.py"
SPEC = importlib.util.spec_from_file_location("user_commit_quality_gate_policy", GATE_PATH)
assert SPEC is not None
gate = importlib.util.module_from_spec(SPEC)
sys.modules["user_commit_quality_gate_policy"] = gate
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


def write_policy(path: Path, common_dir: str, timeout: object) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "preCrTimeoutOverrides": [
                    {"gitCommonDir": common_dir, "timeoutSeconds": timeout}
                ],
            }
        ),
        encoding="utf-8",
    )


def test_git_common_dir_uses_absolute_git_common_directory(tmp_path: Path, monkeypatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"]
        assert kwargs["cwd"] == tmp_path
        return subprocess.CompletedProcess(command, 0, stdout="/repo/.git\n", stderr="")

    monkeypatch.setattr(gate.subprocess, "run", fake_run)

    assert gate.git_common_dir(tmp_path) == Path("/repo/.git")


def test_pre_cr_timeout_defaults_for_unknown_common_directory(tmp_path: Path, monkeypatch) -> None:
    policy_path = tmp_path / "commit-hook-policy.json"
    write_policy(policy_path, "/repo/tmcp/.git", 600)
    monkeypatch.setattr(gate, "git_common_dir", lambda _root: Path("/repo/other/.git"))

    assert gate.pre_cr_timeout_seconds(tmp_path, policy_path=policy_path) == 90


def test_pre_cr_timeout_uses_tmcp_common_directory_for_a_worktree(
    tmp_path: Path, monkeypatch
) -> None:
    policy_path = tmp_path / "commit-hook-policy.json"
    common_dir = "/Users/jakyeamos/projects/tmcp/.git"
    write_policy(policy_path, common_dir, 600)
    monkeypatch.setattr(gate, "git_common_dir", lambda _root: Path(common_dir))

    assert gate.pre_cr_timeout_seconds(tmp_path, policy_path=policy_path) == 600


def test_pre_cr_timeout_rejects_out_of_bounds_or_invalid_matching_values(
    tmp_path: Path, monkeypatch
) -> None:
    policy_path = tmp_path / "commit-hook-policy.json"
    common_dir = "/repo/tmcp/.git"
    monkeypatch.setattr(gate, "git_common_dir", lambda _root: Path(common_dir))

    for timeout in (89, 601, True, "600"):
        write_policy(policy_path, common_dir, timeout)
        assert gate.pre_cr_timeout_seconds(tmp_path, policy_path=policy_path) == 90


def test_scoped_pre_cr_timeout_overrides_repo_config(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".pre-cr.json").write_text(
        json.dumps({"hookTimeoutSeconds": 180}),
        encoding="utf-8",
    )
    policy_path = tmp_path / "commit-hook-policy.json"
    common_dir = "/repo/tmcp/.git"
    write_policy(policy_path, common_dir, 600)
    monkeypatch.setattr(gate, "git_common_dir", lambda _root: Path(common_dir))

    assert gate.pre_cr_timeout_seconds(tmp_path, policy_path=policy_path) == 600
