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
    implement_session_intelligence_candidates,
    list_session_intelligence_candidates,
    list_session_intelligence_clusters,
    list_session_intelligence_implementations,
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


def _insert_helper_implementation(conn: sqlite3.Connection, *, family: str) -> None:
    conn.execute(
        """
        INSERT INTO session_intelligence_implementations (
          id, lane, helper_family, candidate_ids_json, candidate_count,
          implementation_status, telemetry_status, removal_status, removal_reason,
          implemented_artifact_type, implemented_artifact_ref, created_at, updated_at
        )
        VALUES (?, 'friction_tool', ?, '["candidate-1"]', 1, 'implemented',
          'awaiting_telemetry', 'monitor', 'Track usage before keeping.',
          'helper_family_preset', ?, 'now', 'now')
        """,
        (
            f"session-intel-implementation-friction_tool-{family}",
            family,
            f"session-intel-helper-family:{family}",
        ),
    )


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
    assert "Helper strategy:" in decision_report
    assert "- helper family:" in decision_report
    assert "- telemetry plan:" in decision_report
    assert "- removal review:" in decision_report
    assert "- reuse recommendation:" in decision_report
    assert "- dedicated helper:" in decision_report
    assert "Prefer a shared helper family or preset over a one-off script." in decision_report
    assert "## Implementation Telemetry Contract" in decision_report
    assert "Measure whether implemented candidates reduce repeated friction" in decision_report
    assert "## Removal Candidates" in decision_report
    assert "No implemented candidate telemetry is available yet." in decision_report
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


def test_session_intelligence_helper_strategy_uses_reusable_families(tmp_path: Path) -> None:
    sessions_root = tmp_path / "sessions"
    _write_codex_rollout(
        sessions_root / "2026/06/27/rollout-2026-06-27T10-00-00-session-1.jsonl",
        [
            _session_meta("session-1"),
            _function_call("vercel deploy --prod --yes"),
            _function_output("Process exited with code 1\ndeployment failed"),
        ],
    )
    conn = _memory_conn()
    provider = CodexProvider(source_root=sessions_root, db_path=tmp_path / "aios.db")

    result = run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", write_report=True, report_root=tmp_path),
    )

    decision_report = Path(result["decision_report_path"]).read_text(encoding="utf-8")
    assert "- helper family: deployment_flow" in decision_report
    assert "Add this under the deployment_flow family" in decision_report
    assert "- helper family: artifact_probe" not in decision_report


