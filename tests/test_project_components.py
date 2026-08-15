from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.aios_cli import EXIT_NOT_FOUND, EXIT_OK, run_cli
from services.project_components import set_project_component_enabled


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE projects (id TEXT PRIMARY KEY);
        CREATE TABLE project_aios_component_settings (
          project_id TEXT NOT NULL,
          component_key TEXT NOT NULL,
          enabled INTEGER NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY(project_id, component_key)
        );
        INSERT INTO projects (id) VALUES ('project-1');
        """
    )
    conn.commit()
    conn.close()


def test_set_project_component_enabled_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    first = set_project_component_enabled(
        conn,
        {"projectId": "project-1", "componentKey": "standards_health", "enabled": False},
    )
    second = set_project_component_enabled(
        conn,
        {"projectId": "project-1", "componentKey": "standards_health", "enabled": True},
    )

    assert first["enabled"] is False
    assert second["enabled"] is True
    stored = conn.execute(
        "SELECT enabled FROM project_aios_component_settings WHERE project_id = ? AND component_key = ?",
        ("project-1", "standards_health"),
    ).fetchone()
    assert stored["enabled"] == 1
    conn.close()


def test_set_project_component_enabled_rejects_unknown_component(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    with pytest.raises(ValueError, match="Unknown AIOS project component key"):
        set_project_component_enabled(
            conn,
            {"projectId": "project-1", "componentKey": "unknown", "enabled": True},
        )
    conn.close()


def test_cli_project_component_update_uses_python_owner(tmp_path: Path, capsys) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(path),
            "project-component-update",
            "--payload-json",
            json.dumps(
                {"projectId": "project-1", "componentKey": "taski_summary", "enabled": False}
            ),
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["project_id"] == "project-1"
    assert payload["data"]["component_key"] == "taski_summary"
    assert payload["data"]["enabled"] is False
    assert isinstance(payload["data"]["updated_at"], str)


def test_cli_project_component_update_reports_missing_project(tmp_path: Path, capsys) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(path),
            "project-component-update",
            "--payload-json",
            json.dumps({"projectId": "missing", "componentKey": "taski_summary", "enabled": True}),
        ]
    )

    assert exit_code == EXIT_NOT_FOUND
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "project-not-found"
