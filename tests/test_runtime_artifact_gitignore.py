from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ARTIFACT_PATHS = (
    "logs/control-plane/invocations/live-invocation.json",
    "logs/control-plane/tmcp-packets/live-packet.json",
    "logs/control-plane/workflow-reports/live-report.json",
    "logs/session-effectiveness/live-session.json",
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_runtime_control_plane_artifacts_are_ignored() -> None:
    for path in RUNTIME_ARTIFACT_PATHS:
        result = _git("check-ignore", "--quiet", path)

        assert result.returncode == 0, result.stderr


def test_runtime_control_plane_artifacts_are_not_tracked() -> None:
    result = _git("ls-files", "logs/control-plane", "logs/session-effectiveness")

    assert result.returncode == 0
    assert result.stdout == ""