def test_session_intelligence_rolls_up_friction_candidates_by_helper_family(
    tmp_path: Path,
) -> None:
    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    conn.executemany(
        """
        INSERT INTO session_intelligence_candidates (
          id, lane, title, summary, impact_score, confidence, status,
          source_sessions_json, redacted_evidence_json, proposed_artifact_type,
          proposed_next_action, review_note, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "session-intel-repo-state-1",
                "friction_tool",
                "Repeated git status inspection failed",
                "Codex kept rerunning git status checks before closeout.",
                8,
                0.8,
                "pending_review",
                json.dumps(["session-1"]),
                json.dumps([{"session_id": "session-1", "summary": "git status --short failed"}]),
                "deterministic_tool_candidate",
                "Review whether a repo state preset should cover git status checks.",
                None,
                "2026-06-30T10:00:00+00:00",
                "2026-06-30T10:00:00+00:00",
            ),
            (
                "session-intel-repo-state-2",
                "friction_tool",
                "Repeated git diff inspection failed",
                "Codex kept rerunning git diff checks before closeout.",
                7,
                0.7,
                "pending_review",
                json.dumps(["session-2"]),
                json.dumps([{"session_id": "session-2", "summary": "git diff --stat failed"}]),
                "deterministic_tool_candidate",
                "Review whether a repo state preset should cover git diff checks.",
                None,
                "2026-06-30T10:01:00+00:00",
                "2026-06-30T10:01:00+00:00",
            ),
        ],
    )
    provider = CodexProvider(source_root=tmp_path / "missing", db_path=tmp_path / "aios.db")

    result = run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", write_report=True, report_root=tmp_path),
    )

    decision_report = Path(result["decision_report_path"]).read_text(encoding="utf-8")
    assert "#### helper family: repo_state" in decision_report
    assert decision_report.count("#### helper family: repo_state") == 1
    assert "- candidate count: 2" in decision_report
    assert "##### Repeated git status inspection failed" in decision_report
    assert "##### Repeated git diff inspection failed" in decision_report
    assert "Add this under the repo_state family" in decision_report
    assert "record family-level helper telemetry" in decision_report
    assert "promote the family as a removal candidate" in decision_report


def test_session_intelligence_implements_pending_candidates_as_tracked_helper_families(
    tmp_path: Path,
) -> None:
    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    conn.executemany(
        """
        INSERT INTO session_intelligence_candidates (
          id, lane, title, summary, impact_score, confidence, status,
          source_sessions_json, redacted_evidence_json, proposed_artifact_type,
          proposed_next_action, review_note, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "session-intel-repo-state-1",
                "friction_tool",
                "Repeated git status inspection failed",
                "Codex kept rerunning git status checks before closeout.",
                8,
                0.8,
                "pending_review",
                json.dumps(["session-1"]),
                json.dumps([{"session_id": "session-1", "summary": "git status --short failed"}]),
                "deterministic_tool_candidate",
                "Review whether a repo state preset should cover git status checks.",
                None,
                "2026-06-30T10:00:00+00:00",
                "2026-06-30T10:00:00+00:00",
            ),
            (
                "session-intel-repo-state-2",
                "friction_tool",
                "Repeated git diff inspection failed",
                "Codex kept rerunning git diff checks before closeout.",
                7,
                0.7,
                "pending_review",
                json.dumps(["session-2"]),
                json.dumps([{"session_id": "session-2", "summary": "git diff --stat failed"}]),
                "deterministic_tool_candidate",
                "Review whether a repo state preset should cover git diff checks.",
                None,
                "2026-06-30T10:01:00+00:00",
                "2026-06-30T10:01:00+00:00",
            ),
            (
                "session-intel-package-1",
                "friction_tool",
                "Repeated package quality command failed",
                "Codex kept rerunning pnpm checks before closeout.",
                6,
                0.7,
                "pending_review",
                json.dumps(["session-3"]),
                json.dumps([{"session_id": "session-3", "summary": "pnpm test failed"}]),
                "deterministic_tool_candidate",
                "Review whether package quality should use a shared preset.",
                None,
                "2026-06-30T10:02:00+00:00",
                "2026-06-30T10:02:00+00:00",
            ),
        ],
    )

    result = implement_session_intelligence_candidates(
        conn,
        status="pending_review",
        lane="all",
        candidate_ids=["session-intel-repo-state-1", "session-intel-package-1"],
        actor_note="Human approved implementation with removal tracking.",
    )

    implementations = list_session_intelligence_implementations(conn)
    candidates = list_session_intelligence_candidates(conn, status="implemented", lane="all")
    pending = list_session_intelligence_candidates(conn, status="pending_review", lane="all")
    assert result["candidate_count"] == 2
    assert result["implementation_count"] == 2
    assert [item["helper_family"] for item in implementations] == [
        "package_check",
        "repo_state",
    ]
    assert implementations[0]["candidate_count"] == 1
    assert implementations[0]["telemetry_status"] == "awaiting_telemetry"
    assert implementations[0]["removal_status"] == "monitor"
    assert (
        implementations[1]["implemented_artifact_ref"] == "session-intel-helper-family:repo_state"
    )
    assert {candidate["status"] for candidate in candidates} == {"implemented"}
    assert {candidate["id"] for candidate in pending} == {"session-intel-repo-state-2"}
    assert implementations[1]["candidate_ids"] == ["session-intel-repo-state-1"]

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
            "session-intel-repo-state-3",
            "friction_tool",
            "Repeated worktree inspection failed",
            "Codex kept rerunning worktree checks before closeout.",
            6,
            0.7,
            "pending_review",
            json.dumps(["session-4"]),
            json.dumps([{"session_id": "session-4", "summary": "git worktree list failed"}]),
            "deterministic_tool_candidate",
            "Review whether a repo state preset should cover worktree checks.",
            None,
            "2026-06-30T10:03:00+00:00",
            "2026-06-30T10:03:00+00:00",
        ),
    )

    implement_session_intelligence_candidates(
        conn,
        status="pending_review",
        lane="all",
        candidate_ids=["session-intel-repo-state-3"],
        actor_note="Human approved another repo-state candidate.",
    )

    updated_implementations = list_session_intelligence_implementations(conn)
    repo_state = updated_implementations[0]
    assert repo_state["helper_family"] == "repo_state"
    assert repo_state["candidate_count"] == 2
    assert repo_state["candidate_ids"] == [
        "session-intel-repo-state-1",
        "session-intel-repo-state-3",
    ]


