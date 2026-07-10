# ruff: noqa: E402

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_purge_module():
    path = ROOT / "bin" / "purge-noise-patterns.py"
    spec = importlib.util.spec_from_file_location("purge_noise_patterns", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE patterns (
          id TEXT PRIMARY KEY,
          class TEXT,
          title TEXT,
          status TEXT,
          state TEXT,
          human_approved INTEGER DEFAULT 0,
          updated_at TEXT
        )
        """
    )


def test_purge_discards_noise_classes_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    purge = _load_purge_module()
    db_path = tmp_path / "aios.db"
    monkeypatch.setattr(purge, "DB", db_path)

    conn = sqlite3.connect(db_path)
    _schema(conn)
    rows = [
        ("p1", "personal", "candidate", "notice", 0),
        ("p2", "observation", "candidate", "notice", 0),
        ("p3", "error", "candidate", "observation", 0),
        ("p4", "workflow", "candidate", "notice", 0),
        ("p5", "personal", "active", "rule", 1),
    ]
    for pid, class_, status, state, approved in rows:
        conn.execute(
            "INSERT INTO patterns (id, class, title, status, state, human_approved) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, class_, class_, status, state, approved),
        )
    conn.commit()

    result = purge.purge_noise_patterns(conn, dry_run=False)
    assert result["discarded"] == 3

    remaining = {row[0]: row[1] for row in conn.execute(
        "SELECT id, status FROM patterns ORDER BY id"
    ).fetchall()}
    conn.close()
    assert remaining["p4"] == "candidate"
    assert remaining["p5"] == "active"
    assert remaining["p1"] == "discarded"
    assert remaining["p2"] == "discarded"
    assert remaining["p3"] == "discarded"


def test_purge_dry_run_counts_without_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    purge = _load_purge_module()
    db_path = tmp_path / "aios.db"
    monkeypatch.setattr(purge, "DB", db_path)

    conn = sqlite3.connect(db_path)
    _schema(conn)
    conn.execute(
        "INSERT INTO patterns (id, class, title, status, state, human_approved) VALUES ('x', 'error', 'e', 'candidate', 'notice', 0)"
    )
    conn.commit()

    result = purge.purge_noise_patterns(conn, dry_run=True)
    row = conn.execute("SELECT status FROM patterns WHERE id='x'").fetchone()
    conn.close()
    assert result["would_discard"] == 1
    assert row[0] == "candidate"
