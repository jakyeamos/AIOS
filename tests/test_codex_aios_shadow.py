from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class _Completed:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def _load_module():
    module_path = ROOT / "scripts" / "codex-aios-shadow.py"
    spec = importlib.util.spec_from_file_location("codex_aios_shadow", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_gate_adoption_artifacts(
    root: Path,
    run_id: str,
    *,
    test_status: str = "present",
    rollout_phase_ids: list[str] | None = None,
    tmcp_status: str = "insufficient_source",
) -> Path:
    output_dir = root / "AIOS-backfill" / "gate-adoption" / run_id
    phase_ids = rollout_phase_ids or ["phase-0-rubric-audit-pack"]
    _write_json(output_dir / "repo-scan.json", {"schema": "scan", "run_id": run_id})
    _write_json(
        output_dir / "gate-matrix.json",
        {
            "schema": "matrix",
            "run_id": run_id,
            "summary": {"present": 1, "partial": 0, "absent": 1},
            "gates": [
                {
                    "id": "tests",
                    "status": test_status,
                    "enforcement": "hard",
                    "maturity": "enforceable" if test_status == "present" else "baseline_first",
                },
                {
                    "id": "ci",
                    "status": "absent",
                    "enforcement": "not_enforced",
                    "maturity": "baseline_first",
                },
            ],
        },
    )
    (output_dir / "gate-matrix.md").write_text("# Gate Matrix\n", encoding="utf-8")
    _write_json(
        output_dir / "tmcp-expert-enrichment.json",
        {"schema": "tmcp", "status": tmcp_status},
    )
    _write_json(
        output_dir / "rubric-pack.json",
        {
            "schema": "rubrics",
            "run_id": run_id,
            "broad_rubrics": [{"id": "truth_docs_accuracy"}],
            "gate_specific_rubrics": [{"id": "gate_tests"}, {"id": "gate_ci"}],
            "tmcp_expert_enrichment": {"status": tmcp_status},
        },
    )
    _write_json(
        output_dir / "rubric-detail-manifest.json",
        {"schema": "manifest", "document_count": 2},
    )
    for rubric_id in ("gate-tests", "gate-ci"):
        (output_dir / "rubrics" / f"{rubric_id}.audit.md").parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        (output_dir / "rubrics" / f"{rubric_id}.audit.md").write_text(
            "# Audit\n",
            encoding="utf-8",
        )
    _write_json(
        output_dir / "rollout-plan.json",
        {
            "schema": "rollout",
            "run_id": run_id,
            "phases": [
                {"id": phase_id, "title": phase_id.replace("-", " ")} for phase_id in phase_ids
            ],
        },
    )
    (output_dir / "rollout-plan.md").write_text("# Rollout\n", encoding="utf-8")
    return output_dir


def test_make_task_id_is_bounded_and_stable_shape() -> None:
    module = _load_module()

    task_id = module.make_task_id("Fix the route selector and verify the operator UI")

    assert task_id.startswith("codex-shadow-")
    assert "fix-the-route-selector" in task_id
    assert len(task_id) < 90


def test_shadow_prompt_points_to_headless_shadow_execution() -> None:
    module = _load_module()

    prompt = module.shadow_prompt(
        "Fix login",
        {"worktree_path": "/tmp/repo/.aios/shadow-worktrees/aios-eval-fix-login-full-aios"},
    )

    assert prompt is not None
    assert "Headless Codex shadow execution prompt prepared" in prompt
    assert "Fix login" in prompt


def test_make_branch_name_uses_codex_namespace() -> None:
    module = _load_module()

    branch = module.make_branch_name("codex-shadow-260624-fix-login")

    assert branch == "codex/aios-shadow-codex-shadow-260624-fix-login"
    assert branch.count("/") == 1


def test_baseline_instruction_separates_shadow_from_governed_route() -> None:
    module = _load_module()

    automatic = module.baseline_instruction(False)
    governed = module.baseline_instruction(True)

    assert "normally" in automatic
    assert "evidence only" in automatic
    assert "governing context" in governed


def test_route_rule_separates_shadow_from_governed_route() -> None:
    module = _load_module()

    automatic = module.route_rule(False)
    governed = module.route_rule(True)

    assert "do not govern" in automatic
    assert "govern" in governed


def test_route_failure_payload_marks_automatic_shadow_non_blocking() -> None:
    module = _load_module()

    payload = module.route_failure_payload(
        objective="Do a task with no workflow",
        project={"id": "project-aios", "name": "AIOS", "repo_path": "/repo"},
        route_result={
            "returncode": 2,
            "json": {
                "error": {
                    "code": "route-blocked",
                    "message": "No governed workflow matched the objective strongly enough.",
                }
            },
        },
        governed_route=False,
        diagnostics_path=Path("/repo/data/aios-route-failures.jsonl"),
    )

    assert payload["ok"] is True
    assert payload["aios_route"]["status"] == "route_failed"
    assert payload["aios_route"]["blocking"] is False
    assert payload["baseline"]["approval_required"] is False
    assert payload["baseline"]["can_continue_without_shadow"] is True
    assert payload["baseline"]["instruction"].startswith("Continue the baseline task normally")
    assert "does not require user approval" in payload["compare_policy"]["shadow_rule"]
    assert payload["diagnostics"]["path"] == "/repo/data/aios-route-failures.jsonl"


def test_record_route_failure_appends_parseable_jsonl(tmp_path: Path) -> None:
    module = _load_module()
    path = tmp_path / "route-failures.jsonl"

    module.record_route_failure(
        path,
        objective="Do a task with no workflow",
        project={"id": "project-aios", "name": "AIOS", "repo_path": "/repo"},
        route_result={
            "returncode": 2,
            "json": {
                "error": {
                    "code": "route-blocked",
                    "message": "No governed workflow matched the objective strongly enough.",
                }
            },
        },
        governed_route=False,
    )

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["code"] == "route-blocked"
    assert rows[0]["mode"] == "automatic-shadow"
    assert rows[0]["blocking"] is False
    assert rows[0]["objective"] == "Do a task with no workflow"


def test_create_shadow_lane_marks_clean_initial_worktree(tmp_path: Path) -> None:
    module = _load_module()
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    repo = tmp_path / "AIOS"
    repo.mkdir()

    with patch("services.shadow_branch_runner.subprocess.run") as run:
        run.side_effect = [_Completed(str(repo)), _Completed(""), _Completed("")]
        shadow = module.create_shadow_lane(
            db_path=db_path,
            repo_path=repo,
            task_id="codex-shadow-test",
            start_sha="abc123",
            condition="full-aios",
        )

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT contamination_check_passed, parity_checklist_status FROM shadow_branch_runs WHERE id = ?",
        (shadow["shadow_run_id"],),
    ).fetchone()
    conn.close()

    assert shadow["contamination_check_passed"] is True
    assert row == (1, "no_evidence")