def test_session_intelligence_decision_report_lists_tracked_implemented_helpers(
    tmp_path: Path,
) -> None:
    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    conn.execute(
        """
        INSERT INTO session_intelligence_implementations (
          id, lane, helper_family, candidate_ids_json, candidate_count,
          implementation_status, telemetry_status, removal_status, removal_reason,
          implemented_artifact_type, implemented_artifact_ref, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "session-intel-implementation-friction_tool-repo_state",
            "friction_tool",
            "repo_state",
            json.dumps(["session-intel-repo-state-1"]),
            1,
            "implemented",
            "awaiting_telemetry",
            "monitor",
            "Track usage before deciding whether to keep or remove this helper family.",
            "helper_family_preset",
            "session-intel-helper-family:repo_state",
            "2026-06-30T10:00:00+00:00",
            "2026-06-30T10:00:00+00:00",
        ),
    )
    conn.executemany(
        """
        INSERT INTO session_intelligence_helper_telemetry (
          id, implementation_id, helper_family, candidate_ids_json, invoked_at, status,
          latency_ms, input_shape_json, error_type, error_message, caller_surface,
          run_id, session_id, task_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "telemetry-1",
                "session-intel-implementation-friction_tool-repo_state",
                "repo_state",
                json.dumps(["session-intel-repo-state-1"]),
                "2026-06-30T10:01:00+00:00",
                "success",
                10,
                "{}",
                None,
                None,
                "session-intel helper run",
                None,
                None,
                None,
            ),
            (
                "telemetry-2",
                "session-intel-implementation-friction_tool-repo_state",
                "repo_state",
                json.dumps(["session-intel-repo-state-1"]),
                "2026-06-30T10:02:00+00:00",
                "failure",
                30,
                "{}",
                "RuntimeError",
                "failed",
                "session-intel helper run",
                None,
                None,
                None,
            ),
        ],
    )
    provider = CodexProvider(source_root=tmp_path / "missing", db_path=tmp_path / "aios.db")

    result = run_session_intelligence(
        conn,
        provider=provider,
        options=SessionIntelligenceOptions(since="all", write_report=True, report_root=tmp_path),
    )

    decision_report = Path(result["decision_report_path"]).read_text(encoding="utf-8")
    assert "## Removal Candidates" in decision_report
    assert "### monitored implemented helpers" in decision_report
    assert "- repo_state: monitor; awaiting_telemetry; candidates covered: 1" in decision_report
    assert "invocations 2; successes 1; failures 1; bypasses 0; median latency 20ms" in decision_report
    assert "telemetry candidate coverage: 1" in decision_report
    assert "session-intel-helper-family:repo_state" in decision_report


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
    implement_args = parser.parse_args(
        [
            "session-intel",
            "implement",
            "--status",
            "pending_review",
            "--lane",
            "all",
            "--candidate-id",
            "candidate-1",
            "--candidate-id",
            "candidate-2",
        ]
    )
    mark_args = parser.parse_args(
        [
            "session-intel",
            "mark",
            "--candidate-id",
            "candidate-1",
            "--status",
            "implemented",
            "--note",
            "reviewed",
        ]
    )
    helper_list_args = parser.parse_args(["session-intel", "helper", "list"])
    helper_run_args = parser.parse_args(
        [
            "session-intel",
            "helper",
            "run",
            "--family",
            "doc_excerpt",
            "--path",
            "README.md",
            "--start-line",
            "1",
            "--end-line",
            "20",
        ]
    )
    helper_bypass_args = parser.parse_args(
        [
            "session-intel",
            "helper",
            "bypass",
            "--family",
            "doc_excerpt",
            "--reason",
            "manual path was faster",
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
    daily_codex_args = parser.parse_args(["session-intel", "daily-codex"])

    assert run_args.session_intel_command == "run"
    assert candidates_args.session_intel_command == "candidates"
    assert clusters_args.session_intel_command == "clusters"
    assert implement_args.session_intel_command == "implement"
    assert implement_args.candidate_id == ["candidate-1", "candidate-2"]
    assert mark_args.session_intel_command == "mark"
    assert helper_list_args.session_intel_command == "helper"
    assert helper_list_args.session_intel_helper_command == "list"
    assert helper_run_args.session_intel_command == "helper"
    assert helper_run_args.session_intel_helper_command == "run"
    assert helper_run_args.family == "doc_excerpt"
    assert helper_bypass_args.session_intel_helper_command == "bypass"
    assert helper_bypass_args.reason == "manual path was faster"
    assert backfill_args.session_intel_command == "backfill"
    assert backfill_args.provider == "all"
    assert daily_codex_args.session_intel_command == "daily-codex"


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
    implemented = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="implement",
            status="pending_review",
            lane="all",
            note="Human approved implementation.",
        ),
    )
    implemented_list = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(session_intel_command="candidates", status="implemented", lane="all"),
    )
    marked = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="mark",
            candidate_id=implemented_list["candidates"][0]["id"],
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
    assert implemented["candidate_count"] == 1
    assert implemented["implementation_count"] == 1
    assert implemented["implementations"][0]["telemetry_status"] == "awaiting_telemetry"
    assert implemented_list["count"] == 1
    assert marked["status"] == "observed"
    assert clusters["count"] == 1
    assert clusters["total_count"] == 1
    assert clusters["clusters"][0]["status_counts"] == {"observed": 1}
    assert "redacted_evidence" not in clusters["clusters"][0]["top_candidates"][0]


