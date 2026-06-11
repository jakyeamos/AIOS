from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.skills_harvest import HarvestOptions, harvest_skills_library  # noqa: E402


def _seed_project(root: Path) -> None:
    skill_dir = root / ".agents" / "skills" / "review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "# Review Skill\n\nWhen to use: code review. Ask before editing. Run tests.\n",
        encoding="utf-8",
    )
    workflow_dir = root / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "fix.md").write_text(
        "# Fix Workflow\n\nImplement directly when the user asks. Validate output.\n",
        encoding="utf-8",
    )
    (root / "AGENTS.md").write_text(
        "# AGENTS\n\nAlways use pnpm. token = ghp_123456789012345678901234567890123456\n",
        encoding="utf-8",
    )


def test_harvest_dry_run_plans_tmcp_without_writing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _seed_project(project)
    out = tmp_path / "skills-library"

    result = harvest_skills_library(
        HarvestOptions(roots=(project,), out=out, dry_run=True, tmcp=True)
    )

    assert result["summary"]["candidate_count"] == 3
    assert result["summary"]["skill_count"] == 1
    assert result["summary"]["redacted_file_count"] == 1
    assert result["summary"]["conflict_count"] == 1
    assert result["validation"]["status"] == "pass"
    assert "skills.tmcp/router.md" in result["planned_files"]
    assert "skills.tmcp/design-decision.md" in result["planned_files"]
    assert "skills.tmcp/traversal-receipt-schema.md" in result["planned_files"]
    assert "skills.tmcp/evaluation-plan.md" in result["planned_files"]
    assert "skills.tmcp/shortcuts/candidate.md" in result["planned_files"]
    assert not out.exists()


def test_harvest_generates_library_and_commits(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _seed_project(project)
    out = tmp_path / "skills-library"

    result = harvest_skills_library(HarvestOptions(roots=(project,), out=out))

    assert result["validation"]["status"] == "pass"
    assert result["git"]["committed"] is True
    assert (out / "skills.tmcp" / "router.md").exists()
    assert (out / "skills.tmcp" / "design-decision.md").exists()
    assert (out / "skills.tmcp" / "traversal-receipt-schema.md").exists()
    assert (out / "skills.tmcp" / "evaluation-plan.md").exists()
    assert (out / "skills.tmcp" / "shortcuts" / "candidate.md").exists()
    assert (out / "skills.tmcp" / "tests" / "shortcut_promotion_cases.md").exists()
    assert (out / "audit" / "discovery-report.md").exists()
    assert (out / "skills.tmcp" / "branches" / "approval_before_edit.branch.md").exists()
    router = (out / "skills.tmcp" / "router.md").read_text(encoding="utf-8")
    assert "thin decision graph" in router
    assert "@shortcut:candidate" in router
    implementation_task = (out / "skills.tmcp" / "tasks" / "implementation.md").read_text(
        encoding="utf-8"
    )
    assert "## Transition Edges" in implementation_task
    assert "## Custom Skill Construction" in implementation_task
    evaluation_plan = (out / "skills.tmcp" / "evaluation-plan.md").read_text(encoding="utf-8")
    assert "token_roi" in evaluation_plan
    assert "tmcp_promoted_shortcut" in evaluation_plan
    shortcut = (out / "skills.tmcp" / "shortcuts" / "candidate.md").read_text(encoding="utf-8")
    assert "## Promotion Threshold" in shortcut
    assert "top-level TMCP node" in shortcut
    generated_agents = next((out / "instructions" / "global").glob("*.md"))
    text = generated_agents.read_text(encoding="utf-8")
    assert "ghp_123456789012345678901234567890123456" not in text
    assert "[REDACTED:api_key_assignment]" in text
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=out,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.strip()
    assert branch == "main"


def test_skills_harvest_cli_outputs_json(tmp_path: Path, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _seed_project(project)
    out = tmp_path / "skills-library"

    exit_code = run_cli(
        [
            "--json",
            "skills",
            "harvest",
            "--roots",
            str(project),
            "--out",
            str(out),
            "--dry-run",
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "skills-harvest"
    assert payload["data"]["validation"]["status"] == "pass"
    assert payload["data"]["summary"]["dry_run"] is True
