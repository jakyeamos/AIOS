from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.rtk_integration import ensure_rtk_schema  # noqa: E402


def _seed_tier_one_db(path: Path, repo_path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('p1', 'AIOS', ?, ?, 'active')
        """,
        (str(repo_path), str(repo_path)),
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, tool, started_at, ended_at, objective, status, cwd, run_id)
        VALUES (
          's1', 'p1', 'codex', '2026-04-29T00:00:00Z', '2026-04-29T00:10:00Z',
          'tier one regression', 'closed', ?, 'run-1'
        )
        """,
        (str(repo_path),),
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
          id, project_id, session_id, objective, workflow_key, agent_key, status,
          rationale, assumptions_json, context_trace_json, created_at, updated_at
        )
        VALUES (
          'run-1', 'p1', 's1', 'tier one regression', 'implementation-delivery',
          'implementation-lead', 'completed', 'test', '[]', '[]',
          '2026-04-29T00:00:00Z', '2026-04-29T00:10:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_run_events (id, run_id, event_type, to_status, summary, reason_json, created_at)
        VALUES ('event-1', 'run-1', 'completed', 'completed', 'completed', '{}', '2026-04-29T00:10:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO prompt_library_links (id, prompt_hash, obsidian_note_path, promoted_at)
        VALUES ('prompt-link-1', 'hash-1', '/vault/prompt.md', '2026-04-29T00:00:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO knowledge_topics (
          id, slug, kind, title, summary, canonical_href, confidence, project_id, updated_at
        )
        VALUES (
          'topic-1', 'aios-memory', 'project_memory', 'AIOS Memory',
          'Source-backed memory object.', '/knowledge/aios-memory', 0.9, 'p1',
          '2026-04-29T00:00:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO knowledge_references (
          id, topic_id, source_kind, source_id, label, href, excerpt, freshness, confidence, created_at
        )
        VALUES (
          'ref-1', 'topic-1', 'project_memory', 'run-1', 'Run source',
          '/runs/run-1', 'Source excerpt.', 'fresh', 0.9, '2026-04-29T00:00:00Z'
        )
        """
    )
    ensure_rtk_schema(conn)
    conn.execute(
        """
        INSERT INTO rtk_compression_events (
          id, source_kind, command, mode, effective_mode, exit_code,
          raw_chars, compressed_chars, estimated_raw_tokens, estimated_compressed_tokens,
          token_reduction_percent, ambiguous_failure, metadata_json
        )
        VALUES (
          'rtk-1', 'test', 'echo ok', 'compressed', 'compressed', 0,
          40, 80, 10, 20, 0.0, 0, '{}'
        )
        """
    )
    conn.commit()
    conn.close()


def test_tier_one_audits_preserve_core_contracts(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    repo_path = tmp_path / "repo"
    logs_dir.mkdir()
    repo_path.mkdir()
    _seed_tier_one_db(db_path, repo_path)

    lifecycle_exit = run_cli(["--json", "--db", str(db_path), "--logs-dir", str(logs_dir), "lifecycle-audit"])
    assert lifecycle_exit == EXIT_OK
    lifecycle = json.loads(capsys.readouterr().out)["data"]
    assert lifecycle["summary"]["unsupported_state_count"] == 0

    contracts_exit = run_cli(["--json", "--db", str(db_path), "--logs-dir", str(logs_dir), "contracts-audit"])
    assert contracts_exit == EXIT_OK
    contracts = json.loads(capsys.readouterr().out)["data"]
    assert contracts["summary"]["canonical_contract_count"] == 7
    assert contracts["summary"]["implemented_count"] == 7
    assert contracts["summary"]["partial_count"] == 0

    capability_exit = run_cli(["--json", "--db", str(db_path), "--logs-dir", str(logs_dir), "capability-audit"])
    assert capability_exit == EXIT_OK
    capability = json.loads(capsys.readouterr().out)["data"]
    assert capability["prompt_library"]["visibility"]["value"] == "visible"
    assert capability["rtk"]["state"]["value"] == "token_regressive"
    assert capability["rtk"]["state"]["explanation"]
    assert capability["automations"]["items"][0]["trigger"]["value"] == "Weekdays at 9:00 AM"
    assert capability["automations"]["items"][0]["status"]["value"] == "unknown"
    assert capability["automations"]["items"][0]["status"]["missing_reason"]
    assert any(finding["code"] == "automation_history_missing" for finding in capability["findings"])

    learning_exit = run_cli(["--json", "--db", str(db_path), "--logs-dir", str(logs_dir), "workflow-learning-audit"])
    assert learning_exit == EXIT_OK
    learning = json.loads(capsys.readouterr().out)["data"]
    assert "no_learning_count" in learning["summary"]
    assert learning["summary"]["terminal_run_count"] >= 1