def test_session_intelligence_daily_codex_wrapper_returns_report_paths_and_review_only(
    tmp_path: Path,
) -> None:
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

    payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="daily-codex",
            source_root=str(sessions_root),
            report_root=str(tmp_path),
        ),
    )

    assert payload["provider"] == "codex"
    assert payload["scanned_range"] == "last"
    assert payload["review_only"] is True
    assert payload["wrapped_command"] == [
        ".venv/bin/python",
        "/Users/jakyeamos/AIOS/bin/aios.py",
        "session-intel",
        "run",
        "--provider",
        "codex",
        "--since",
        "last",
        "--write-report",
        "--json",
    ]
    assert payload["summary"]["candidate_count"] == 1
    assert payload["report_paths"] == {
        "markdown": payload["report_path"],
        "json": payload["report_json_path"],
        "decision": payload["decision_report_path"],
    }
    assert all(Path(path).exists() for path in payload["report_paths"].values())
    candidates = list_session_intelligence_candidates(conn, status="pending_review", lane="all")
    implementations = list_session_intelligence_implementations(conn)
    review_events = conn.execute("SELECT * FROM session_intelligence_review_events").fetchall()
    run_row = conn.execute(
        "SELECT provider, scanned_range FROM session_intelligence_runs"
    ).fetchone()
    assert len(candidates) == 1
    assert candidates[0]["status"] == "pending_review"
    assert implementations == []
    assert review_events == []
    assert dict(run_row) == {"provider": "codex", "scanned_range": "last"}


def test_session_intelligence_helper_list_returns_adopted_families() -> None:
    import services.aios_cli as aios_cli

    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    conn.execute(
        """
        INSERT INTO session_intelligence_implementations (
          id, lane, helper_family, candidate_ids_json, candidate_count,
          implementation_status, telemetry_status, removal_status, removal_reason,
          implemented_artifact_type, implemented_artifact_ref, created_at, updated_at
        )
        VALUES (
          'session-intel-implementation-friction_tool-doc_excerpt',
          'friction_tool',
          'doc_excerpt',
          '["candidate-1"]',
          1,
          'implemented',
          'awaiting_telemetry',
          'monitor',
          'Track usage before keeping.',
          'helper_family_preset',
          'session-intel-helper-family:doc_excerpt',
          'now',
          'now'
        )
        """
    )

    payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(session_intel_command="helper", session_intel_helper_command="list"),
    )

    assert payload["count"] == 1
    assert payload["helpers"][0]["family"] == "doc_excerpt"
    assert payload["helpers"][0]["candidate_count"] == 1
    assert payload["helpers"][0]["implemented"] is True


def test_session_intelligence_helper_run_records_success_telemetry(tmp_path: Path) -> None:
    import services.aios_cli as aios_cli

    target = tmp_path / "notes.md"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    _insert_helper_implementation(conn, family="doc_excerpt")

    payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="helper",
            session_intel_helper_command="run",
            family="doc_excerpt",
            path=str(target),
            repo=None,
            start_line=1,
            end_line=1,
        ),
    )

    telemetry_rows = conn.execute(
        "SELECT helper_family, status, input_shape_json FROM session_intelligence_helper_telemetry"
    ).fetchall()
    implementation = list_session_intelligence_implementations(conn)[0]
    assert payload["telemetry"]["status"] == "success"
    assert len(telemetry_rows) == 1
    assert telemetry_rows[0]["helper_family"] == "doc_excerpt"
    assert telemetry_rows[0]["status"] == "success"
    assert json.loads(telemetry_rows[0]["input_shape_json"])["path_suffix"] == ".md"
    assert implementation["telemetry_status"] == "active"
    assert implementation["removal_status"] == "monitor"


