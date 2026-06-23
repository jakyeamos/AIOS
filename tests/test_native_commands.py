from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.native_commands import handoff, review_squad, security_audit, zoom_out  # noqa: E402


def _write_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    services = repo / "services"
    tests = repo / "tests"
    services.mkdir(parents=True)
    tests.mkdir()
    (services / "__init__.py").write_text("", encoding="utf-8")
    (services / "example.py").write_text(
        "\n".join(
            [
                '"""Example service for native command tests."""',
                "import json",
                "from pathlib import Path",
                "",
                "def load_value(path: Path) -> dict[str, object]:",
                "    try:",
                "        return json.loads(path.read_text())",
                "    except Exception:",
                "        return {}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tests / "test_example.py").write_text(
        "from services.example import load_value\n", encoding="utf-8"
    )
    return repo


def test_zoom_out_reports_required_sections_and_is_read_only(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "services" / "example.py"
    before = target.read_text(encoding="utf-8")

    report = zoom_out(target, repo_root=repo)

    assert target.read_text(encoding="utf-8") == before
    for key in [
        "target",
        "purpose",
        "system_position",
        "inbound_dependencies",
        "outbound_dependencies",
        "sibling_modules",
        "conventions",
        "domain_vocabulary",
        "risks",
        "next_context",
    ]:
        assert report[key]
    assert report["markdown"].startswith("# Zoom-Out Report")


def test_handoff_preview_is_read_only_and_contains_required_sections(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    before_paths = sorted(path.relative_to(repo) for path in repo.rglob("*"))

    report = handoff(
        objective="Continue native commands",
        repo_root=repo,
        decision=["Keep agent files thin."],
        test=["uv run pytest tests/test_native_commands.py"],
        next_action=["Implement audit security next."],
    )

    after_paths = sorted(path.relative_to(repo) for path in repo.rglob("*"))
    assert after_paths == before_paths
    for section in [
        "## Goal",
        "## Current State",
        "## Branch / Workspace Status",
        "## Files Touched",
        "## Decisions",
        "## Tests Run",
        "## What Worked",
        "## Failed / Dead Ends",
        "## Blockers",
        "## Relevant References",
        "## Next Recommended Actions",
    ]:
        assert section in report["markdown"]
    assert report["artifact_path"] is None


def test_handoff_writes_only_to_allowed_artifact_location(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    output = repo / "docs" / "handoffs" / "native.md"

    report = handoff(objective="Write handoff", repo_root=repo, output_path=output)

    assert report["artifact_path"] == str(output)
    assert output.read_text(encoding="utf-8").startswith("# AIOS Handoff")


def test_review_squad_runs_all_lanes_and_is_read_only(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "services" / "example.py"
    before = target.read_text(encoding="utf-8")

    report = review_squad(repo_root=repo, files=[target])

    assert target.read_text(encoding="utf-8") == before
    assert set(report["lanes"]) == {
        "security",
        "correctness",
        "testing",
        "architecture",
        "maintainability",
        "project_alignment",
    }
    assert "## Reviewer Lanes" in report["markdown"]
    assert report["findings_by_severity"]["medium"]


def test_native_commands_are_available_from_cli_json(tmp_path: Path, capsys) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "services" / "example.py"

    assert (
        run_cli(["--json", "zoom-out", str(target), "--repo-root", str(repo), "--depth", "1"])
        == EXIT_OK
    )
    zoom_payload = json.loads(capsys.readouterr().out)
    assert zoom_payload["data"]["markdown"].startswith("# Zoom-Out Report")

    assert (
        run_cli(
            [
                "--json",
                "review",
                "squad",
                "--repo-root",
                str(repo),
                "--file",
                str(target),
            ]
        )
        == EXIT_OK
    )
    review_payload = json.loads(capsys.readouterr().out)
    assert set(review_payload["data"]["lanes"]) == {
        "security",
        "correctness",
        "testing",
        "architecture",
        "maintainability",
        "project_alignment",
    }


def test_security_audit_strict_reports_only_critical_and_high(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "services" / "security.py"
    target.write_text(
        "\n".join(
            [
                'API_KEY = "abc123"',
                "import subprocess",
                "def run(user_arg: str) -> None:",
                "    subprocess.run('rm -rf ' + user_arg, shell=True)",
                "    token = user_arg",
                "    email = 'person@example.com'",
            ]
        ),
        encoding="utf-8",
    )

    report = security_audit(mode="strict", repo_root=repo, files=[target])

    severities = {finding["severity"] for finding in report["findings"]}
    assert severities == {"critical", "high"}
    for finding in report["findings"]:
        assert finding["affected_file"] == "services/security.py"
        assert finding["issue"]
        assert finding["why_it_matters"]
        assert finding["exploit_or_failure_scenario"]
        assert finding["recommended_fix"]
        assert finding["confidence"]


def test_security_audit_practical_includes_contextual_medium_findings(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "services" / "privacy.py"
    target.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "def save_profile(email: str, token: str, path: Path) -> None:",
                "    path.write_text(email + token)",
            ]
        ),
        encoding="utf-8",
    )

    report = security_audit(mode="practical", repo_root=repo, files=[target])

    assert {finding["severity"] for finding in report["findings"]} == {"medium"}
    assert report["non_issues_checked"]
    assert report["verification_suggestions"]
    assert "generic" not in report["markdown"].lower()


def test_audit_security_cli_json(tmp_path: Path, capsys) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "services" / "security.py"
    target.write_text('SECRET = "abc123"\n', encoding="utf-8")

    assert (
        run_cli(
            [
                "--json",
                "audit",
                "security",
                "--mode",
                "strict",
                "--repo-root",
                str(repo),
                "--file",
                str(target),
            ]
        )
        == EXIT_OK
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["markdown"].startswith("# Security Audit")
    assert payload["data"]["findings_by_severity"]["high"]
