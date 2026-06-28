from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.session_intelligence_loop import (  # noqa: E402
    SessionIntelligenceOptions,
    ensure_session_intelligence_schema,
    list_session_intelligence_candidates,
    mark_session_intelligence_candidate,
    run_session_intelligence,
)
from services.session_providers.codex import CodexProvider  # noqa: E402


def _memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _write_codex_rollout(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(line, sort_keys=True) for line in lines) + "\n",
        encoding="utf-8",
    )


def _message(role: str, text: str, *, phase: str = "final_answer") -> dict:
    return {
        "timestamp": "2026-06-27T10:00:00Z",
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "phase": phase,
            "content": [{"type": "input_text" if role == "user" else "output_text", "text": text}],
        },
    }


def _session_meta(session_id: str, *, cwd: str = "/repo") -> dict:
    return {
        "timestamp": "2026-06-27T10:00:00Z",
        "type": "session_meta",
        "payload": {
            "id": session_id,
            "session_id": session_id,
            "timestamp": "2026-06-27T10:00:00Z",
            "cwd": cwd,
            "model_provider": "openai",
            "source": {"thread": "codex"},
        },
    }


def _function_call(command: str) -> dict:
    return {
        "timestamp": "2026-06-27T10:01:00Z",
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "exec_command",
            "arguments": json.dumps({"cmd": command, "workdir": "/repo"}),
        },
    }


def _function_output(output: str) -> dict:
    return {
        "timestamp": "2026-06-27T10:02:00Z",
        "type": "response_item",
        "payload": {
            "type": "function_call_output",
            "output": output,
        },
    }


def test_codex_provider_normalizes_tools_commands_errors_and_cwd(tmp_path: Path) -> None:
    rollout = tmp_path / "sessions" / "rollout-2026-06-27T10-00-00-session-1.jsonl"
    _write_codex_rollout(
        rollout,
        [
            _session_meta("session-1", cwd="/Users/jakyeamos/AIOS"),
            _message("user", "Please run the quality gate."),
            _function_call("pnpm test"),
            _function_output("Process exited with code 1\npytest failed"),
            _message("assistant", "The test failed because the quality gate is missing."),
        ],
    )
    provider = CodexProvider(source_root=tmp_path / "sessions", db_path=tmp_path / "aios.db")

    normalized = provider.normalize_session(
        provider.extract_raw_session(provider.discover_sources()[0])
    )

    assert normalized.workspace_path == "/Users/jakyeamos/AIOS"
    assert normalized.commands_run == ["pnpm test"]
    assert normalized.tool_calls[0]["tool"] == "exec_command"
    assert normalized.errors_extracted == ["Process exited with code 1: pytest failed"]
    assert normalized.provider_metadata["model_provider"] == "openai"


def test_session_intelligence_classifies_lanes_and_redacts_report(tmp_path: Path) -> None:
    sessions_root = tmp_path / "sessions"
    secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
    for index in range(2):
        _write_codex_rollout(
            sessions_root / f"2026/06/27/rollout-2026-06-27T10-0{index}-00-session-{index}.jsonl",
            [
                _session_meta(f"session-{index}"),
                _message(
                    "user",
                    f"Highest leverage impact idea: automate transcript review. Secret {secret}",
                ),
                _function_call("pnpm test"),
                _function_output("Process exited with code 1\npytest failed"),
                _message(
                    "assistant",
                    "Workflow completed cleanly: inspect sessions, run tests, write review-gated report.",
                ),
            ],
        )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")

    result = run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", write_report=True, report_root=tmp_path),
    )

    lanes = {candidate["lane"] for candidate in result["candidates"]}
    assert {"friction_tool", "workflow_skill", "impact_idea"}.issubset(lanes)
    assert result["summary"]["candidate_count"] >= 3
    assert result["report_path"]
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert secret not in report
    assert "[REDACTED:api_key]" in report


def test_session_intelligence_deduplicates_candidates_across_runs(tmp_path: Path) -> None:
    sessions_root = tmp_path / "sessions"
    _write_codex_rollout(
        sessions_root / "2026/06/27/rollout-2026-06-27T10-00-00-session-1.jsonl",
        [
            _session_meta("session-1"),
            _function_call("pnpm test"),
            _function_output("Process exited with code 1\npytest failed"),
        ],
    )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")
    options = SessionIntelligenceOptions(since="all", write_report=False, report_root=tmp_path)

    first = run_session_intelligence(conn, provider=provider, options=options)
    second = run_session_intelligence(conn, provider=provider, options=options)

    assert first["summary"]["candidate_count"] == 1
    assert second["summary"]["candidate_count"] == 1
    assert len(list_session_intelligence_candidates(conn)) == 1


def test_session_intelligence_lists_and_marks_candidates(tmp_path: Path) -> None:
    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    provider = CodexProvider(source_root=tmp_path / "missing", db_path=tmp_path / "aios.db")
    run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", write_report=False, report_root=tmp_path),
    )
    conn.execute(
        """
        INSERT INTO session_intelligence_candidates (
          id, lane, title, summary, impact_score, confidence, status, source_sessions_json,
          redacted_evidence_json, proposed_artifact_type, proposed_next_action, created_at, updated_at
        )
        VALUES (
          'candidate-1', 'impact_idea', 'Impact idea', 'Review transcripts', 5, 0.8,
          'pending_review', '[]', '[]', 'review_note', 'Review this candidate', 'now', 'now'
        )
        """
    )

    pending = list_session_intelligence_candidates(conn, status="pending_review", lane="all")
    updated = mark_session_intelligence_candidate(
        conn,
        candidate_id="candidate-1",
        status="approved",
        note="Approved for later implementation.",
    )

    assert pending[0]["id"] == "candidate-1"
    assert updated["status"] == "approved"
    assert updated["review_note"] == "Approved for later implementation."


def test_session_intelligence_cli_parser_accepts_run_candidates_and_mark() -> None:
    import services.aios_cli as aios_cli

    parser = aios_cli.create_parser()

    run_args = parser.parse_args(["session-intel", "run", "--provider", "codex", "--since", "last"])
    candidates_args = parser.parse_args(
        ["session-intel", "candidates", "--status", "pending_review", "--lane", "all"]
    )
    mark_args = parser.parse_args(
        [
            "session-intel",
            "mark",
            "--candidate-id",
            "candidate-1",
            "--status",
            "approved",
            "--note",
            "reviewed",
        ]
    )

    assert run_args.session_intel_command == "run"
    assert candidates_args.session_intel_command == "candidates"
    assert mark_args.session_intel_command == "mark"


def test_session_intelligence_cli_payloads_run_list_and_mark(tmp_path: Path) -> None:
    import services.aios_cli as aios_cli

    sessions_root = tmp_path / "sessions"
    _write_codex_rollout(
        sessions_root / "2026/06/27/rollout-2026-06-27T10-00-00-session-1.jsonl",
        [
            _session_meta("session-1"),
            _function_call("pnpm test"),
            _function_output("Process exited with code 1\npytest failed"),
        ],
    )
    conn = _memory_conn()

    run_payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="run",
            provider="codex",
            since="all",
            lane="all",
            write_report=True,
            source_root=str(sessions_root),
            report_root=str(tmp_path),
        ),
    )
    listed = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(session_intel_command="candidates", status="pending_review", lane="all"),
    )
    marked = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="mark",
            candidate_id=listed["candidates"][0]["id"],
            status="observed",
            note="keep watching",
        ),
    )

    assert run_payload["summary"]["candidate_count"] == 1
    assert Path(run_payload["report_path"]).exists()
    assert listed["count"] == 1
    assert marked["status"] == "observed"
