from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = ROOT / "scripts" / "codex-aios-route.py"
    spec = importlib.util.spec_from_file_location("codex_aios_route", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _db(path: Path, repo: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          repo_path TEXT,
          status TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, status) VALUES (?, ?, ?, 'active')",
        ("project-aios", "AIOS", str(repo)),
    )
    conn.commit()
    conn.close()
    return path


def test_resolve_project_by_name(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path / "AIOS"
    repo.mkdir()
    db_path = _db(tmp_path / "aios.db", repo)

    project = module.resolve_project(db_path, explicit="AIOS", cwd=tmp_path)

    assert project["id"] == "project-aios"


def test_resolve_project_by_cwd_inside_repo(tmp_path: Path) -> None:
    module = _load_module()
    repo = tmp_path / "AIOS"
    nested = repo / "services"
    nested.mkdir(parents=True)
    db_path = _db(tmp_path / "aios.db", repo)

    project = module.resolve_project(db_path, explicit=None, cwd=nested)

    assert project["name"] == "AIOS"


def test_start_work_retries_detached_on_implicit_stale_session(tmp_path: Path) -> None:
    module = _load_module()
    stale_result = {
        "returncode": 3,
        "json": {"error": {"code": "session-not-found", "message": "Session not found: stale"}},
    }
    ok_result = {"returncode": 0, "json": {"ok": True, "data": {"run": {"id": "run-1"}}}}

    with patch.object(module, "run_json_command", side_effect=[stale_result, ok_result]) as run:
        result = module.start_work(
            db_path=tmp_path / "aios.db",
            objective="Fix stale session",
            project_id="project-aios",
        )

    assert result == ok_result
    assert run.call_count == 2
    assert "--session-id" not in run.call_args_list[0].args[0]
    assert run.call_args_list[1].args[0][-2:] == ["--session-id", ""]


def test_start_work_does_not_retry_non_session_failures(tmp_path: Path) -> None:
    module = _load_module()
    blocked_result = {
        "returncode": 2,
        "json": {"error": {"code": "route-blocked", "message": "Ambiguous objective"}},
    }

    with patch.object(module, "run_json_command", return_value=blocked_result) as run:
        result = module.start_work(
            db_path=tmp_path / "aios.db",
            objective="Do the thing",
            project_id="project-aios",
        )

    assert result == blocked_result
    assert run.call_count == 1
