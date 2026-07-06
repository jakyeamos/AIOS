from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.skills_harvest import (  # noqa: E402
    HarvestOptions,
    harvest_skills_library,
    verify_tmcp_graph,
)


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
    assert "skills.tmcp/graph.json" in result["planned_files"]
    assert "skills.tmcp/shortcuts/candidate.md" in result["planned_files"]
    assert result["summary"]["graph_profile"]["profile_id"]
    assert result["summary"]["graph_diff"]["schema"] == "tmcp-graph-diff-v0.1"
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
    assert (out / "skills.tmcp" / "graph.json").exists()
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
    assert "## Shortcut Statuses" in shortcut
    assert "stale_candidate" in shortcut
    assert "## Rebuild Outcomes" in shortcut
    assert "source graph version" in shortcut
    assert "fall back to router traversal" in shortcut
    graph = json.loads((out / "skills.tmcp" / "graph.json").read_text(encoding="utf-8"))
    atom_registry = json.loads((ROOT / "config" / "tmcp" / "behavior-atoms.json").read_text())
    assert graph["schema"] == "tmcp-graph-v0.1"
    assert atom_registry["schema"] == "tmcp-behavior-atoms-v0.1"
    assert graph["tasks"]
    assert graph["modules"]
    assert graph["source_skills"]
    implementation = graph["tasks"]["implementation"]
    assert "behavior_atoms" in implementation
    assert set(atom_registry["node_mappings"]["implementation"]) <= set(
        implementation["behavior_atoms"]
    )
    assert "token_cost" in implementation
    test_gate = graph["modules"]["test_gate"]
    assert "verification_gate" in test_gate["behavior_atoms"]
    source_skill = next(iter(graph["source_skills"].values()))
    assert source_skill["adds_behavior"]
    assert source_skill["risk_if_omitted"] in {"low", "medium", "high"}
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


def test_harvest_reports_stale_sources_against_existing_lock(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _seed_project(project)
    out = tmp_path / "skills-library"
    harvest_skills_library(HarvestOptions(roots=(project,), out=out))

    skill = project / ".agents" / "skills" / "review" / "SKILL.md"
    skill.write_text(
        "# Review Skill\n\nWhen to use: code review. Ask before editing. Run focused tests.\n",
        encoding="utf-8",
    )

    result = harvest_skills_library(HarvestOptions(roots=(project,), out=out, dry_run=True))

    assert result["summary"]["graph_diff"]["changed_source_count"] >= 1


def test_harvest_blocks_large_skill_count_drop(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _seed_project(project)
    out = tmp_path / "skills-library"
    out.mkdir()
    (out / "manifest.json").write_text(json.dumps({"skill_count": 10}), encoding="utf-8")

    try:
        harvest_skills_library(HarvestOptions(roots=(project,), out=out, dry_run=True))
    except ValueError as exc:
        assert "skill count dropped" in str(exc)
    else:
        raise AssertionError("expected large drop guard to fail")


def test_graph_verify_repairs_missing_graph_json_for_existing_library(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _seed_project(project)
    out = tmp_path / "skills-library"
    harvest_skills_library(HarvestOptions(roots=(project,), out=out))
    (out / "skills.tmcp" / "graph.json").unlink()

    before = verify_tmcp_graph(out)
    repaired = verify_tmcp_graph(out, repair=True)

    assert before["status"] == "fail"
    assert before["summary"]["skill_count"] == 1
    assert repaired["status"] == "pass"
    assert repaired["repaired"] is True
    assert (out / "skills.tmcp" / "graph.json").exists()
    graph = json.loads((out / "skills.tmcp" / "graph.json").read_text(encoding="utf-8"))
    assert len(graph["source_skills"]) == 1
    assert next(iter(graph["source_skills"].values()))["behavior_atoms"]
