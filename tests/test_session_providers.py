# ruff: noqa: E402
"""12 test cases covering all acceptance criteria for the session provider pipeline."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.session_providers.antigravity import AntigravityProvider
from services.session_providers.base import NormalizedSession, RawSession, SourcePath
from services.session_providers.cursor import CursorProvider
from services.session_summarizer import summarize_session
from services.session_writeback import emit_writeback_candidates

CURSOR_FIXTURE = ROOT / "tests" / "fixtures" / "cursor"
ANTIGRAVITY_FIXTURE = ROOT / "tests" / "fixtures" / "antigravity"


def _load_sessions_cli():
    spec = importlib.util.spec_from_file_location("sessions_cli", ROOT / "bin" / "sessions.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["sessions_cli"] = module
    spec.loader.exec_module(module)
    return module


def _cursor_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    workspace = home / "Library/Application Support/Cursor/User/workspaceStorage/hash-1"
    workspace.mkdir(parents=True)
    shutil.copy2(CURSOR_FIXTURE / "state.vscdb", workspace / "state.vscdb")
    project = tmp_path / "my-project"
    project.mkdir()
    (workspace / "workspace.json").write_text(
        json.dumps({"folder": str(project)}),
        encoding="utf-8",
    )
    transcript_dir = home / ".cursor/projects/project-a/agent-transcripts"
    transcript_dir.mkdir(parents=True)
    shutil.copy2(
        CURSOR_FIXTURE / "agent-transcripts/session-001.jsonl", transcript_dir / "session-001.jsonl"
    )
    return home


def _antigravity_root(tmp_path: Path) -> Path:
    gemini = tmp_path / ".gemini"
    brain = gemini / "antigravity-cli" / "brain"
    shutil.copytree(ANTIGRAVITY_FIXTURE / "brain", brain)
    return gemini


def test_provider_discovery_with_fixture_dirs(tmp_path: Path) -> None:
    cursor_provider = CursorProvider(
        home=_cursor_home(tmp_path), snapshot_root=tmp_path / "snapshots"
    )
    cursor_sources = cursor_provider.discover_sources()
    assert {source.source_type for source in cursor_sources} >= {
        "cursor_workspace_vscdb",
        "cursor_agent_transcript_jsonl",
    }

    antigravity = AntigravityProvider(gemini_root=_antigravity_root(tmp_path))
    antigravity_sources = antigravity.discover_sources()
    assert any(
        source.source_type == "antigravity_brain_session_dir" for source in antigravity_sources
    )


def test_cursor_sqlite_itemtable_import(tmp_path: Path) -> None:
    provider = CursorProvider(home=_cursor_home(tmp_path), snapshot_root=tmp_path / "snapshots")
    source = next(
        s for s in provider.discover_sources() if s.source_type == "cursor_workspace_vscdb"
    )
    raw = provider.extract_raw_session(source)
    normalized = provider.normalize_session(raw)
    assert normalized.provider == "cursor"
    assert normalized.messages
    assert normalized.tool_calls
    assert normalized.file_edits


def test_cursor_jsonl_transcript_import(tmp_path: Path) -> None:
    provider = CursorProvider(home=_cursor_home(tmp_path), snapshot_root=tmp_path / "snapshots")
    source = next(
        s for s in provider.discover_sources() if s.source_type == "cursor_agent_transcript_jsonl"
    )
    raw = provider.extract_raw_session(source)
    normalized = provider.normalize_session(raw)
    assert normalized.provider_session_id == "cursor-jsonl-1"
    assert normalized.messages
    assert normalized.commands_run == ["python -m pytest"]


def test_cursor_workspace_hash_and_path_mapping(tmp_path: Path) -> None:
    provider = CursorProvider(home=_cursor_home(tmp_path), snapshot_root=tmp_path / "snapshots")
    source = next(
        s for s in provider.discover_sources() if s.source_type == "cursor_workspace_vscdb"
    )
    normalized = provider.normalize_session(provider.extract_raw_session(source))
    assert normalized.workspace_id == "hash-1"
    assert normalized.workspace_path == str(tmp_path / "my-project")


def test_antigravity_numeric_dir_import(tmp_path: Path) -> None:
    provider = AntigravityProvider(gemini_root=_antigravity_root(tmp_path))
    source = next(s for s in provider.discover_sources() if s.path.name == "session.json")
    normalized = provider.normalize_session(provider.extract_raw_session(source))
    assert normalized.provider_session_id == "1234567"
    assert normalized.commands_run
    assert normalized.file_edits


def test_antigravity_unknown_binary_health_warning(tmp_path: Path) -> None:
    provider = AntigravityProvider(gemini_root=_antigravity_root(tmp_path))
    health = provider.health_check()
    assert health.source_counts["unknown_binary"] >= 1
    assert any("metadata only" in warning for warning in health.warnings)


class _FixtureProvider:
    provider_id = "fixture"

    def __init__(self, source: Path) -> None:
        self.source = source

    def discover_sources(self) -> list[SourcePath]:
        return [SourcePath(path=self.source, source_type="fixture")]

    def extract_raw_session(self, source: SourcePath) -> RawSession:
        return RawSession(
            provider="fixture", source=source, payload=json.loads(source.path.read_text())
        )

    def normalize_session(self, raw: RawSession) -> NormalizedSession:
        payload = raw.payload
        return NormalizedSession(
            provider="fixture",
            stable_session_id="fixture:1",
            provider_session_id="1",
            workspace_path=None,
            workspace_id=None,
            project_id=None,
            started_at=None,
            updated_at=None,
            imported_at="2026-06-23T00:00:00Z",
            source_files=[str(raw.source.path)],
            source_file_mtimes={str(raw.source.path): raw.source.path.stat().st_mtime},
            content_hash=str(payload["content_hash"]),
            title=str(payload["title"]),
            participants=["user"],
            messages=[{"role": "user", "text": payload["title"]}],
            tool_calls=[],
            file_edits=[],
            commands_run=[],
            decisions_extracted=[],
            todos_extracted=[],
            errors_extracted=[],
            summary_status="pending",
            writeback_status="pending",
            confidence=0.7,
        )

    def upsert_session(self, normalized: NormalizedSession) -> str:
        return normalized.stable_session_id


def test_incremental_sync_no_duplicate(monkeypatch, tmp_path: Path) -> None:
    sessions_cli = _load_sessions_cli()
    source = tmp_path / "session.json"
    source.write_text(json.dumps({"title": "first", "content_hash": "a"}), encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    sessions_cli.ensure_schema(conn)
    monkeypatch.setattr(
        sessions_cli, "instantiate_provider", lambda _provider_id: _FixtureProvider(source)
    )

    first = sessions_cli.sync_provider(conn, "fixture", dry_run=False, backfill=False)
    second = sessions_cli.sync_provider(conn, "fixture", dry_run=False, backfill=False)

    assert first.imported == 1
    assert second.imported == 0
    assert conn.execute("SELECT COUNT(*) FROM session_imports").fetchone()[0] == 1


def test_changed_mtime_hash_triggers_update(monkeypatch, tmp_path: Path) -> None:
    sessions_cli = _load_sessions_cli()
    source = tmp_path / "session.json"
    source.write_text(json.dumps({"title": "first", "content_hash": "a"}), encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    sessions_cli.ensure_schema(conn)
    monkeypatch.setattr(
        sessions_cli, "instantiate_provider", lambda _provider_id: _FixtureProvider(source)
    )

    sessions_cli.sync_provider(conn, "fixture", dry_run=False, backfill=False)
    source.write_text(json.dumps({"title": "second", "content_hash": "b"}), encoding="utf-8")
    result = sessions_cli.sync_provider(conn, "fixture", dry_run=False, backfill=False)

    assert result.imported == 1
    title = conn.execute(
        "SELECT title FROM session_imports WHERE stable_session_id = 'fixture:1'"
    ).fetchone()[0]
    assert title == "second"


def test_dry_run_no_db_writes(monkeypatch, tmp_path: Path) -> None:
    sessions_cli = _load_sessions_cli()
    source = tmp_path / "session.json"
    source.write_text(json.dumps({"title": "first", "content_hash": "a"}), encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    sessions_cli.ensure_schema(conn)
    monkeypatch.setattr(
        sessions_cli, "instantiate_provider", lambda _provider_id: _FixtureProvider(source)
    )

    before = conn.execute("SELECT COUNT(*) FROM session_imports").fetchone()[0]
    result = sessions_cli.sync_provider(conn, "fixture", dry_run=True, backfill=False)
    after = conn.execute("SELECT COUNT(*) FROM session_imports").fetchone()[0]

    assert result.imported == 0
    assert before == after


def test_secrets_redacted_from_summaries(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _insert_session_import(
        conn,
        title="Use sk-" + "a" * 24,
        message="Use sk-" + "a" * 24,
    )
    summary = summarize_session("fixture:secret", conn)
    assert "[REDACTED:api_key]" in json.dumps(summary.to_dict())
    assert "sk-" not in json.dumps(summary.to_dict())


def test_raw_sessions_not_written_into_vault_notes(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _insert_session_import(conn, title="Implement writeback", message="Implement writeback")
    summary = summarize_session("fixture:secret", conn)
    candidates = emit_writeback_candidates(
        "fixture:secret", summary, conn=conn, summary_dir=tmp_path
    )
    assert candidates
    payload = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert payload["raw_transcript_included"] is False
    assert "messages" not in payload
    assert "Implement writeback" in payload["what_i_was_trying_to_do"]


def _insert_session_import(
    conn: sqlite3.Connection,
    *,
    message: str,
    title: str = "Sensitive session",
) -> None:
    conn.execute(
        """CREATE TABLE session_imports (
        stable_session_id TEXT PRIMARY KEY, provider_id TEXT, provider_session_id TEXT,
        workspace_path TEXT, workspace_id TEXT, project_id TEXT, started_at TEXT, updated_at TEXT,
        imported_at TEXT, source_files_json TEXT, source_file_mtimes_json TEXT, content_hash TEXT,
        title TEXT, participants_json TEXT, messages_json TEXT, tool_calls_json TEXT,
        file_edits_json TEXT, commands_run_json TEXT, decisions_extracted_json TEXT,
        todos_extracted_json TEXT, errors_extracted_json TEXT, summary_status TEXT,
        writeback_status TEXT, confidence REAL, provider_metadata_json TEXT, redaction_incomplete INTEGER)"""
    )
    conn.execute(
        "INSERT INTO session_imports VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "fixture:secret",
            "fixture",
            "secret",
            "/repo",
            None,
            "project-aios",
            None,
            None,
            "2026-06-23T00:00:00Z",
            json.dumps(["source"]),
            json.dumps({}),
            "hash",
            title,
            json.dumps(["user"]),
            json.dumps([{"role": "user", "text": message}]),
            json.dumps([]),
            json.dumps([{"path": "services/session_writeback.py"}]),
            json.dumps(["uv run pytest"]),
            json.dumps(["Decision: proposal flow"]),
            json.dumps([]),
            json.dumps([]),
            "pending",
            "pending",
            0.8,
            json.dumps({}),
            0,
        ),
    )
