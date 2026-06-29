from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.native_commands import (  # noqa: E402
    de_slopify,
    handoff,
    prototype,
    review_squad,
    security_audit,
    zoom_out,
)


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


def test_de_slopify_flags_risky_structural_changes_without_applying(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "services" / "cleanup_target.py"
    target.write_text(
        "\n".join(
            [
                "def helper(data):  ",
                "    # TODO: remove agent-created branch",
                "    try:",
                "        return data",
                "    except Exception:",
                "        return None",
                "",
            ]
        ),
        encoding="utf-8",
    )
    before = target.read_text(encoding="utf-8")

    report = de_slopify(repo_root=repo, files=[target], cleanup_goals=["remove slop"])

    assert target.read_text(encoding="utf-8") == before
    assert report["proposed_changes"]
    assert {change["kind"] for change in report["skipped_risky_changes"]} >= {
        "broad_error_handling",
        "public_api",
        "todo_or_agent_marker",
    }
    assert report["applied_changes"] == []
    assert report["markdown"].startswith("# De-Slopify Report")


def test_de_slopify_apply_only_changes_low_risk_formatting(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "notes.md"
    target.write_text("alpha   \n\n\n\nbeta\n", encoding="utf-8")

    report = de_slopify(repo_root=repo, files=[target], apply=True)

    assert target.read_text(encoding="utf-8") == "alpha\n\n\nbeta\n"
    assert report["applied_changes"]
    assert report["skipped_risky_changes"] == []


def test_prototype_writes_only_to_allowed_sandbox_locations(tmp_path: Path) -> None:
    repo = _write_repo(tmp_path)
    report = prototype(
        question="Can a disposable parser work?",
        repo_root=repo,
        sandbox_path=Path(".planning/prototypes/parser-spike"),
    )

    created = Path(report["created_files"][0])
    assert created.is_file()
    assert created.read_text(encoding="utf-8").startswith("# Prototype Report")

    disallowed = repo / "services" / "prototype"
    try:
        prototype(question="bad path", repo_root=repo, sandbox_path=disallowed)
    except ValueError as exc:
        assert "Prototype path must be under" in str(exc)
    else:
        raise AssertionError("prototype accepted a production path")


def test_cleanup_and_prototype_cli_json(tmp_path: Path, capsys) -> None:
    repo = _write_repo(tmp_path)
    target = repo / "notes.md"
    target.write_text("alpha   \n", encoding="utf-8")

    assert (
        run_cli(
            [
                "--json",
                "cleanup",
                "de-slopify",
                "--repo-root",
                str(repo),
                "--file",
                str(target),
            ]
        )
        == EXIT_OK
    )
    cleanup_payload = json.loads(capsys.readouterr().out)
    assert cleanup_payload["data"]["markdown"].startswith("# De-Slopify Report")
    assert cleanup_payload["data"]["applied_changes"] == []

    assert (
        run_cli(
            [
                "--json",
                "prototype",
                "--repo-root",
                str(repo),
                "--question",
                "Can sandbox writes stay isolated?",
                "--sandbox-path",
                ".planning/prototypes/cli-spike",
            ]
        )
        == EXIT_OK
    )
    prototype_payload = json.loads(capsys.readouterr().out)
    assert prototype_payload["data"]["markdown"].startswith("# Prototype Report")
    assert Path(prototype_payload["data"]["created_files"][0]).is_file()


def test_native_command_registry_covers_schema_and_safety_contracts() -> None:
    registry = json.loads(
        (ROOT / "config" / "commands" / "native-workflow-commands.json").read_text()
    )
    commands = {command["id"]: command for command in registry["commands"]}

    assert set(commands) == {
        "route",
        "zoom_out",
        "handoff",
        "review_squad",
        "audit_security",
        "cleanup_de_slopify",
        "prototype",
    }
    for command in commands.values():
        assert command["safety_class"] in registry["safety_classes"]
        assert command["input_schema"]["required"]
        assert command["output_schema"]["required"]
        assert command["validation_gates"]
        assert command["logging_metadata"]
    assert commands["cleanup_de_slopify"]["safety_class"] == "guarded_modify"
    assert commands["prototype"]["safety_class"] == "sandbox_write"


def test_native_workflow_command_docs_cover_required_workflows() -> None:
    docs = (ROOT / "docs" / "aios" / "native-workflow-commands.md").read_text()

    for phrase in [
        "aios route",
        "aios zoom-out",
        "aios handoff",
        "aios review squad",
        "aios audit security",
        "aios cleanup de-slopify",
        "aios prototype",
        "Unfamiliar Code",
        "Risky Or Security-Sensitive Work",
        "Uncertain Design Ideas",
        "Second-brain behavior: disabled by default",
        "Metadata logging is local JSONL only",
    ]:
        assert phrase in docs
