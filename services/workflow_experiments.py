from __future__ import annotations

import json
import subprocess
import tempfile
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.workflow_orchestration import WorkflowExecutionContext, execute_workflow

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_REPOS = ROOT / "config" / "experiments" / "test-repos.json"
DEFAULT_PAPER_FIXTURES = ROOT / "fixtures" / "papers" / "generated"
DEFAULT_WORKFLOW_REGISTRY = ROOT / "config" / "workflows" / "registry.json"
DEFAULT_SKILL_REGISTRY = ROOT / "config" / "workflows" / "skills.json"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_workflow_experiment_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS github_skill_candidates (
          id TEXT PRIMARY KEY,
          workflow_key TEXT NOT NULL,
          skill_key TEXT NOT NULL,
          name TEXT NOT NULL,
          github_url TEXT NOT NULL,
          repo TEXT NOT NULL,
          path TEXT,
          summary TEXT NOT NULL,
          tags_json TEXT NOT NULL DEFAULT '[]',
          detail_json TEXT NOT NULL DEFAULT '{}',
          status TEXT NOT NULL DEFAULT 'candidate',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_skill_experiments (
          id TEXT PRIMARY KEY,
          workflow_key TEXT NOT NULL,
          skill_key TEXT NOT NULL,
          candidate_id TEXT,
          test_repo_id TEXT NOT NULL,
          test_repo_path TEXT NOT NULL,
          branch_name TEXT NOT NULL,
          experiment_kind TEXT NOT NULL,
          baseline_score REAL,
          candidate_score REAL,
          outcome TEXT,
          status TEXT NOT NULL DEFAULT 'queued',
          details_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
          UNIQUE(workflow_key, skill_key, test_repo_id, experiment_kind)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_paper_fixtures (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          fixture_path TEXT NOT NULL UNIQUE,
          purpose TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_test_repos(path: Path = DEFAULT_TEST_REPOS) -> list[dict[str, str]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    repos = loaded.get("test_repos", [])
    if not isinstance(repos, list):
        return []
    normalized = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        repo_id = str(repo.get("id", "")).strip()
        repo_path = str(repo.get("repo_path", "")).strip()
        if repo_id and repo_path:
            normalized.append(
                {
                    "id": repo_id,
                    "name": str(repo.get("name", repo_id)),
                    "repo_path": repo_path,
                    "profile": str(repo.get("profile", repo_id)),
                }
            )
    return normalized


def queue_test_repo_experiments(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    skill_key: str,
    candidate_id: str | None = None,
    test_repos_path: Path = DEFAULT_TEST_REPOS,
) -> list[dict[str, str]]:
    ensure_workflow_experiment_schema(conn)
    queued: list[dict[str, str]] = []
    for repo in load_test_repos(test_repos_path):
        branch_name = f"aios/experiment/{workflow_key}/{skill_key}/{repo['id']}"
        experiment_id = f"workflow-skill-exp-{uuid.uuid4()}"
        now = _now_iso()
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO workflow_skill_experiments (
              id, workflow_key, skill_key, candidate_id, test_repo_id, test_repo_path,
              branch_name, experiment_kind, status, details_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'test_repo_branch', 'queued', ?, ?, ?)
            """,
            (
                experiment_id,
                workflow_key,
                skill_key,
                candidate_id,
                repo["id"],
                repo["repo_path"],
                branch_name,
                _json({"repo_profile": repo["profile"], "repo_name": repo["name"]}),
                now,
                now,
            ),
        )
        if cursor.rowcount > 0:
            queued.append(
                {
                    "workflow_key": workflow_key,
                    "skill_key": skill_key,
                    "test_repo_id": repo["id"],
                    "branch_name": branch_name,
                }
            )
    return queued


def seed_paper_fixtures(
    conn: sqlite3.Connection,
    *,
    fixtures_dir: Path = DEFAULT_PAPER_FIXTURES,
) -> list[dict[str, str]]:
    ensure_workflow_experiment_schema(conn)
    seeded: list[dict[str, str]] = []
    if not fixtures_dir.exists():
        return seeded
    for path in sorted(fixtures_dir.glob("*.md")):
        title = path.stem.replace("-", " ").title()
        fixture_id = f"paper-fixture-{path.stem}"
        conn.execute(
            """
            INSERT OR IGNORE INTO workflow_paper_fixtures (id, title, fixture_path, purpose)
            VALUES (?, ?, ?, ?)
            """,
            (
                fixture_id,
                title,
                _display_path(path),
                "Humanizer workflow experiment fixture generated for controlled rewrite evaluation.",
            ),
        )
        seeded.append({"id": fixture_id, "path": _display_path(path)})
    return seeded


def _queued_rows(conn: sqlite3.Connection, *, limit: int, experiment_id: str | None = None) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    if experiment_id:
        return conn.execute(
            """
            SELECT * FROM workflow_skill_experiments
            WHERE id = ? AND status IN ('queued', 'running')
            LIMIT 1
            """,
            (experiment_id,),
        ).fetchall()
    return conn.execute(
        """
        SELECT * FROM workflow_skill_experiments
        WHERE status = 'queued'
        ORDER BY created_at, workflow_key, test_repo_id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _proposal_for_workflow(conn: sqlite3.Connection, workflow_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT proposal_key, workflow_spec_json, skill_specs_json
        FROM workflow_synthesis_proposals
        WHERE proposal_key = ? AND status != 'discarded'
        ORDER BY CASE status WHEN 'pending_approval' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END
        LIMIT 1
        """,
        (workflow_key,),
    ).fetchone()
    if row is None:
        return None
    return {
        "workflow_key": str(row["proposal_key"]),
        "workflow_spec": json.loads(str(row["workflow_spec_json"])),
        "skill_specs": json.loads(str(row["skill_specs_json"])),
    }


def _candidate_skill(conn: sqlite3.Connection, candidate_id: str | None) -> dict[str, Any] | None:
    if not candidate_id:
        return None
    row = conn.execute(
        """
        SELECT skill_key, summary, detail_json, tags_json
        FROM github_skill_candidates
        WHERE id = ? AND status IN ('candidate', 'wired', 'promoted')
        LIMIT 1
        """,
        (candidate_id,),
    ).fetchone()
    if row is None:
        return None
    try:
        detail = json.loads(str(row["detail_json"]))
    except json.JSONDecodeError:
        detail = {}
    try:
        tags = json.loads(str(row["tags_json"]))
    except json.JSONDecodeError:
        tags = []
    return {
        "key": str(row["skill_key"]),
        "purpose": str(row["summary"]),
        "allowed_stages": [str(tag) for tag in tags if isinstance(tag, str)] or ["generate"],
        "input_schema": {},
        "output_schema": {"result_text": "string"},
        "invariants": [str(item) for item in detail.get("invariants", []) if isinstance(item, str)],
        "failure_conditions": [
            str(item) for item in detail.get("failure_conditions", []) if isinstance(item, str)
        ],
        "side_effects": [],
        "execution_mode": str(detail.get("execution_mode", "heuristic")),
        "source": "github_skill_candidate",
        "runtime_adapter": "github_candidate_metadata_v1",
        "executable": False,
        "promotion_gate": "test_repo_experiment",
    }


def _base_skill_registry(extra_skills: list[dict[str, Any]]) -> dict[str, Any]:
    loaded = _load_json(DEFAULT_SKILL_REGISTRY)
    skills = [skill for skill in loaded.get("skills", []) if isinstance(skill, dict)]
    existing = {str(skill.get("key")) for skill in skills}
    for skill in extra_skills:
        key = str(skill.get("key", ""))
        if key and key not in existing:
            skills.append(skill)
            existing.add(key)
    return {**loaded, "skills": skills}


def _workflow_registry(workflow_spec: dict[str, Any]) -> dict[str, Any]:
    loaded = _load_json(DEFAULT_WORKFLOW_REGISTRY)
    return {
        "version": loaded.get("version", "experiment"),
        "stage_kinds": loaded.get("stage_kinds", []),
        "workflows": [workflow_spec],
    }


def _without_skill(workflow_spec: dict[str, Any], skill_key: str) -> dict[str, Any]:
    copied = json.loads(json.dumps(workflow_spec))
    for stage in copied.get("stages", []):
        if not isinstance(stage, dict):
            continue
        required = stage.get("required_skills", [])
        if isinstance(required, list):
            stage["required_skills"] = [skill for skill in required if skill != skill_key]
    return copied


def _score_report(report: dict[str, Any], skill_key: str) -> float:
    score = 0.0
    if report.get("status") == "completed":
        score += 0.25
    if not report.get("unresolved_issues"):
        score += 0.15
    failed = report.get("failed_required_validations") or []
    if not failed:
        score += 0.15
    artifacts = report.get("artifacts") if isinstance(report.get("artifacts"), dict) else {}
    if artifacts.get("normalized_prompt"):
        score += 0.1
    if artifacts.get("result_text"):
        score += 0.2
    if artifacts.get("learned_workflow_skill") == skill_key:
        score += 0.1
    for stage in report.get("stages", []):
        for skill in stage.get("skills", []):
            if skill.get("skill_key") == skill_key and skill.get("output_keys"):
                score += 0.05
    return round(min(score, 1.0), 4)


def _run_git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _prepare_branch(repo_path: Path, branch_name: str, dry_run: bool) -> dict[str, Any]:
    if not (repo_path / ".git").exists():
        return {"ok": False, "error": f"not a git repo: {repo_path}"}
    dirty = _run_git(repo_path, ["status", "--porcelain"])
    if dirty.returncode != 0:
        return {"ok": False, "error": dirty.stderr.strip() or dirty.stdout.strip()}
    if dirty.stdout.strip():
        return {"ok": False, "error": "repo has uncommitted changes"}
    current = _run_git(repo_path, ["branch", "--show-current"])
    original_branch = current.stdout.strip() or "HEAD"
    if dry_run:
        return {"ok": True, "original_branch": original_branch, "dry_run": True}
    exists = _run_git(repo_path, ["rev-parse", "--verify", branch_name])
    switch_args = ["switch", branch_name] if exists.returncode == 0 else ["switch", "-c", branch_name]
    switched = _run_git(repo_path, switch_args)
    if switched.returncode != 0:
        return {"ok": False, "error": switched.stderr.strip() or switched.stdout.strip()}
    _run_git(repo_path, ["config", "user.email", "aios-experiments@example.local"])
    _run_git(repo_path, ["config", "user.name", "AIOS Experiments"])
    return {"ok": True, "original_branch": original_branch}


def _write_repo_artifact(repo_path: Path, row: sqlite3.Row, payload: dict[str, Any], dry_run: bool) -> str | None:
    artifact_path = repo_path / ".aios" / "workflow-skill-experiments" / f"{row['id']}.json"
    if dry_run:
        return str(artifact_path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(artifact_path, payload)
    _run_git(repo_path, ["add", str(artifact_path.relative_to(repo_path))])
    commit = _run_git(
        repo_path,
        [
            "commit",
            "-m",
            f"Record AIOS workflow skill experiment {row['workflow_key']} on {row['test_repo_id']}",
        ],
    )
    if commit.returncode != 0 and "nothing to commit" not in (commit.stderr + commit.stdout).lower():
        raise RuntimeError(commit.stderr.strip() or commit.stdout.strip())
    return str(artifact_path)


def _restore_branch(repo_path: Path, original_branch: str | None, dry_run: bool) -> None:
    if dry_run or not original_branch or original_branch == "HEAD":
        return
    _run_git(repo_path, ["switch", original_branch])


def _execute_with_temp_registries(
    *,
    workflow_spec: dict[str, Any],
    skill_specs: list[dict[str, Any]],
    context: WorkflowExecutionContext,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aios-workflow-exp-") as tmp:
        tmp_path = Path(tmp)
        workflow_path = tmp_path / "registry.json"
        skills_path = tmp_path / "skills.json"
        _write_json(workflow_path, _workflow_registry(workflow_spec))
        _write_json(skills_path, _base_skill_registry(skill_specs))
        return execute_workflow(
            context,
            workflow_registry_path=workflow_path,
            skill_registry_path=skills_path,
        )


def run_workflow_skill_experiment(
    conn: sqlite3.Connection,
    experiment_id: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    ensure_workflow_experiment_schema(conn)
    rows = _queued_rows(conn, limit=1, experiment_id=experiment_id)
    if not rows:
        raise ValueError(f"Queued workflow skill experiment not found: {experiment_id}")
    row = rows[0]
    proposal = _proposal_for_workflow(conn, str(row["workflow_key"]))
    if proposal is None:
        raise ValueError(f"No active workflow proposal found for {row['workflow_key']}")
    skill_specs = [skill for skill in proposal["skill_specs"] if isinstance(skill, dict)]
    candidate_skill = _candidate_skill(conn, row["candidate_id"])
    if candidate_skill is not None:
        skill_specs.append(candidate_skill)

    skill_key = str(row["skill_key"])
    repo_path = ROOT / str(row["test_repo_path"])
    branch = _prepare_branch(repo_path, str(row["branch_name"]), dry_run)
    if not branch.get("ok"):
        details = {"error": branch.get("error"), "repo_path": str(repo_path)}
        conn.execute(
            """
            UPDATE workflow_skill_experiments
            SET status='blocked', outcome='blocked', details_json=?, updated_at=?
            WHERE id=?
            """,
            (_json(details), _now_iso(), experiment_id),
        )
        conn.commit()
        return {"id": experiment_id, "status": "blocked", "details": details}

    now = _now_iso()
    conn.execute(
        "UPDATE workflow_skill_experiments SET status='running', updated_at=? WHERE id=?",
        (now, experiment_id),
    )
    conn.commit()

    objective = (
        f"Run {row['workflow_key']} on the {row['test_repo_id']} test repository "
        f"and produce an evidence-backed workflow execution report."
    )
    context = WorkflowExecutionContext(
        objective=objective,
        workflow_key=str(row["workflow_key"]),
        repo_path=str(repo_path),
    )
    baseline_spec = _without_skill(proposal["workflow_spec"], skill_key)
    candidate_spec = proposal["workflow_spec"]
    baseline_report = _execute_with_temp_registries(
        workflow_spec=baseline_spec,
        skill_specs=skill_specs,
        context=context,
    )
    candidate_report = _execute_with_temp_registries(
        workflow_spec=candidate_spec,
        skill_specs=skill_specs,
        context=context,
    )
    baseline_score = _score_report(baseline_report, skill_key)
    candidate_score = _score_report(candidate_report, skill_key)
    delta = round(candidate_score - baseline_score, 4)
    outcome = "promotion_ready" if delta >= 0.05 else "no_improvement"
    artifact_payload = {
        "experiment_id": experiment_id,
        "workflow_key": row["workflow_key"],
        "skill_key": skill_key,
        "test_repo_id": row["test_repo_id"],
        "baseline_score": baseline_score,
        "candidate_score": candidate_score,
        "score_delta": delta,
        "outcome": outcome,
        "baseline_report": baseline_report,
        "candidate_report": candidate_report,
    }
    artifact_path: str | None = None
    original_branch = str(branch.get("original_branch") or "")
    try:
        artifact_path = _write_repo_artifact(repo_path, row, artifact_payload, dry_run)
    finally:
        _restore_branch(repo_path, original_branch, dry_run)

    details = {
        "score_delta": delta,
        "branch_name": row["branch_name"],
        "artifact_path": artifact_path,
        "baseline_status": baseline_report.get("status"),
        "candidate_status": candidate_report.get("status"),
        "dry_run": dry_run,
    }
    conn.execute(
        """
        UPDATE workflow_skill_experiments
        SET status='completed',
            baseline_score=?,
            candidate_score=?,
            outcome=?,
            details_json=?,
            updated_at=?
        WHERE id=?
        """,
        (
            baseline_score,
            candidate_score,
            outcome,
            _json(details),
            _now_iso(),
            experiment_id,
        ),
    )
    conn.commit()
    return {
        "id": experiment_id,
        "workflow_key": row["workflow_key"],
        "skill_key": skill_key,
        "test_repo_id": row["test_repo_id"],
        "baseline_score": baseline_score,
        "candidate_score": candidate_score,
        "score_delta": delta,
        "outcome": outcome,
        "artifact_path": artifact_path,
    }


def run_queued_workflow_skill_experiments(
    conn: sqlite3.Connection,
    *,
    limit: int = 20,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    ensure_workflow_experiment_schema(conn)
    rows = _queued_rows(conn, limit=limit)
    results = []
    for row in rows:
        results.append(run_workflow_skill_experiment(conn, str(row["id"]), dry_run=dry_run))
    return results