def test_shadow_evidence_report_marks_gate_artifact_delta_actionable(tmp_path: Path) -> None:
    module = _load_module()
    baseline_repo = tmp_path / "repo"
    shadow_repo = tmp_path / "shadow"
    run_id = "gate-run-1"
    baseline_repo.mkdir()
    shadow_repo.mkdir()
    _write_gate_adoption_artifacts(
        baseline_repo,
        run_id,
        test_status="present",
        rollout_phase_ids=["phase-0-rubric-audit-pack"],
        tmcp_status="insufficient_source",
    )
    _write_gate_adoption_artifacts(
        shadow_repo,
        run_id,
        test_status="partial",
        rollout_phase_ids=["phase-0-rubric-audit-pack", "phase-1-ci-proof"],
        tmcp_status="sufficient",
    )

    report = module.build_shadow_evidence_report(
        repo_path=baseline_repo,
        run_id=run_id,
        workflow_key="repo_gate_adoption_v1",
        baseline_dirty=True,
        shadow={"worktree_path": str(shadow_repo), "contamination_check_passed": False},
        inspect_commands={
            "shadow_parity": "shadow parity command",
            "operator_search": "operator search command",
            "daily_flow": "daily flow command",
        },
    )

    assert report["quality_signal"] == "actionable_comparison"
    assert "comparable artifact deltas" in report["headline"]
    assert report["artifact_inventory"]["baseline"]["present_count"] == len(
        module.GATE_ADOPTION_ARTIFACTS
    )
    assert report["artifact_inventory"]["shadow"]["rubric_doc_count"] == 2
    assert report["comparison"]["gate_matrix"]["status_changes"] == [
        {"gate_id": "tests", "baseline": "present", "shadow": "partial"}
    ]
    assert report["comparison"]["rollout_plan"]["added_phase_ids"] == ["phase-1-ci-proof"]
    assert (
        report["comparison"]["rubric_pack"]["baseline_tmcp_expert_status"] == "insufficient_source"
    )
    assert report["comparison"]["rubric_pack"]["shadow_tmcp_expert_status"] == "sufficient"
    assert {finding["title"] for finding in report["findings"]} >= {
        "Baseline workspace was dirty",
        "Contamination check did not pass",
    }
    assert [inspection["name"] for inspection in report["next_inspections"]][:2] == [
        "shadow parity",
        "gate-adoption artifacts",
    ]


def test_shadow_evidence_report_marks_shadow_artifacts_without_baseline_actionable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    baseline_repo = tmp_path / "repo"
    shadow_repo = tmp_path / "shadow"
    run_id = "gate-run-2"
    baseline_repo.mkdir()
    shadow_repo.mkdir()
    _write_gate_adoption_artifacts(shadow_repo, run_id)

    report = module.build_shadow_evidence_report(
        repo_path=baseline_repo,
        run_id=run_id,
        workflow_key="repo_gate_adoption_v1",
        baseline_dirty=False,
        shadow={"worktree_path": str(shadow_repo), "contamination_check_passed": True},
        inspect_commands={
            "shadow_parity": "shadow parity command",
            "operator_search": "operator search command",
            "daily_flow": "daily flow command",
        },
    )

    assert report["quality_signal"] == "actionable_shadow_artifacts"
    assert "no baseline artifact set" in report["headline"]
    assert report["artifact_inventory"]["baseline"]["present_count"] == 0
    assert report["artifact_inventory"]["shadow"]["present_count"] == len(
        module.GATE_ADOPTION_ARTIFACTS
    )