def test_session_intelligence_helper_run_records_failure_telemetry(tmp_path: Path) -> None:
    import services.aios_cli as aios_cli

    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    _insert_helper_implementation(conn, family="doc_excerpt")

    try:
        aios_cli._session_intel_payload(
            conn,
            argparse.Namespace(
                session_intel_command="helper",
                session_intel_helper_command="run",
                family="doc_excerpt",
                path=str(tmp_path / "missing.md"),
                repo=None,
                start_line=1,
                end_line=1,
            ),
        )
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing helper input should fail")

    telemetry_row = conn.execute(
        "SELECT status, error_type FROM session_intelligence_helper_telemetry"
    ).fetchone()
    implementation = list_session_intelligence_implementations(conn)[0]
    assert telemetry_row["status"] == "failure"
    assert telemetry_row["error_type"] == "FileNotFoundError"
    assert implementation["telemetry_status"] == "insufficient_telemetry"
    assert implementation["removal_status"] == "monitor"


def test_session_intelligence_helper_bypass_records_removal_ready_telemetry() -> None:
    import services.aios_cli as aios_cli

    conn = _memory_conn()
    ensure_session_intelligence_schema(conn)
    _insert_helper_implementation(conn, family="doc_excerpt")

    for _index in range(3):
        aios_cli._session_intel_payload(
            conn,
            argparse.Namespace(
                session_intel_command="helper",
                session_intel_helper_command="bypass",
                family="doc_excerpt",
                reason="manual command was faster",
            ),
        )

    implementation = list_session_intelligence_implementations(conn)[0]
    telemetry_count = conn.execute(
        "SELECT COUNT(*) FROM session_intelligence_helper_telemetry WHERE status = 'bypass'"
    ).fetchone()[0]
    assert telemetry_count == 3
    assert implementation["telemetry_status"] == "removal_review_ready"
    assert implementation["removal_status"] == "removal_candidate"


def test_session_intelligence_doc_excerpt_helper_reads_bounded_lines(tmp_path: Path) -> None:
    import services.aios_cli as aios_cli

    target = tmp_path / "notes.md"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    conn = _memory_conn()

    payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="helper",
            session_intel_helper_command="run",
            family="doc_excerpt",
            path=str(target),
            repo=None,
            start_line=2,
            end_line=3,
        ),
    )

    assert payload["family"] == "doc_excerpt"
    assert payload["path"] == str(target)
    assert payload["line_count"] == 2
    assert payload["lines"] == [
        {"line": 2, "text": "beta"},
        {"line": 3, "text": "gamma"},
    ]


def test_session_intelligence_artifact_probe_helper_summarizes_json_and_csv(tmp_path: Path) -> None:
    import services.aios_cli as aios_cli

    json_path = tmp_path / "report.json"
    csv_path = tmp_path / "rows.csv"
    json_path.write_text('{"items": [1, 2], "status": "ok"}\n', encoding="utf-8")
    csv_path.write_text("name,score\nA,1\nB,2\n", encoding="utf-8")
    conn = _memory_conn()

    json_payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="helper",
            session_intel_helper_command="run",
            family="artifact_probe",
            path=str(json_path),
            repo=None,
            start_line=None,
            end_line=None,
        ),
    )
    csv_payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="helper",
            session_intel_helper_command="run",
            family="artifact_probe",
            path=str(csv_path),
            repo=None,
            start_line=None,
            end_line=None,
        ),
    )

    assert json_payload["artifact"]["kind"] == "json"
    assert json_payload["artifact"]["top_level_keys"] == ["items", "status"]
    assert json_payload["artifact"]["array_lengths"] == {"items": 2}
    assert csv_payload["artifact"]["kind"] == "csv"
    assert csv_payload["artifact"]["headers"] == ["name", "score"]
    assert csv_payload["artifact"]["row_count"] == 2


def test_session_intelligence_package_check_helper_reports_scripts_and_lockfiles(
    tmp_path: Path,
) -> None:
    import services.aios_cli as aios_cli

    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "packageManager": "pnpm@10.0.0",
                "scripts": {"lint": "eslint .", "test": "vitest"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    conn = _memory_conn()

    payload = aios_cli._session_intel_payload(
        conn,
        argparse.Namespace(
            session_intel_command="helper",
            session_intel_helper_command="run",
            family="package_check",
            path=None,
            repo=str(tmp_path),
            start_line=None,
            end_line=None,
        ),
    )

    assert payload["family"] == "package_check"
    assert payload["repo"] == str(tmp_path)
    assert payload["package_manager"] == "pnpm"
    assert payload["lockfiles"] == ["pnpm-lock.yaml"]
    assert payload["scripts"] == {"lint": "eslint .", "test": "vitest"}


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
