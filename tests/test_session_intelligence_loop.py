from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.session_intelligence_loop import (  # noqa: E402
    SessionIntelligenceBackfillOptions,
    SessionIntelligenceOptions,
    ensure_session_intelligence_schema,
    list_session_intelligence_candidates,
    list_session_intelligence_clusters,
    mark_session_intelligence_candidate,
    run_session_intelligence,
    run_session_intelligence_backfill,
)
from services.session_providers.claude import ClaudeProvider  # noqa: E402
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


def _write_claude_session(path: Path, session_id: str, user_text: str, assistant_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "type": "user",
            "timestamp": "2026-06-27T10:00:00Z",
            "cwd": "/Users/jakyeamos/AIOS",
            "message": {"role": "user", "content": user_text},
        },
        {
            "type": "assistant",
            "timestamp": "2026-06-27T10:01:00Z",
            "cwd": "/Users/jakyeamos/AIOS",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4",
                "content": [{"type": "text", "text": assistant_text}],
            },
        },
    ]
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def _write_claude_tool_session(path: Path, session_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [
        {
            "type": "user",
            "timestamp": "2026-06-27T10:00:00Z",
            "cwd": "/Users/jakyeamos/AIOS",
            "sessionId": session_id,
            "message": {"role": "user", "content": "Run the tests."},
        },
        {
            "type": "assistant",
            "timestamp": "2026-06-27T10:01:00Z",
            "cwd": "/Users/jakyeamos/AIOS",
            "sessionId": session_id,
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "Bash",
                        "input": {"command": "pnpm test", "description": "Run tests"},
                    }
                ],
            },
        },
        {
            "type": "user",
            "timestamp": "2026-06-27T10:02:00Z",
            "cwd": "/Users/jakyeamos/AIOS",
            "sessionId": session_id,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "is_error": True,
                        "content": "Process exited with code 1\npytest failed",
                    }
                ],
            },
        },
    ]
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


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


def test_claude_provider_normalizes_bash_tools_commands_and_errors(tmp_path: Path) -> None:
    session_path = tmp_path / "claude" / "-Users-jakyeamos-AIOS" / "claude-session.jsonl"
    _write_claude_tool_session(session_path, "claude-session")
    provider = ClaudeProvider(source_root=tmp_path / "claude", db_path=tmp_path / "aios.db")

    normalized = provider.normalize_session(
        provider.extract_raw_session(provider.discover_sources()[0])
    )

    assert normalized.workspace_path == "/Users/jakyeamos/AIOS"
    assert normalized.commands_run == ["pnpm test"]
    assert normalized.tool_calls[0]["tool"] == "Bash"
    assert normalized.tool_calls[0]["command"] == "pnpm test"
    assert normalized.errors_extracted == ["Process exited with code 1: pytest failed"]


def test_session_intelligence_backfill_classifies_claude_friction(tmp_path: Path) -> None:
    session_path = tmp_path / "claude" / "-Users-jakyeamos-AIOS" / "claude-session.jsonl"
    _write_claude_tool_session(session_path, "claude-session")
    conn = _memory_conn()
    provider = ClaudeProvider(source_root=tmp_path / "claude", db_path=tmp_path / "aios.db")

    result = run_session_intelligence_backfill(
        conn,
        provider=provider,
        options=SessionIntelligenceBackfillOptions(since="all", batch_size=1),
    )

    assert result["summary"]["candidate_count"] == 1
    assert list_session_intelligence_candidates(conn)[0]["lane"] == "friction_tool"


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
    assert result["decision_report_path"] == str(tmp_path / "codex-daily-candidate-decisions.md")
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    decision_report = Path(result["decision_report_path"]).read_text(encoding="utf-8")
    assert secret not in report
    assert secret not in decision_report
    assert "[REDACTED:api_key]" in report
    assert "# Codex Daily Candidate Decisions" in decision_report
    assert "## friction_tool" in decision_report
    assert "## workflow_skill" in decision_report
    assert "## impact_idea" in decision_report
    assert "Review Queue" in decision_report
    assert "Anecdotal setting:" in decision_report
    assert "When a Codex run repeatedly hits this friction" in decision_report
    assert "source sessions:" not in decision_report
    assert "[REDACTED:api_key]" in decision_report


