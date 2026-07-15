from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.aios_cli import EXIT_OK, run_cli
from services.pattern_mutations import update_pattern_approval


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE patterns (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          status TEXT NOT NULL,
          state TEXT NOT NULL,
          human_approved INTEGER NOT NULL,
          promoted_at TEXT
        );
        INSERT INTO patterns (id, title, status, state, human_approved, promoted_at)
        VALUES ('pattern-1', 'A recurring pattern', 'candidate', 'hypothesis', 0, NULL);
        """
    )
    conn.commit()
    conn.close()


def test_update_pattern_approval_approves_and_preserves_promotion_time(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)
    conn = sqlite3.connect(path)

    result = update_pattern_approval(conn, {"id": "pattern-1", "decision": "approve"})
    repeat = update_pattern_approval(conn, {"id": "pattern-1", "decision": "approve"})

    assert result == {"ok": True, "id": "pattern-1", "changed_rows": 1}
    assert repeat["changed_rows"] == 1
    row = conn.execute(
        "SELECT status, state, human_approved, promoted_at FROM patterns WHERE id = ?",
        ("pattern-1",),
    ).fetchone()
    assert row is not None
    assert row[0:3] == ("active", "rule", 1)
    assert isinstance(row[3], str)
    conn.close()


def test_update_pattern_approval_rejects(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)
    conn = sqlite3.connect(path)

    result = update_pattern_approval(conn, {"id": "pattern-1", "decision": "reject"})

    assert result == {"ok": True, "id": "pattern-1", "changed_rows": 1}
    row = conn.execute(
        "SELECT status, human_approved FROM patterns WHERE id = ?",
        ("pattern-1",),
    ).fetchone()
    assert row == ("discarded", 0)
    conn.close()


def test_update_pattern_approval_handles_missing_table_and_unknown_id(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    conn = sqlite3.connect(path)

    missing_table = update_pattern_approval(conn, {"id": "pattern-1", "decision": "approve"})
    assert missing_table == {"ok": False, "id": "pattern-1", "changed_rows": 0}
    conn.close()

    _seed_db(path)
    conn = sqlite3.connect(path)
    missing_row = update_pattern_approval(conn, {"id": "missing", "decision": "reject"})
    assert missing_row == {"ok": False, "id": "missing", "changed_rows": 0}
    conn.close()


def test_update_pattern_approval_rejects_invalid_payload(tmp_path: Path) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)
    conn = sqlite3.connect(path)

    with pytest.raises(ValueError, match="decision must be one of"):
        update_pattern_approval(conn, {"id": "pattern-1", "decision": "keep"})
    with pytest.raises(ValueError, match="Unsupported pattern approval fields"):
        update_pattern_approval(
            conn,
            {"id": "pattern-1", "decision": "approve", "status": "active"},
        )
    conn.close()


def test_cli_pattern_approval_update_uses_python_owner(tmp_path: Path, capsys) -> None:
    path = tmp_path / "aios.db"
    _seed_db(path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(path),
            "pattern-approval-update",
            "--payload-json",
            json.dumps({"id": "pattern-1", "decision": "approve"}),
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["schema"] == "pattern-approval-update-result-v1"
    assert payload["data"]["id"] == "pattern-1"
    assert payload["data"]["decision"] == "approve"
    assert payload["data"]["changed_rows"] == 1
