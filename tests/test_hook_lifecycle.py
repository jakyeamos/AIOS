from __future__ import annotations

import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))


def _load_module(module_name: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _apply_base_schema(conn: sqlite3.Connection) -> None:
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))


@pytest.fixture
def hook_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "aios.db"
    conn = sqlite3.connect(db_path)
    _apply_base_schema(conn)
    conn.commit()
    conn.close()
    return db_path


def test_prompt_submit_recovers_missing_session_before_logging_prompt(
    hook_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_prompt = _load_module("hook_prompt_lifecycle", "bin/hook-prompt-submit.py")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    log_path = tmp_path / "hooks.log"

    monkeypatch.setattr(hook_prompt, "DB", str(hook_db))
    monkeypatch.setattr(hook_prompt, "LOG", str(log_path))
    monkeypatch.setattr(
        hook_prompt,
        "load_policy",
        lambda: {"prompt_retrieval": {"enabled": False}, "reusable_prompt_hint": {"enabled": False}},
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "missing-session",
                    "cwd": str(repo_path),
                    "prompt": "Fix the hook lifecycle recovery regression",
                }
            )
        ),
    )

    hook_prompt.main()

    conn = sqlite3.connect(hook_db)
    session = conn.execute(
        "SELECT id, status, cwd, objective FROM sessions WHERE id = 'missing-session'"
    ).fetchone()
    prompts = conn.execute(
        "SELECT prompt_text FROM prompts_used WHERE session_id = 'missing-session'"
    ).fetchall()
    conn.close()

    assert session == (
        "missing-session",
        "open",
        str(repo_path),
        "Fix the hook lifecycle recovery regression",
    )
    assert prompts == [("Fix the hook lifecycle recovery regression",)]
    assert "recovered missing session missing-session from UserPromptSubmit" in log_path.read_text()


def test_stop_recovers_missing_session_and_closes_it(
    hook_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_stop = _load_module("hook_stop_lifecycle", "bin/hook-stop.py")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    log_path = tmp_path / "hooks.log"

    monkeypatch.setattr(hook_stop, "DB", str(hook_db))
    monkeypatch.setattr(hook_stop, "LOG", str(log_path))
    monkeypatch.setattr(hook_stop, "SUMMARIES_DIR", str(tmp_path / "summaries"))
    monkeypatch.setattr(hook_stop.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        hook_stop,
        "evaluate_and_record",
        lambda *_args, **_kwargs: {
            "evaluation_id": "criteria-eval",
            "summary": "ok",
        },
    )
    monkeypatch.setattr(
        hook_stop,
        "evaluate_standards_health",
        lambda *_args, **_kwargs: {
            "snapshot_id": "standards-eval",
            "summary": "ok",
        },
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "session_id": "stop-missing-session",
                    "cwd": str(repo_path),
                    "objective": "Close recovered lifecycle session",
                }
            )
        ),
    )

    hook_stop.main()

    conn = sqlite3.connect(hook_db)
    session = conn.execute(
        "SELECT status, ended_at, objective, cwd FROM sessions WHERE id = 'stop-missing-session'"
    ).fetchone()
    memory_update = conn.execute(
        "SELECT summary FROM memory_updates WHERE session_id = 'stop-missing-session'"
    ).fetchone()
    conn.close()

    assert session is not None
    assert session[0] == "closed"
    assert session[1] is not None
    assert session[2] == "Close recovered lifecycle session"
    assert session[3] == str(repo_path)
    assert memory_update is not None
    assert "Close recovered lifecycle session" in memory_update[0]
    assert "recovered missing session stop-missing-session from Stop" in log_path.read_text()


def test_stop_empty_stdin_uses_current_session_pointer(
    hook_db: Path,
    tmp_path: Path,
) -> None:
    conn = sqlite3.connect(hook_db)
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('project-aios', 'AIOS', ?, '', 'active')
        """,
        (str(tmp_path),),
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
        VALUES ('current-session', 'project-aios', 'claude-code', '2026-05-13T19:00:00Z',
                'Already closed session', 'closed', ?)
        """,
        (str(tmp_path),),
    )
    conn.commit()
    conn.close()

    home_dir = tmp_path / "home"
    logs_dir = home_dir / "AIOS" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "current_session").write_text("current-session", encoding="utf-8")
    log_path = logs_dir / "hooks.log"

    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "hook-stop.py")],
        input="",
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "HOME": str(home_dir),
            "AIOS_DB": str(hook_db),
            "PYTHONPATH": f"{BIN}:{ROOT}",
        },
    )

    assert result.returncode == 0
    assert "AIOS · session already closed, skipping" in result.stdout
    assert log_path.exists()
    assert "empty stdin; using current_session pointer for stop" in log_path.read_text()
    assert "failed to parse stdin" not in log_path.read_text()