def test_session_intelligence_decision_report_includes_full_pending_backlog(
    tmp_path: Path,
) -> None:
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
    ensure_session_intelligence_schema(conn)
    conn.execute(
        """
        INSERT INTO session_intelligence_candidates (
          id, lane, title, summary, impact_score, confidence, status,
          source_sessions_json, redacted_evidence_json, proposed_artifact_type,
          proposed_next_action, review_note, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "session-intel-backlog-only",
            "friction_tool",
            "Stored backlog-only candidate",
            "Existing pending work should stay visible after a smaller latest scan.",
            8,
            0.7,
            "pending_review",
            json.dumps(["older-session"]),
            json.dumps([{"session_id": "older-session", "summary": "older evidence"}]),
            "deterministic_tool_candidate",
            "Review whether this backlog item still deserves promotion.",
            None,
            "2026-06-26T10:00:00+00:00",
            "2026-06-26T10:00:00+00:00",
        ),
    )
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")

    result = run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="last", write_report=True, report_root=tmp_path),
    )

    decision_report = Path(result["decision_report_path"]).read_text(encoding="utf-8")
    assert "## New in latest scan" in decision_report
    assert "## All pending candidates" in decision_report
    assert "- latest pending candidates: 1" in decision_report
    assert "- all pending candidates: 2" in decision_report
    assert "Stored backlog-only candidate" in decision_report


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


def test_session_intelligence_backfill_batches_and_resumes_from_cursors(
    tmp_path: Path,
) -> None:
    sessions_root = tmp_path / "sessions"
    for index in range(3):
        _write_codex_rollout(
            sessions_root / f"2026/06/27/rollout-2026-06-27T10-0{index}-00-session-{index}.jsonl",
            [
                _session_meta(f"session-{index}"),
                _function_call(f"pnpm test --filter package-{index}"),
                _function_output("Process exited with code 1\npytest failed"),
            ],
        )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")
    options = SessionIntelligenceBackfillOptions(
        since="all",
        batch_size=2,
        write_report=True,
        report_root=tmp_path / "reports",
    )

    first = run_session_intelligence_backfill(conn, provider=provider, options=options)
    second = run_session_intelligence_backfill(conn, provider=provider, options=options)

    assert first["summary"]["eligible_source_count"] == 3
    assert first["summary"]["processed_source_count"] == 3
    assert first["summary"]["skipped_source_count"] == 0
    assert first["summary"]["batch_count"] == 2
    assert first["summary"]["candidate_count"] == 2
    assert len(first["report_paths"]) == 2
    assert all(Path(path).exists() for path in first["report_paths"])
    assert second["summary"]["eligible_source_count"] == 3
    assert second["summary"]["processed_source_count"] == 0
    assert second["summary"]["skipped_source_count"] == 3
    assert second["summary"]["batch_count"] == 0

    first_source = sorted(sessions_root.glob("**/*.jsonl"))[0]
    first_source.touch()
    third = run_session_intelligence_backfill(conn, provider=provider, options=options)

    assert third["summary"]["processed_source_count"] == 0
    assert third["summary"]["skipped_source_count"] == 3
    assert third["summary"]["batch_count"] == 1


def test_session_intelligence_backfill_merges_same_candidate_across_batches(
    tmp_path: Path,
) -> None:
    sessions_root = tmp_path / "sessions"
    for index in range(3):
        _write_codex_rollout(
            sessions_root / f"2026/06/27/rollout-2026-06-27T10-0{index}-00-session-{index}.jsonl",
            [
                _session_meta(f"session-{index}"),
                _function_call("pnpm test"),
                _function_output("Process exited with code 1\npytest failed"),
            ],
        )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")

    run_session_intelligence_backfill(
        conn,
        provider=provider,
        options=SessionIntelligenceBackfillOptions(since="all", batch_size=1),
    )
    candidates = list_session_intelligence_candidates(conn)

    assert len(candidates) == 1
    assert candidates[0]["source_sessions"] == ["session-0", "session-1", "session-2"]
    assert len(candidates[0]["redacted_evidence"]) == 3


def test_session_intelligence_groups_friction_by_intent_not_exact_command(
    tmp_path: Path,
) -> None:
    sessions_root = tmp_path / "sessions"
    for index, command in enumerate(
        ("git status --short", "git -C /repo status --short", "git diff --stat")
    ):
        _write_codex_rollout(
            sessions_root / f"2026/06/27/rollout-2026-06-27T10-0{index}-00-session-{index}.jsonl",
            [
                _session_meta(f"session-{index}"),
                _function_call(command),
                _function_output("Process exited with code 1\nnot a git repository"),
            ],
        )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")

    run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", lane="friction_tool"),
    )
    candidates = list_session_intelligence_candidates(conn)

    assert len(candidates) == 1
    assert candidates[0]["title"] == "Deterministic helper for repo state inspection"
    assert candidates[0]["source_sessions"] == ["session-0", "session-1", "session-2"]
    assert "git status --short" in candidates[0]["redacted_evidence"][0]["summary"]
    assert "git -C /repo status --short" in candidates[0]["redacted_evidence"][1]["summary"]
    assert "git diff --stat" in candidates[0]["redacted_evidence"][2]["summary"]


def test_session_intelligence_mines_successful_command_sequences_as_workflows(
    tmp_path: Path,
) -> None:
    sessions_root = tmp_path / "sessions"
    for index in range(2):
        _write_codex_rollout(
            sessions_root / f"2026/06/27/rollout-2026-06-27T10-0{index}-00-session-{index}.jsonl",
            [
                _session_meta(f"session-{index}"),
                _function_call("rg -n session_intelligence services tests"),
                _function_output("services/session_intelligence_loop.py:1:match"),
                _function_call("uv run pytest tests/test_session_intelligence_loop.py -q"),
                _function_output("12 passed"),
                _message("assistant", "Implemented the change, verified tests, and updated truth."),
            ],
        )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")

    run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", lane="workflow_skill"),
    )
    candidates = list_session_intelligence_candidates(conn)

    assert len(candidates) == 1
    assert candidates[0]["lane"] == "workflow_skill"
    assert candidates[0]["title"] == "Reusable implementation verification workflow"
    assert candidates[0]["proposed_artifact_type"] == "skill_or_workflow_candidate"


def test_session_intelligence_clusters_candidates_for_triage(tmp_path: Path) -> None:
    sessions_root = tmp_path / "sessions"
    for index, command in enumerate(("git status --short", "git diff --stat", "pnpm test")):
        _write_codex_rollout(
            sessions_root / f"2026/06/27/rollout-2026-06-27T10-0{index}-00-session-{index}.jsonl",
            [
                _session_meta(f"session-{index}"),
                _function_call(command),
                _function_output("Process exited with code 1\nfailed"),
            ],
        )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")
    run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", lane="friction_tool"),
    )

    clusters = list_session_intelligence_clusters(conn, status="pending_review", lane="all")

    assert clusters[0]["cluster_key"] == "friction_tool:repo_state_inspection"
    assert clusters[0]["candidate_count"] == 1
    assert clusters[0]["source_session_count"] == 2
    assert clusters[0]["recommended_review_action"] == "Review as a deterministic tool candidate."
    assert clusters[1]["cluster_key"] == "friction_tool:javascript_package_quality"


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
    events = conn.execute("SELECT * FROM session_intelligence_review_events").fetchall()
    assert len(events) == 1
    assert events[0]["candidate_id"] == "candidate-1"
    assert events[0]["status"] == "approved"


def test_session_intelligence_cli_parser_accepts_run_candidates_and_mark() -> None:
    import services.aios_cli as aios_cli

    parser = aios_cli.create_parser()

    run_args = parser.parse_args(["session-intel", "run", "--provider", "codex", "--since", "last"])
    candidates_args = parser.parse_args(
        ["session-intel", "candidates", "--status", "pending_review", "--lane", "all"]
    )
    clusters_args = parser.parse_args(
        ["session-intel", "clusters", "--status", "pending_review", "--lane", "all"]
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
    backfill_args = parser.parse_args(
        [
            "session-intel",
            "backfill",
            "--provider",
            "all",
            "--since",
            "all",
            "--batch-size",
            "250",
            "--write-report",
        ]
    )

    assert run_args.session_intel_command == "run"
    assert candidates_args.session_intel_command == "candidates"
    assert clusters_args.session_intel_command == "clusters"
    assert mark_args.session_intel_command == "mark"
    assert backfill_args.session_intel_command == "backfill"
    assert backfill_args.provider == "all"


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
    clusters = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(session_intel_command="clusters", status="all", lane="all", limit=1),
    )

    assert run_payload["summary"]["candidate_count"] == 1
    assert Path(run_payload["report_path"]).exists()
    assert listed["count"] == 1
    assert marked["status"] == "observed"
    assert clusters["count"] == 1
    assert clusters["total_count"] == 1
    assert clusters["clusters"][0]["status_counts"] == {"observed": 1}
    assert "redacted_evidence" not in clusters["clusters"][0]["top_candidates"][0]


def test_session_intelligence_cli_backfill_supports_codex_and_claude(
    tmp_path: Path,
) -> None:
    import services.aios_cli as aios_cli

    codex_root = tmp_path / "codex"
    claude_root = tmp_path / "claude"
    _write_codex_rollout(
        codex_root / "2026/06/27/rollout-2026-06-27T10-00-00-codex-session.jsonl",
        [
            _session_meta("codex-session"),
            _function_call("pnpm test"),
            _function_output("Process exited with code 1\npytest failed"),
        ],
    )
    _write_claude_session(
        claude_root / "-Users-jakyeamos-AIOS" / "claude-session.jsonl",
        "claude-session",
        "Highest leverage impact idea: backfill Claude and Codex transcripts.",
        "Keep generated candidates review-gated.",
    )
    conn = _memory_conn()

    payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="backfill",
            provider="all",
            since="all",
            lane="all",
            batch_size=1,
            write_report=False,
            source_root=None,
            codex_source_root=str(codex_root),
            claude_source_root=str(claude_root),
            report_root=str(tmp_path / "reports"),
        ),
    )

    assert payload["summary"]["provider_count"] == 2
    assert payload["summary"]["processed_source_count"] == 2
    assert {result["provider"] for result in payload["providers"]} == {"codex", "claude"}
    assert len(list_session_intelligence_candidates(conn)) == 2


def test_session_intelligence_cli_backfill_persists_rows(tmp_path: Path, capsys) -> None:
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
    db_path = tmp_path / "aios.db"
    db_path.touch()

    exit_code = aios_cli.run_cli(
        [
            "--db",
            str(db_path),
            "session-intel",
            "backfill",
            "--provider",
            "codex",
            "--source-root",
            str(sessions_root),
            "--batch-size",
            "1",
        ]
    )
    capsys.readouterr()

    with sqlite3.connect(db_path) as conn:
        run_count = conn.execute("SELECT COUNT(*) FROM session_intelligence_runs").fetchone()[0]
        candidate_count = conn.execute(
            "SELECT COUNT(*) FROM session_intelligence_candidates"
        ).fetchone()[0]

    assert exit_code == 0
    assert run_count == 1
    assert candidate_count == 1