def test_shadow_evidence_report_marks_repo_gate_without_artifacts_trace_only_needs_execution(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_shadow_evidence_report(
        repo_path=tmp_path / "repo",
        run_id="gate-run-3",
        workflow_key="repo_gate_adoption_v1",
        baseline_dirty=False,
        shadow={"worktree_path": str(tmp_path / "shadow"), "contamination_check_passed": True},
        inspect_commands={
            "shadow_parity": "shadow parity command",
            "operator_search": "operator search command",
            "daily_flow": "daily flow command",
        },
    )

    assert report["quality_signal"] == "trace_only_needs_shadow_execution"
    assert "No shadow gate-adoption artifacts found yet" in {
        finding["title"] for finding in report["findings"]
    }


def test_shadow_evidence_report_marks_non_gate_workflow_trace_only(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_shadow_evidence_report(
        repo_path=tmp_path / "repo",
        run_id="run-1",
        workflow_key="implementation-delivery",
        baseline_dirty=False,
        shadow=None,
        inspect_commands={
            "shadow_parity": "shadow parity command",
            "operator_search": "operator search command",
            "daily_flow": "daily flow command",
        },
    )

    assert report["quality_signal"] == "trace_only"
    assert [inspection["name"] for inspection in report["next_inspections"]] == [
        "shadow parity",
        "operator-search",
        "daily-flow",
    ]


def test_shadow_main_no_worktree_returns_planning_governance_route(tmp_path: Path, capsys) -> None:
    module = _load_module()
    db_path = tmp_path / "aios.db"
    db_path.write_text("", encoding="utf-8")
    repo = tmp_path / "AIOS"
    repo.mkdir()
    project = {"id": "project-aios", "name": "AIOS", "repo_path": str(repo)}

    class Helper:
        @staticmethod
        def resolve_project(*_args, **_kwargs):
            return project

        @staticmethod
        def start_work(*_args, **_kwargs):
            return {
                "returncode": 0,
                "json": {
                    "data": {
                        "run": {
                            "id": "run-planning",
                            "workflow_key": "planning-governance",
                            "packet_id": "packet-planning",
                            "route_id": "route-planning",
                            "status": "in_progress",
                        }
                    }
                },
            }

    with (
        patch.object(
            module.sys,
            "argv",
            [
                "codex-aios-shadow.py",
                "Add a new GSD phase for planning governance",
                "--db",
                str(db_path),
                "--no-worktree",
            ],
        ),
        patch.object(module, "load_route_helper", return_value=Helper),
        patch.object(
            module,
            "git_snapshot",
            return_value={"head": "abc123", "branch": "main", "dirty": False},
        ),
    ):
        assert module.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["aios_route"]["workflow_key"] == "planning-governance"
    assert payload["shadow"] is None
    assert payload["shadow_prompt"] is None
    assert payload["candidate_score"]["recommendation"] == "trace_only"
    assert payload["shadow_execution"]["status"] == "not_started"
    assert payload["evidence_report"]["schema"] == "aios-shadow-evidence-report-v0.1"
    assert payload["evidence_report"]["quality_signal"] == "trace_only"
    assert [
        inspection["name"] for inspection in payload["evidence_report"]["next_inspections"]
    ] == [
        "shadow parity",
        "operator-search",
        "daily-flow",
    ]


def test_shadow_main_no_worktree_returns_known_gsd_command_route(tmp_path: Path, capsys) -> None:
    module = _load_module()
    db_path = tmp_path / "aios.db"
    db_path.write_text("", encoding="utf-8")
    repo = tmp_path / "AIOS"
    repo.mkdir()
    project = {"id": "project-aios", "name": "AIOS", "repo_path": str(repo)}

    class Helper:
        @staticmethod
        def resolve_project(*_args, **_kwargs):
            return project

        @staticmethod
        def start_work(*_args, **_kwargs):
            return {
                "returncode": 0,
                "json": {
                    "data": {
                        "run": {
                            "id": "run-execute",
                            "workflow_key": "implementation-delivery",
                            "packet_id": "packet-execute",
                            "route_id": "route-execute",
                            "status": "in_progress",
                        }
                    }
                },
            }

    with (
        patch.object(
            module.sys,
            "argv",
            [
                "codex-aios-shadow.py",
                "gsd-execute-phase 24",
                "--db",
                str(db_path),
                "--no-worktree",
            ],
        ),
        patch.object(module, "load_route_helper", return_value=Helper),
        patch.object(
            module,
            "git_snapshot",
            return_value={"head": "abc123", "branch": "main", "dirty": False},
        ),
    ):
        assert module.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["aios_route"]["workflow_key"] == "implementation-delivery"
    assert payload["shadow"] is None
    assert payload["shadow_prompt"] is None
    assert payload["shadow_execution"]["status"] == "not_started"
    assert payload["evidence_report"]["quality_signal"] == "trace_only"
