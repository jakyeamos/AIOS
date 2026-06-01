from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from services.session_effectiveness import write_session_effectiveness_receipt  # noqa: E402


def _load_hook_stop() -> Any:
    path = ROOT / "bin" / "hook-stop.py"
    spec = importlib.util.spec_from_file_location("hook_stop", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _conn(status: str = "completed") -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE workflow_execution_reports (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          invocation_id TEXT,
          workflow_key TEXT,
          status TEXT,
          report_json TEXT,
          artifact_path TEXT,
          created_at TEXT
        );
        CREATE TABLE agentize_evaluations (
          id TEXT PRIMARY KEY,
          packet_id TEXT,
          original_request TEXT,
          transformed_request_json TEXT,
          selected_execution_mode TEXT,
          selected_skills_json TEXT DEFAULT '[]',
          selected_standards_json TEXT DEFAULT '[]',
          created_at TEXT
        );
        CREATE TABLE improvement_writebacks (
          id TEXT PRIMARY KEY,
          run_id TEXT,
          project_id TEXT,
          layer_type TEXT,
          layer_key TEXT,
          title TEXT,
          summary TEXT,
          evidence_json TEXT DEFAULT '[]',
          proposed_change_json TEXT DEFAULT '{}',
          impact_scope TEXT DEFAULT 'scoped',
          status TEXT,
          requires_approval INTEGER DEFAULT 0,
          approval_reason TEXT,
          token_regressive INTEGER DEFAULT 0,
          created_at TEXT,
          updated_at TEXT
        );
        """
    )
    conn.execute(
        """
        INSERT INTO workflow_execution_reports
        VALUES ('wr1', 'run-1', NULL, 'implementation-delivery', ?, ?, NULL, '2026-05-24T00:00:00Z')
        """,
        (
            status,
            json.dumps(
                {
                    "stage_evaluations": [
                        {
                            "stage_key": "validate",
                            "outcome": "completed",
                            "blocker_count": 0,
                        }
                    ]
                }
            ),
        ),
    )
    conn.execute(
        """
        INSERT INTO agentize_evaluations
        VALUES ('ae1', 'packet-1', 'request', ?, 'single', '[]', '[]', '2026-05-24T00:00:00Z')
        """,
        (json.dumps({"experiment_metadata": {"recommendation_source": "recommender"}}),),
    )
    return conn


def test_hook_stop_emits_asset_promotion_candidate_when_threshold_crossed() -> None:
    module = _load_hook_stop()
    conn = _conn()
    writeback_id = module._emit_asset_promotion_candidate(
        conn,
        run_id="run-1",
        project_id="p1",
    )
    assert writeback_id is not None
    payload = conn.execute("SELECT proposed_change_json FROM improvement_writebacks").fetchone()[0]
    assert json.loads(payload)["policy_class"] == "asset_promotion_candidate"

    failed_conn = _conn(status="failed")
    assert (
        module._emit_asset_promotion_candidate(failed_conn, run_id="run-1", project_id="p1") is None
    )


def test_hook_stop_persists_resolved_run_before_effectiveness_receipt(tmp_path: Path) -> None:
    module = _load_hook_stop()
    conn = sqlite3.connect(":memory:")
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('project-aios', 'AIOS', ?, '', 'active')
        """,
        (str(ROOT),),
    )
    conn.execute(
        """
        INSERT INTO sessions (
            id, project_id, tool, started_at, objective, status, cwd,
            summary_candidate_path, handoff_path
        )
        VALUES (
            'session-aios', 'project-aios', 'claude-code', '2026-05-31T00:00:00Z',
            'Fix session effectiveness attribution', 'closed', ?, '/tmp/summary.json',
            '/tmp/handoff.md'
        )
        """,
        (str(ROOT),),
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, session_id, objective, workflow_key, agent_key,
            status, rationale
        )
        VALUES (
            'run-aios', 'project-aios', 'session-aios',
            'Fix session effectiveness attribution',
            'implementation-delivery', 'codex', 'in_progress', 'test'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_invocations (
            id, run_id, backend_key, backend_label, status, handshake_token
        )
        VALUES ('invoke-aios', 'run-aios', 'codex', 'Codex', 'running', 'token')
        """
    )

    module._persist_resolved_run_linkage(
        conn,
        session_id="session-aios",
        linked_run_id="run-aios",
        linked_invocation_id="invoke-aios",
        objective="Fix session effectiveness attribution",
        used_legacy_link=False,
        payload_run_id="run-aios",
        payload_invocation_id="invoke-aios",
    )
    receipt = write_session_effectiveness_receipt(conn, "session-aios", receipt_dir=tmp_path)

    assert receipt is not None
    assert receipt["project_name"] == "AIOS"
    assert receipt["run_id"] == "run-aios"
    assert receipt["invocation_id"] == "invoke-aios"
