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


def test_prompt_submit_reassigns_stale_payload_to_current_session(
    hook_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_prompt = _load_module("hook_prompt_stale_pointer", "bin/hook-prompt-submit.py")
    aios_repo = tmp_path / "AIOS"
    stale_repo = tmp_path / "other"
    aios_repo.mkdir()
    stale_repo.mkdir()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    log_path = logs_dir / "hooks.log"
    (logs_dir / "current_session").write_text("current-aios-session", encoding="utf-8")

    conn = sqlite3.connect(hook_db)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES ('p-aios', 'AIOS', ?, '', 'active')",
        (str(aios_repo),),
    )
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES ('p-other', 'Other', ?, '', 'active')",
        (str(stale_repo),),
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
        VALUES ('stale-session', 'p-other', 'claude-code', '2026-05-18T00:00:00Z', 'stale', 'open', ?)
        """,
        (str(stale_repo),),
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
        VALUES ('current-aios-session', 'p-aios', 'claude-code', '2026-05-17T00:00:00Z',
                'Verify agent rules session injection', 'open', ?)
        """,
        (str(aios_repo),),
    )
    conn.commit()
    conn.close()

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
                    "session_id": "stale-session",
                    "cwd": str(aios_repo),
                    "prompt": "Audit the live agent-rules smoke test session",
                }
            )
        ),
    )

    hook_prompt.main()

    conn = sqlite3.connect(hook_db)
    prompt_rows = conn.execute(
        "SELECT session_id, prompt_text FROM prompts_used ORDER BY rowid"
    ).fetchall()
    conn.close()

    assert prompt_rows == [
        ("current-aios-session", "Audit the live agent-rules smoke test session")
    ]
    assert (
        "reassigned stale prompt-submit payload session stale-session to current session current-aios-session"
        in log_path.read_text()
    )


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


def test_stop_reassigns_stale_payload_and_closes_current_session(
    hook_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_stop = _load_module("hook_stop_stale_pointer", "bin/hook-stop.py")
    aios_repo = tmp_path / "AIOS"
    stale_repo = tmp_path / "other"
    aios_repo.mkdir()
    stale_repo.mkdir()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    log_path = logs_dir / "hooks.log"
    (logs_dir / "current_session").write_text("current-aios-session", encoding="utf-8")

    conn = sqlite3.connect(hook_db)
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES ('p-aios', 'AIOS', ?, '', 'active')",
        (str(aios_repo),),
    )
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES ('p-other', 'Other', ?, '', 'active')",
        (str(stale_repo),),
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
        VALUES ('stale-session', 'p-other', 'claude-code', '2026-05-18T00:00:00Z', 'stale', 'open', ?)
        """,
        (str(stale_repo),),
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
        VALUES ('current-aios-session', 'p-aios', 'claude-code', '2026-05-17T00:00:00Z',
                'Verify agent rules session injection', 'open', ?)
        """,
        (str(aios_repo),),
    )
    conn.commit()
    conn.close()

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
        io.StringIO(json.dumps({"session_id": "stale-session", "cwd": str(aios_repo)})),
    )

    hook_stop.main()

    conn = sqlite3.connect(hook_db)
    current = conn.execute(
        "SELECT status, ended_at FROM sessions WHERE id = 'current-aios-session'"
    ).fetchone()
    stale = conn.execute(
        "SELECT status, ended_at FROM sessions WHERE id = 'stale-session'"
    ).fetchone()
    conn.close()

    assert current is not None
    assert current[0] == "closed"
    assert current[1] is not None
    assert stale == ("open", None)
    assert (
        "reassigned stale stop payload session stale-session to current session current-aios-session"
        in log_path.read_text()
    )


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


def test_repair_stale_open_sessions_abandons_only_inactive_non_current(
    hook_db: Path,
    tmp_path: Path,
) -> None:
    repair = _load_module("repair_stale_open_sessions", "bin/repair-stale-open-sessions.py")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "current_session").write_text("current-session", encoding="utf-8")

    conn = sqlite3.connect(hook_db)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES ('p1', 'Repo', ?, '', 'active')",
        (str(repo_path),),
    )
    for session_id in ("stale-empty", "current-session", "has-prompt"):
        conn.execute(
            """
            INSERT INTO sessions (id, project_id, tool, started_at, objective, status, cwd)
            VALUES (?, 'p1', 'claude-code', '2026-05-01T00:00:00+00:00', ?, 'open', ?)
            """,
            (session_id, session_id, str(repo_path)),
        )
    conn.execute(
        """
        INSERT INTO prompts_used (id, session_id, prompt_text, reusable_candidate)
        VALUES ('prompt-1', 'has-prompt', 'Keep active because prompts exist', 0)
        """
    )
    conn.commit()

    rows = repair.stale_sessions(conn, older_than_days=2, current_id="current-session")
    assert [row["id"] for row in rows] == ["stale-empty"]

    repair.abandon_sessions(conn, rows, reason="unit-test")
    conn.commit()
    statuses = dict(conn.execute("SELECT id, status FROM sessions").fetchall())
    event = conn.execute(
        "SELECT event_type FROM tool_events WHERE session_id = 'stale-empty'"
    ).fetchone()
    conn.close()

    assert statuses["stale-empty"] == "abandoned"
    assert statuses["current-session"] == "open"
    assert statuses["has-prompt"] == "open"
    assert event is not None
    assert event[0] == "SessionAbandonedBackfill"


def test_resolve_session_cwd_replaces_agent_config_dir_with_registered_process_cwd(
    hook_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_lifecycle = _load_module("hook_lifecycle_attribution", "bin/hook_lifecycle.py")
    repo_path = tmp_path / "AIOS"
    repo_path.mkdir()
    monkeypatch.chdir(repo_path)

    conn = sqlite3.connect(hook_db)
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('project-aios', 'AIOS', ?, '', 'active')
        """,
        (str(repo_path),),
    )

    resolved = hook_lifecycle.resolve_session_cwd(conn, str(Path.home() / ".claude"))
    conn.close()

    assert resolved == str(repo_path)


def test_get_or_create_project_uses_registered_process_project_for_agent_config_payload(
    hook_db: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_lifecycle = _load_module("hook_lifecycle_project_attribution", "bin/hook_lifecycle.py")
    repo_path = tmp_path / "AIOS"
    repo_path.mkdir()
    monkeypatch.chdir(repo_path)

    conn = sqlite3.connect(hook_db)
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('project-aios', 'AIOS', ?, '', 'active')
        """,
        (str(repo_path),),
    )

    project_id = hook_lifecycle.get_or_create_project(conn, str(Path.home() / ".claude"))
    conn.close()

    assert project_id == "project-aios"
