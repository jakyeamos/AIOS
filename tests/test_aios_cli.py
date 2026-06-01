from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import services.aios_cli as aios_cli  # noqa: E402
from services import standards_health, success_criteria  # noqa: E402
from services.aios_cli import EXIT_OK, run_cli  # noqa: E402
from services.rtk_integration import ensure_rtk_schema  # noqa: E402


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT,
            repo_path TEXT,
            obsidian_path TEXT,
            status TEXT
        );
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            status TEXT,
            started_at TEXT,
            ended_at TEXT,
            cwd TEXT,
            objective TEXT,
            run_id TEXT,
            invocation_id TEXT,
            runtime_metadata_json TEXT DEFAULT '{}'
        );
        CREATE TABLE bug_log (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            symptom TEXT,
            status TEXT,
            created_at TEXT
        );
        CREATE TABLE orchestration_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            session_id TEXT,
            objective TEXT,
            workflow_key TEXT,
            agent_key TEXT,
            status TEXT,
            rationale TEXT,
            assumptions_json TEXT DEFAULT '[]',
            context_trace_json TEXT DEFAULT '[]',
            backend_key TEXT,
            route_id TEXT,
            route_status TEXT,
            route_result_json TEXT DEFAULT '{}',
            active_invocation_id TEXT,
            packet_id TEXT,
            status_reason_json TEXT DEFAULT '{}',
            resume_snapshot_json TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE orchestration_invocations (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            backend_key TEXT,
            backend_label TEXT,
            status TEXT,
            handshake_token TEXT,
            session_id TEXT,
            command_json TEXT DEFAULT '[]',
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT,
            started_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE briefing_packets (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            project_id TEXT,
            objective TEXT,
            workflow_key TEXT,
            agent_key TEXT,
            packet_markdown TEXT,
            sections_json TEXT DEFAULT '[]',
            policy_mode TEXT DEFAULT 'compact-ranked',
            token_budget INTEGER DEFAULT 900,
            route_id TEXT,
            route_result_json TEXT DEFAULT '{}',
            selection_trace_json TEXT DEFAULT '[]',
            omitted_context_json TEXT DEFAULT '[]',
            created_at TEXT
        );
        CREATE TABLE active_rules (
            title TEXT,
            body TEXT,
            domain TEXT,
            confidence REAL
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
            updated_at TEXT,
            decision_note TEXT,
            decision_actor TEXT,
            decision_at TEXT
        );
        CREATE TABLE knowledge_topics (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            canonical_href TEXT,
            confidence REAL,
            project_id TEXT,
            updated_at TEXT
        );
        CREATE TABLE orchestration_run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            to_status TEXT,
            summary TEXT,
            reason_json TEXT,
            created_at TEXT
        );
        CREATE TABLE workflow_execution_reports (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            invocation_id TEXT,
            workflow_key TEXT,
            status TEXT,
            report_json TEXT DEFAULT '{}',
            artifact_path TEXT,
            created_at TEXT
        );
        """
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('p1', 'AIOS', '/repo', '03 Projects/AIOS', 'active')
        """
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, status, started_at, ended_at, cwd)
        VALUES ('s1', 'p1', 'closed', '2026-04-23T00:00:00Z', '2026-04-23T00:10:00Z', '/repo')
        """
    )
    conn.execute(
        """
        INSERT INTO bug_log (id, project_id, symptom, status, created_at)
        VALUES ('b1', 'p1', 'TypeError: boom', 'open', '2026-04-23T00:20:00Z')
        """
    )
    conn.execute("INSERT INTO orchestration_runs (id, status) VALUES ('run-1', 'failed')")
    conn.execute(
        """
        INSERT INTO active_rules (title, body, domain, confidence)
        VALUES ('Use explicit handshakes', 'Start serious work with run and invocation linkage.', 'workflow', 0.9)
        """
    )
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
            id, project_id, layer_type, layer_key, title, summary, status,
            requires_approval, created_at, updated_at
        )
        VALUES (
            'wb-1', 'p1', 'workflow', 'routing', 'Route serious work through AIOS',
            'Use the control plane packet before implementation work.', 'applied', 0,
            '2026-04-23T00:25:00Z', '2026-04-23T00:25:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO knowledge_topics (
            id, title, summary, canonical_href, confidence, project_id, updated_at
        )
        VALUES (
            'topic-1', 'Agent routing', 'AIOS should route serious agent work through explicit packets.',
            '/knowledge/agent-routing', 0.95, 'p1', '2026-04-23T00:26:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_run_events (id, run_id, to_status, summary, reason_json, created_at)
        VALUES ('e1', 'run-1', 'failed', 'Run failed', '{}', '2026-04-23T00:30:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
            id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at
        )
        VALUES (
            'wr-1', 'run-1', 'inv-1', 'academic_paper_v1', 'completed',
            '{}', '/tmp/workflow-report.json', '2026-04-23T00:35:00Z'
        )
        """
    )
    conn.commit()
    conn.close()


def _memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_record_learning_event_persists_signal_kind() -> None:
    conn = _memory_conn()
    aios_cli._ensure_workflow_learning_schema(conn)

    aios_cli._record_workflow_learning_event(
        conn,
        run_id="r1",
        evidence_type="workflow_evidence",
        proposal_target="propose-x",
        confidence=0.7,
        approval_state="pending",
        rationale="seed",
        source={"k": "v"},
        signal_kind="weak_workflow",
    )

    assert (
        conn.execute(
            "SELECT signal_kind FROM workflow_learning_events WHERE run_id = 'r1'"
        ).fetchone()["signal_kind"]
        == "weak_workflow"
    )


def test_record_learning_event_signal_kind_optional() -> None:
    conn = _memory_conn()
    aios_cli._ensure_workflow_learning_schema(conn)

    aios_cli._record_workflow_learning_event(
        conn,
        run_id="r1",
        evidence_type="workflow_evidence",
        proposal_target="propose-x",
        confidence=0.7,
        approval_state="pending",
        rationale="seed",
        source={"k": "v"},
    )

    assert (
        conn.execute(
            "SELECT signal_kind FROM workflow_learning_events WHERE run_id = 'r1'"
        ).fetchone()["signal_kind"]
        is None
    )


def test_workflow_learning_event_dedupe_respects_signal_kind() -> None:
    conn = _memory_conn()
    aios_cli._ensure_workflow_learning_schema(conn)

    for signal_kind in ("weak_workflow", "ignored_rule", "weak_workflow"):
        aios_cli._record_workflow_learning_event(
            conn,
            run_id="r1",
            evidence_type="workflow_evidence",
            proposal_target="propose-x",
            confidence=0.7,
            approval_state="pending",
            rationale="seed",
            source={"k": "v"},
            signal_kind=signal_kind,
        )

    assert (
        conn.execute("SELECT COUNT(*) AS count FROM workflow_learning_events").fetchone()["count"]
        == 2
    )


def test_workflow_learning_event_dedupe_legacy_path_unchanged() -> None:
    conn = _memory_conn()
    aios_cli._ensure_workflow_learning_schema(conn)

    for _ in range(2):
        aios_cli._record_workflow_learning_event(
            conn,
            run_id="r1",
            evidence_type="workflow_evidence",
            proposal_target="propose-x",
            confidence=0.7,
            approval_state="pending",
            rationale="seed",
            source={"k": "v"},
        )

    assert (
        conn.execute("SELECT COUNT(*) AS count FROM workflow_learning_events").fetchone()["count"]
        == 1
    )


def test_ensure_workflow_learning_schema_creates_signal_kind_column() -> None:
    conn = _memory_conn()

    aios_cli._ensure_workflow_learning_schema(conn)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(workflow_learning_events)")}
    assert "signal_kind" in columns


def test_workflow_learning_payload_surfaces_signal_kind() -> None:
    conn = _memory_conn()
    conn.execute(
        """
        CREATE TABLE orchestration_runs (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            session_id TEXT,
            objective TEXT,
            workflow_key TEXT,
            agent_key TEXT,
            status TEXT,
            rationale TEXT,
            assumptions_json TEXT DEFAULT '[]',
            context_trace_json TEXT DEFAULT '[]',
            result_summary TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, objective, workflow_key, agent_key, status, rationale, result_summary, updated_at
        )
        VALUES ('r1', 'objective', 'implementation-delivery', 'codex', 'completed',
                'rationale', 'done', '2026-06-01T00:00:00Z')
        """
    )
    aios_cli._ensure_workflow_learning_schema(conn)
    aios_cli._record_workflow_learning_event(
        conn,
        run_id="r1",
        evidence_type="workflow_evidence",
        proposal_target="implementation-delivery",
        confidence=0.7,
        approval_state="not_required",
        rationale="seed",
        source={"k": "v"},
        signal_kind="weak_workflow",
    )
    aios_cli._record_workflow_learning_event(
        conn,
        run_id="r1",
        evidence_type="prompt_template_evidence",
        proposal_target="research",
        confidence=0.7,
        approval_state="not_required",
        rationale="seed",
        source={"k": "v"},
    )

    payload = aios_cli._workflow_learning_payload(conn)
    by_target = {row["proposal_target"]: row for row in payload["persisted_events"]}

    assert by_target["implementation-delivery"]["signal_kind"] == "weak_workflow"
    assert by_target["research"]["signal_kind"] is None


def test_status_and_recent_failures_json(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "hooks.log").write_text(
        "2026-04-23T00:40:00Z [hook] error: failed example\n",
        encoding="utf-8",
    )
    _seed_db(db_path)

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "status",
        ]
    )
    assert status_exit == EXIT_OK
    status_output = json.loads(capsys.readouterr().out)
    assert status_output["ok"] is True
    assert status_output["command"] == "status"
    assert status_output["data"]["resumable_runs"] == []


def test_asset_lifecycle_list_subcommand(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE promotion_lifecycle_items (
          id TEXT PRIMARY KEY,
          item_kind TEXT NOT NULL,
          item_key TEXT NOT NULL,
          source_run_id TEXT,
          status TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status_reason TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id, item_kind, item_key, status, status_reason, created_at, updated_at
        )
        VALUES ('life-1', 'workflow', 'implementation-delivery', 'active', 'seed',
                '2026-05-24T00:00:00Z', '2026-05-24T00:00:00Z')
        """
    )
    conn.commit()
    conn.close()

    assert (
        run_cli(["--json", "--db", str(db_path), "asset-lifecycle", "list", "--kind", "workflow"])
        == EXIT_OK
    )
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["assets"][0]["kind"] == "workflow"
    assert output["data"]["assets"][0]["lifecycle_state"] == "active"


def test_asset_lifecycle_promote_subcommand(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path)

    assert (
        run_cli(
            [
                "--json",
                "--db",
                str(db_path),
                "asset-lifecycle",
                "promote",
                "--kind",
                "prompt",
                "--key",
                "research",
                "--from",
                "draft",
                "--to",
                "candidate",
                "--actor",
                "op",
                "--rationale",
                "test",
            ]
        )
        == EXIT_OK
    )
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["asset_key"] == "research"
    assert output["data"]["to_state"] == "candidate"


def test_workflow_compare_cli(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path)

    assert (
        run_cli(
            [
                "--json",
                "--db",
                str(db_path),
                "workflow-compare",
                "--workflow-key",
                "academic_paper_v1",
                "--since",
                "2026-01-01T00:00:00Z",
            ]
        )
        == EXIT_OK
    )
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["workflow_key"] == "academic_paper_v1"
    assert "mean_blockers_per_stage" in output["data"]
    assert "writeback_usefulness" in output["data"]


def test_promote_asset_cli_for_workflow_uses_workflow_promotion(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path)

    assert (
        run_cli(
            [
                "--json",
                "--db",
                str(db_path),
                "promote-asset",
                "--kind",
                "workflow",
                "--key",
                "implementation-delivery",
                "--to",
                "approved",
                "--actor",
                "op",
                "--rationale",
                "evidence",
                "--since",
                "2026-01-01T00:00:00Z",
            ]
        )
        == EXIT_OK
    )
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["requires_approval"] is True
    assert output["data"]["writeback_id"]
    assert output["data"]["lifecycle_id"]


def test_contracts_audit_includes_asset_lifecycle_and_workflow_comparison(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "aios.db"
    _seed_db(db_path)

    assert run_cli(["--json", "--db", str(db_path), "contracts-audit"]) == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    names = {contract["name"] for contract in output["data"]["contracts"]}
    assert {"AssetLifecycle", "WorkflowComparison"} <= names


def test_status_reports_resume_snapshot_for_resumable_run(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO orchestration_runs (
            id, project_id, objective, workflow_key, agent_key, status, rationale,
            assumptions_json, context_trace_json, packet_id, resume_snapshot_json, created_at, updated_at
        )
        VALUES (
            'run-resume', 'p1', 'Resume AIOS workflow execution', 'implementation-delivery',
            'implementation-lead', 'waiting_for_user', 'Resume test', '[]', '[]', 'packet-resume',
            ?, '2026-04-23T01:00:00Z', '2026-04-23T01:10:00Z'
        )
        """,
        (
            json.dumps(
                {
                    "packet_id": "packet-resume",
                    "current_stage": "awaiting_approval",
                    "next_recommended_action": "Review the pending workflow-default writeback before resuming execution.",
                    "pending_approval_count": 1,
                    "approval_targets": ["workflow-default"],
                    "updated_at": "2026-04-23T01:10:00Z",
                }
            ),
        ),
    )
    conn.commit()
    conn.close()

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "status",
        ]
    )
    assert status_exit == EXIT_OK
    status_output = json.loads(capsys.readouterr().out)
    resumable = status_output["data"]["resumable_runs"]
    assert len(resumable) == 1
    assert resumable[0]["run_id"] == "run-resume"
    assert resumable[0]["current_stage"] == "awaiting_approval"
    assert resumable[0]["pending_approval_count"] == 1
    assert resumable[0]["next_recommended_action"].startswith("Review the pending workflow-default")


def test_status_reports_recent_governed_closeout(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
            id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at
        )
        VALUES (
            'wr-closeout', 'run-1', 'inv-1', 'implementation-delivery', 'needs_follow_up',
            ?, '/tmp/closeout.json', '2026-04-23T01:20:00Z'
        )
        """,
        (
            json.dumps(
                {
                    "report_type": "governed_closeout",
                    "outcome": "needs_follow_up",
                    "result_summary": "Implementation shipped but cleanup remains.",
                    "changed_artifacts": ["/repo/services/task_routing.py"],
                    "checks_run": {"success_criteria_evaluation_id": "eval-1"},
                    "approvals": {"pending_approval_count": 1},
                    "unresolved_deltas": {
                        "open_questions": ["Need sign-off"],
                        "risks": ["Follow-up cleanup"],
                    },
                }
            ),
        ),
    )
    conn.commit()
    conn.close()

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "status",
        ]
    )
    assert status_exit == EXIT_OK
    status_output = json.loads(capsys.readouterr().out)
    closeouts = status_output["data"]["recent_closeouts"]
    assert len(closeouts) == 1
    assert closeouts[0]["run_id"] == "run-1"
    assert closeouts[0]["outcome"] == "needs_follow_up"
    assert closeouts[0]["pending_approval_count"] == 1
    assert closeouts[0]["changed_artifact_count"] == 1


def test_truth_audit_reports_governed_truth_contract(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    truth_file = tmp_path / "PROJECT.md"
    truth_file.write_text(
        "\n".join(
            [
                "# Demo Truth",
                "Last updated: 2026-05-17",
                "## Goals",
                "## Architecture",
                "## Risks",
                "## Completed Work",
                "## Unresolved Deltas",
                "## Next Actions",
                "## Decisions",
            ]
        ),
        encoding="utf-8",
    )
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        UPDATE orchestration_runs
        SET
            project_id = 'p1',
            objective = 'Complete governed truth update',
            workflow_key = 'project-truth-update',
            agent_key = 'implementation-lead',
            status = 'needs_follow_up',
            packet_id = 'packet-truth',
            resume_snapshot_json = ?,
            updated_at = '2026-05-18T01:10:00Z'
        WHERE id = 'run-1'
        """,
        (
            json.dumps(
                {
                    "packet_id": "packet-truth",
                    "current_stage": "truth_review",
                    "next_recommended_action": "Review proposed truth deltas.",
                    "pending_approval_count": 1,
                    "approval_targets": ["PROJECT.md"],
                    "updated_at": "2026-05-18T01:10:00Z",
                }
            ),
        ),
    )
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
            id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at
        )
        VALUES (
            'wr-truth-closeout', 'run-1', 'inv-1', 'project-truth-update', 'needs_follow_up',
            ?, '/tmp/truth-closeout.json', '2026-05-18T01:20:00Z'
        )
        """,
        (
            json.dumps(
                {
                    "report_type": "governed_closeout",
                    "outcome": "needs_follow_up",
                    "result_summary": "Truth update proposal is ready for review.",
                    "changed_artifacts": [str(truth_file)],
                    "approvals": {"pending_approval_count": 1},
                    "unresolved_deltas": {
                        "open_questions": ["Operator approval required"],
                        "risks": [],
                    },
                }
            ),
        ),
    )
    conn.commit()
    conn.close()

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "truth-audit",
            "--truth-file",
            str(truth_file),
        ]
    )

    assert status_exit == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    data = output["data"]
    assert output["command"] == "truth-audit"
    assert data["summary"]["missing_facet_count"] == 0
    assert data["summary"]["recent_closeout_count"] == 1
    assert data["summary"]["resumable_run_count"] == 1
    assert data["contract"]["important_updates_require_review"] is True
    assert data["contract"]["proposal_sources"] == [
        "workflow_execution_reports.report_json",
        "orchestration_runs.resume_snapshot_json",
    ]


def test_truth_audit_reports_missing_facets(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    truth_file = tmp_path / "PROJECT.md"
    truth_file.write_text("# Sparse Truth\nLast updated: 2026-05-17\n## Goals\n", encoding="utf-8")
    _seed_db(db_path)

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "truth-audit",
            "--truth-file",
            str(truth_file),
        ]
    )

    assert status_exit == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["summary"]["missing_facet_count"] > 0
    assert "truth_facets_missing" in {finding["code"] for finding in data["findings"]}


def test_pre_pr_readiness_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        aios_cli,
        "pre_pr_readiness_payload",
        lambda **_: {
            "status": "pass",
            "coverage": {"coveragePercent": 92.5},
            "unsupported_changed_files": [],
            "supported_changed_files": ["services/pre_pr_readiness.py"],
            "ignored_changed_files": [],
            "findings": [],
            "workspace_root": "/repo",
            "server_entry": "/pre-cr/server.js",
            "pre_cr": {},
        },
    )

    exit_code = run_cli(["--json", "pre-pr-readiness"])

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"] == "pre-pr-readiness"
    assert payload["data"]["status"] == "pass"


def test_capability_audit_reports_missing_and_no_data_signals(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "capability-audit",
        ]
    )

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["command"] == "capability-audit"

    data = output["data"]
    assert data["summary"]["surfaces"] == 5
    assert data["rtk"]["state"]["value"] == "no_eligible_data"
    assert data["rtk"]["state"]["provenance"] == "missing"
    assert data["automations"]["items"][0]["trigger"]["value"] == "Weekdays at 9:00 AM"
    assert data["prompt_library"]["visibility"]["provenance"] == "missing"
    assert data["knowledge"]["topic_count"]["value"] == 1
    assert data["knowledge"]["reference_coverage"]["provenance"] == "missing"

    project = data["projects"]["items"][0]
    assert project["health_score"]["provenance"] == "missing"
    assert project["status"]["provenance"] == "confirmed"
    assert any(finding["code"] == "project_missing_source" for finding in data["findings"])
    assert any(finding["code"] == "prompt_library_links_missing" for finding in data["findings"])
    assert any(finding["code"] == "knowledge_references_missing" for finding in data["findings"])

    failures_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "recent-failures",
            "--last",
            "5",
        ]
    )
    assert failures_exit == EXIT_OK
    failures_output = json.loads(capsys.readouterr().out)
    assert failures_output["ok"] is True
    assert failures_output["command"] == "recent-failures"
    assert failures_output["data"]["count"] >= 2


def test_invocation_audit_and_backend_label_contract(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    audit_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "invocation-audit",
        ]
    )
    assert audit_exit == EXIT_OK
    audit_output = json.loads(capsys.readouterr().out)
    assert audit_output["command"] == "invocation-audit"
    assert audit_output["data"]["summary"]["backend_count"] >= 3
    assert audit_output["data"]["contract"]["required_fields"] == [
        "run_id",
        "invocation_id",
        "backend_key",
        "objective",
        "project_id",
        "workflow_key",
        "packet_id",
        "lifecycle_events",
        "artifacts",
        "closeout_evaluation",
    ]
    assert (
        audit_output["data"]["handshake_coverage"]["legacy_fallback_policy"]
        == "disabled_by_default"
    )

    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "Audit AIOS backend labeling and ship a scoped fix",
            "--backend",
            "claude-managed-runtime",
        ]
    )
    assert start_exit == EXIT_OK
    start_output = json.loads(capsys.readouterr().out)
    invocation_id = start_output["data"]["invocation"]["id"]

    conn = sqlite3.connect(db_path)
    label = conn.execute(
        "SELECT backend_label FROM orchestration_invocations WHERE id = ?",
        (invocation_id,),
    ).fetchone()[0]
    conn.close()
    assert label == "Claude Managed Runtime"


def test_lifecycle_audit_reports_attention_and_unsupported_states(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO orchestration_runs (id, status) VALUES (?, ?)",
        [
            ("run-blocked", "blocked"),
            ("run-user", "waiting_for_user"),
            ("run-tool", "waiting_for_tool"),
            ("run-validation", "failed_validation"),
            ("run-partial", "partial"),
            ("run-follow-up", "needs_follow_up"),
            ("run-superseded", "superseded"),
            ("run-unknown", "mystery_state"),
        ],
    )
    conn.executemany(
        "INSERT INTO orchestration_run_events (id, run_id, to_status, summary, reason_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                "e-blocked",
                "run-blocked",
                "blocked",
                "Waiting on dependency",
                "{}",
                "2026-04-23T00:31:00Z",
            ),
            (
                "e-user",
                "run-user",
                "waiting_for_user",
                "Needs approval",
                "{}",
                "2026-04-23T00:32:00Z",
            ),
            (
                "e-tool",
                "run-tool",
                "waiting_for_tool",
                "Tool pending",
                "{}",
                "2026-04-23T00:33:00Z",
            ),
            (
                "e-validation",
                "run-validation",
                "failed_validation",
                "Criteria failed",
                "{}",
                "2026-04-23T00:34:00Z",
            ),
            (
                "e-unknown",
                "run-unknown",
                "mystery_state",
                "Unexpected state",
                "{}",
                "2026-04-23T00:35:00Z",
            ),
            (
                "e-partial",
                "run-partial",
                "partial",
                "Scoped fix shipped; follow-up tests still required",
                "{}",
                "2026-04-23T00:36:00Z",
            ),
            (
                "e-follow-up",
                "run-follow-up",
                "needs_follow_up",
                "Implementation landed but approval-driven cleanup remains",
                "{}",
                "2026-04-23T00:37:00Z",
            ),
        ],
    )
    conn.commit()
    conn.close()

    lifecycle_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "lifecycle-audit",
        ]
    )

    assert lifecycle_exit == EXIT_OK
    lifecycle_output = json.loads(capsys.readouterr().out)
    data = lifecycle_output["data"]
    assert data["summary"]["attention_count"] == 6
    assert data["summary"]["unsupported_state_count"] == 1
    assert "waiting_for_user" in data["contract"]["attention_states"]
    assert "partial" in data["contract"]["terminal_states"]
    assert "needs_follow_up" in data["contract"]["attention_states"]
    assert data["observed_run_status_counts"]["mystery_state"] == 1
    assert data["unsupported_states"] == ["mystery_state"]
    assert data["recent_attention_events"][0]["to_status"] == "needs_follow_up"


def test_knowledge_objects_expose_provenance_contract(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE knowledge_references (
            id TEXT PRIMARY KEY,
            topic_id TEXT,
            source_kind TEXT,
            source_id TEXT,
            label TEXT,
            href TEXT,
            excerpt TEXT,
            freshness TEXT,
            confidence REAL,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO knowledge_references (
            id, topic_id, source_kind, source_id, label, href, excerpt, freshness, confidence, created_at
        )
        VALUES (
            'ref-1', 'topic-1', 'project_memory', 'run-1', 'Run evidence',
            '/runs/run-1', 'Agent routing evidence', 'fresh', 0.9, '2026-04-23T00:36:00Z'
        )
        """
    )
    conn.commit()
    conn.close()

    objects_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "knowledge-objects",
        ]
    )

    assert objects_exit == EXIT_OK
    objects_output = json.loads(capsys.readouterr().out)
    data = objects_output["data"]
    assert data["summary"]["object_count"] == 1
    assert data["summary"]["source_ref_coverage"] == 1.0
    assert data["contract"]["required_fields"] == [
        "stable_id",
        "kind",
        "title",
        "summary",
        "source_refs",
        "backlinks",
        "freshness",
        "confidence",
        "retrieval_trace_count",
    ]
    assert data["summary"]["unknown_kind_count"] == 0
    assert data["findings"] == []
    assert data["objects"][0]["retrieval_trace_count"] == 0
    assert data["objects"][0]["stable_id"] == "topic-1"
    assert data["objects"][0]["kind"] == "concept"
    assert data["objects"][0]["source_ref_count"] == 1
    assert data["objects"][0]["source_refs"][0]["source_kind"] == "project_memory"


def test_workflow_learning_audit_classifies_run_evidence(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO orchestration_runs (id, status, workflow_key) VALUES (?, ?, ?)",
        [
            ("run-learning", "completed", "implementation-delivery"),
            ("run-empty", "completed", "implementation-delivery"),
        ],
    )
    conn.executemany(
        """
        INSERT INTO improvement_writebacks (
            id, run_id, project_id, layer_type, layer_key, title, summary, status, requires_approval, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "wb-workflow",
                "run-learning",
                "p1",
                "workflow",
                "implementation-delivery",
                "Workflow proposal",
                "Reusable workflow evidence",
                "proposed",
                0,
                "2026-04-23T00:37:00Z",
            ),
            (
                "wb-prompt",
                "run-learning",
                "p1",
                "prompt",
                "implementation-delivery",
                "Prompt proposal",
                "Reusable prompt evidence",
                "pending_approval",
                1,
                "2026-04-23T00:38:00Z",
            ),
        ],
    )
    conn.commit()
    conn.close()

    learning_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "workflow-learning-audit",
        ]
    )

    assert learning_exit == EXIT_OK
    learning_output = json.loads(capsys.readouterr().out)
    data = learning_output["data"]
    assert data["summary"]["terminal_run_count"] == 3
    assert data["summary"]["runs_with_learning"] == 2
    assert data["summary"]["no_learning_count"] == 1
    assert data["summary"]["persisted_event_count"] == 4
    assert data["summary"]["pending_approval_count"] == 1
    assert data["classification_counts"]["workflow_evidence"] == 2
    assert data["classification_counts"]["prompt_template_evidence"] == 1
    assert data["classification_counts"]["no_learning_signal"] == 1


def test_governance_audit_reports_pending_and_missing_terminal_evidence(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT INTO orchestration_runs (id, status, workflow_key, objective, updated_at) VALUES (?, ?, ?, ?, ?)",
        [
            (
                "run-governed",
                "completed",
                "implementation-delivery",
                "Governed run",
                "2026-04-23T01:10:00Z",
            ),
            (
                "run-silent",
                "completed",
                "implementation-delivery",
                "Silent run",
                "2026-04-23T01:20:00Z",
            ),
        ],
    )
    conn.execute(
        """
        INSERT INTO improvement_writebacks (
            id, run_id, project_id, layer_type, layer_key, title, summary, status, requires_approval, created_at
        )
        VALUES (
            'wb-governed', 'run-governed', 'p1', 'truth', 'PROJECT.md', 'Truth proposal',
            'Review before promoting into accepted truth.', 'pending_approval', 1, '2026-04-23T01:30:00Z'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO workflow_execution_reports (
            id, run_id, invocation_id, workflow_key, status, report_json, artifact_path, created_at
        )
        VALUES (
            'wr-governed-closeout', 'run-governed', 'inv-1', 'implementation-delivery', 'needs_follow_up',
            ?, '/tmp/governed-closeout.json', '2026-04-23T01:35:00Z'
        )
        """,
        (
            json.dumps(
                {
                    "report_type": "governed_closeout",
                    "approvals": {"pending_approval_count": 1},
                    "unresolved_deltas": {"risks": ["Approval pending"], "open_questions": []},
                }
            ),
        ),
    )
    success_criteria.ensure_success_criteria_schema(conn)
    conn.execute(
        """
        INSERT INTO success_criteria_stage_findings (
            id, run_id, stage_key, stage_kind, criterion_id, criterion_title,
            criterion_scope, level, summary, created_at
        )
        VALUES (
            'criteria-stage-finding-governance', 'run-governed', 'validate', 'validate',
            'testing-trust', 'Testing Trust', 'global', 'blocker', 'Missing test evidence.',
            '2026-04-01T00:00:00Z'
        )
        """
    )
    conn.commit()
    conn.close()

    audit_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "governance-audit",
        ]
    )

    assert audit_exit == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["summary"]["proposal_count"] == 2
    assert data["summary"]["pending_approval_count"] == 1
    assert data["summary"]["terminal_run_count"] == 3
    assert data["summary"]["terminal_runs_missing_evidence_count"] == 1
    assert data["summary"]["unresolved_closeout_count"] == 1
    assert data["stage_findings"]["open_count"] == 1
    assert data["stage_findings"]["blocker_open_count"] == 1
    assert data["stage_findings"]["recent"][0]["id"] == "criteria-stage-finding-governance"
    assert data["missing_evidence_runs"][0]["run_id"] == "run-silent"
    assert "terminal_runs_missing_governance_evidence" in {
        finding["code"] for finding in data["findings"]
    }


def test_workflow_learning_audit_infers_evidence_from_linked_artifacts(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE artifacts (id TEXT PRIMARY KEY, session_id TEXT, artifact_type TEXT, path TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO orchestration_runs (id, status, workflow_key) VALUES ('run-artifact', 'completed', 'implementation-delivery')"
    )
    conn.execute(
        """
        INSERT INTO sessions (id, project_id, status, started_at, ended_at, cwd, run_id)
        VALUES ('s-artifact', 'p1', 'closed', '2026-04-23T00:00:00Z', '2026-04-23T00:10:00Z', '/repo', 'run-artifact')
        """
    )
    conn.execute(
        """
        INSERT INTO artifacts (id, session_id, artifact_type, path, created_at)
        VALUES ('artifact-1', 's-artifact', 'patch', '/tmp/change.patch', '2026-04-23T00:11:00Z')
        """
    )
    conn.commit()
    conn.close()

    learning_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "workflow-learning-audit",
        ]
    )

    assert learning_exit == EXIT_OK
    learning_output = json.loads(capsys.readouterr().out)
    data = learning_output["data"]
    assert data["classification_counts"]["workflow_evidence"] >= 1
    assert data["summary"]["inferred_evidence_count"] >= 1
    assert data["summary"]["no_learning_count"] == 0
    inferred_by_run = {item["run_id"]: item for item in data["inferred_evidence"]}
    assert inferred_by_run["run-artifact"]["evidence_type"] == "workflow_evidence"


def test_contracts_audit_reports_canonical_interfaces(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    contracts_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "contracts-audit",
        ]
    )

    assert contracts_exit == EXIT_OK
    contracts_output = json.loads(capsys.readouterr().out)
    data = contracts_output["data"]
    names = {contract["name"] for contract in data["contracts"]}
    assert data["summary"]["canonical_contract_count"] == 10
    assert data["summary"]["implemented_or_partial_count"] >= 6
    assert {
        "TrustedSignal",
        "InvocationBackend",
        "RunLifecycleEvent",
        "KnowledgeObject",
        "RetrievalTrace",
        "WorkflowLearningEvent",
        "EvaluationFinding",
        "DeltaExplanation",
        "AssetLifecycle",
        "WorkflowComparison",
    }.issubset(names)
    invocation = next(
        contract for contract in data["contracts"] if contract["name"] == "InvocationBackend"
    )
    assert invocation["status"] == "implemented"
    assert invocation["source"] == "services/invocation_backends.py"


def test_criteria_finding_resolve_transitions_open_finding(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    conn = sqlite3.connect(db_path)
    success_criteria.ensure_success_criteria_schema(conn)
    conn.execute(
        """
        INSERT INTO success_criteria_evaluations (
            id, trigger_kind, evaluator_version, summary
        )
        VALUES ('criteria-eval-test', 'test', 'v1', 'test')
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_findings (
            id, evaluation_id, criterion_id, criterion_title, criterion_scope,
            level, summary
        )
        VALUES (
            'criteria-finding-test', 'criteria-eval-test', 'testing-trust',
            'Testing Trust', 'global', 'warning', 'Needs review.'
        )
        """
    )
    conn.commit()
    conn.close()

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "criteria-finding",
            "resolve",
            "--id",
            "criteria-finding-test",
            "--status",
            "accepted",
            "--rationale",
            "ok",
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)["data"]
    assert payload["previous_status"] == "open"
    assert payload["new_status"] == "accepted"
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        """
        SELECT resolution_status, resolution_actor, resolution_rationale, resolved_at
        FROM success_criteria_findings
        WHERE id = 'criteria-finding-test'
        """
    ).fetchone()
    conn.close()
    assert row[0] == "accepted"
    assert row[1] == "operator-cli"
    assert row[2] == "ok"
    assert row[3] is not None


def test_criteria_finding_resolve_works_on_stage_findings_too(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    conn = sqlite3.connect(db_path)
    success_criteria.ensure_success_criteria_schema(conn)
    conn.execute(
        """
        INSERT INTO success_criteria_stage_findings (
            id, run_id, stage_key, stage_kind, criterion_id, criterion_title,
            criterion_scope, level, summary
        )
        VALUES (
            'criteria-stage-finding-test', 'run-1', 'validate', 'validate',
            'testing-trust', 'Testing Trust', 'global', 'blocker', 'Needs review.'
        )
        """
    )
    conn.commit()
    conn.close()

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "criteria-finding",
            "resolve",
            "--id",
            "criteria-stage-finding-test",
            "--status",
            "waived",
            "--rationale",
            "accepted risk",
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)["data"]
    assert payload["scope"] == "stage"
    assert payload["new_status"] == "waived"


def test_standards_resolution_preview_returns_merged_payload(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "standards-resolution",
            "preview",
            "--project-id",
            "p1",
            "--project-name",
            "AIOS",
            "--objective",
            "Implement workflow orchestration",
            "--classification",
            "implement",
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)["data"]
    assert payload["criteria"]
    assert payload["resolution_status"] in {"ok", "no_profile_attached"}
    assert "execution_first_triggers" in payload


def _seed_standards_health_for_cli(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("ALTER TABLE orchestration_run_events ADD COLUMN project_id TEXT")
    standards_health.ensure_standards_health_schema(conn)
    conn.execute(
        """
        INSERT INTO project_standards_profiles (
            project_id, profile_id, attached_version, latest_version, migration_mode
        )
        VALUES ('p1', 'aios-core', '2026.06.0', '2026.06.0', 'current')
        ON CONFLICT(project_id) DO UPDATE SET
            attached_version = excluded.attached_version,
            latest_version = excluded.latest_version
        """
    )
    standards_health.evaluate_and_record(conn, project_id="p1")
    conn.commit()
    conn.close()


def test_delta_explain_cli_returns_explanations(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    _seed_standards_health_for_cli(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "delta-explain",
            "--project",
            "p1",
        ]
    )

    assert exit_code == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["project_id"] == "p1"
    assert data["snapshot_id"] is not None
    assert data["delta_explanations"]
    assert {
        "standard_id",
        "domain",
        "status",
        "provenance",
        "confidence",
        "freshness",
        "evidence",
        "contradiction",
        "remediation_summary",
        "priority_score",
        "priority_bucket",
    }.issubset(data["delta_explanations"][0])


def test_delta_explain_cli_with_no_snapshot_returns_empty_list(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "delta-explain",
            "--project",
            "missing",
        ]
    )

    assert exit_code == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert data == {"project_id": "missing", "snapshot_id": None, "delta_explanations": []}


def test_recommend_workflow_cli_returns_recommendations(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    _seed_standards_health_for_cli(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "recommend-workflow",
            "--project",
            "p1",
        ]
    )

    assert exit_code == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["project_id"] == "p1"
    assert data["recommendations"]
    first = data["recommendations"][0]
    assert {
        "workflow_key",
        "rationale",
        "available_in_registry",
        "requires_approval",
        "impact_scope",
        "policy_class",
        "triggered_by",
    }.issubset(first)
    assert any(row["available_in_registry"] is False for row in data["recommendations"])


def test_recommend_workflow_cli_with_no_snapshot_returns_empty_list(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "recommend-workflow",
            "--project",
            "missing",
        ]
    )

    assert exit_code == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert data == {"project_id": "missing", "recommendations": []}


def test_standards_override_cli_writes_override_and_next_snapshot_reflects_it(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "standards-override",
            "--project",
            "p1",
            "--standard",
            "ux.operator_clarity",
            "--status",
            "pass",
            "--rationale",
            "operator-reviewed-2026-05-24",
            "--actor",
            "operator-cli",
        ]
    )

    assert exit_code == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["standard_id"] == "ux.operator_clarity"
    assert data["status"] == "pass"
    conn = sqlite3.connect(db_path)
    standards_health.evaluate_and_record(conn, project_id="p1")
    row = conn.execute(
        """
        SELECT status, evaluator_type, reason
        FROM standards_assessments
        WHERE project_id = 'p1' AND standard_id = 'ux.operator_clarity'
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "pass"
    assert row[1] == "manual"
    assert "operator-reviewed-2026-05-24" in row[2]


def test_standards_override_cli_rejects_invalid_status(tmp_path: Path) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    with pytest.raises(SystemExit) as exc:
        run_cli(
            [
                "--json",
                "--db",
                str(db_path),
                "--logs-dir",
                str(logs_dir),
                "standards-override",
                "--project",
                "p1",
                "--standard",
                "ux.operator_clarity",
                "--status",
                "invalid",
            ]
        )
    assert exc.value.code == 2


def test_standards_override_cli_rejects_unknown_standard_id(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)

    exit_code = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "standards-override",
            "--project",
            "p1",
            "--standard",
            "nonexistent.fake",
            "--status",
            "pass",
            "--rationale",
            "x",
        ]
    )

    assert exit_code == aios_cli.EXIT_USAGE
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_governance_audit_includes_recommended_workflows(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    _seed_standards_health_for_cli(db_path)

    exit_code = run_cli(
        ["--json", "--db", str(db_path), "--logs-dir", str(logs_dir), "governance-audit"]
    )

    assert exit_code == EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert "recommended_workflows" in data
    assert data["recommended_workflows"]["p1"]


def test_metadata_and_skills_refresh_flow(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    config_root = tmp_path / "config"
    vault_root = tmp_path / "vault"
    logs_dir.mkdir()
    config_root.mkdir()
    vault_root.mkdir()

    _seed_db(db_path)

    arch_dir = config_root / "architecture-enforcement"
    arch_dir.mkdir()
    (arch_dir / "projects.json").write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "id": "aios",
                        "name": "AIOS",
                        "path": str(tmp_path),
                        "proof_target": True,
                        "profile_bindings": [{"profile_id": "python-service-v1"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    source_file = tmp_path / "source.md"
    source_file.write_text("hello from source\n", encoding="utf-8")
    (config_root / "instruction-registry.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "id": "global",
                        "project_id": None,
                        "source": str(source_file),
                        "target": "06 Knowledge/Claude-Context/global.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    criteria_dir = config_root / "success-criteria"
    criteria_dir.mkdir()
    (criteria_dir / "registry.json").write_text(
        json.dumps(
            {
                "criteria": [
                    {
                        "id": "code-simplicity",
                        "title": "Protect Simplicity and Comprehension",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    workflows_dir = config_root / "workflows"
    workflows_dir.mkdir()
    (workflows_dir / "registry.json").write_text(
        json.dumps(
            {
                "workflows": [
                    {
                        "key": "academic_paper_v1",
                        "name": "Academic Paper v1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    strategy_dir = config_root / "execution-strategies"
    strategy_dir.mkdir()
    (strategy_dir / "registry.json").write_text(
        json.dumps(
            {
                "task_families": ["audit_and_implement"],
                "selection": [
                    {
                        "task_family": "audit_and_implement",
                        "surface": "codex",
                        "strategy_id": "audit_and_implement_codex_v1",
                    },
                    {
                        "task_family": "audit_and_implement",
                        "surface": "claude_code",
                        "strategy_id": "audit_and_implement_claude_v1",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE success_criteria_evaluations (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            run_id TEXT,
            session_id TEXT,
            pass_count INTEGER,
            warning_count INTEGER,
            blocker_count INTEGER,
            summary TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO success_criteria_evaluations (
            id, project_id, run_id, session_id, pass_count, warning_count, blocker_count, summary, created_at
        )
        VALUES ('eval-1', 'p1', 'run-1', 's1', 3, 1, 0, 'latest criteria summary', '2026-04-23T00:50:00Z')
        """
    )
    conn.execute(
        """
        CREATE TABLE standards_health_snapshots (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            profile_id TEXT,
            attached_version TEXT,
            latest_version TEXT,
            standards_version TEXT,
            overall_score REAL,
            weighted_delta REAL,
            max_penalty REAL,
            unmet_standards_count INTEGER,
            critical_delta_count INTEGER,
            regression_count INTEGER,
            unknown_count INTEGER,
            unknown_coverage REAL,
            evaluation_confidence REAL,
            domain_scores_json TEXT,
            score_explain_json TEXT,
            migration_json TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO standards_health_snapshots (
            id, project_id, profile_id, attached_version, latest_version, standards_version,
            overall_score, weighted_delta, max_penalty, unmet_standards_count, critical_delta_count,
            regression_count, unknown_count, unknown_coverage, evaluation_confidence,
            domain_scores_json, score_explain_json, migration_json, created_at
        )
        VALUES (
            'health-1', 'p1', 'aios-core', '2026.04.0', '2026.05.0', '2026.05.0',
            84.25, 8.5, 50.0, 2, 1, 0, 1, 0.22, 0.81,
            '{}', '{}', '{}', '2026-04-23T00:55:00Z'
        )
        """
    )
    conn.commit()
    conn.close()

    standards_dir = config_root / "standards"
    standards_dir.mkdir()
    (standards_dir / "registry.json").write_text(
        json.dumps(
            {
                "profile": {
                    "id": "aios-core",
                    "version": "2026.05.0",
                    "default_attached_version": "2026.04.0",
                },
                "standards": [
                    {
                        "id": "architecture.boundary_enforcement",
                        "domain": "architecture",
                    },
                    {
                        "id": "testing.trust_signal",
                        "domain": "testing",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    metadata_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "metadata",
        ]
    )
    assert metadata_exit == EXIT_OK
    metadata_output = json.loads(capsys.readouterr().out)
    assert metadata_output["ok"] is True
    assert metadata_output["data"]["linked_projects"]["count"] == 1
    assert metadata_output["data"]["instructions"]["summary"]["missing_target"] == 1
    assert metadata_output["data"]["success_criteria"]["catalog"]["count"] == 1
    assert metadata_output["data"]["success_criteria"]["latest_evaluation"]["id"] == "eval-1"
    assert metadata_output["data"]["workflow_orchestration"]["registry"]["count"] == 1
    assert (
        metadata_output["data"]["workflow_orchestration"]["latest_execution_report"]["id"] == "wr-1"
    )
    assert metadata_output["data"]["execution_strategies"]["task_family_count"] == 1
    assert metadata_output["data"]["execution_strategies"]["strategy_count"] == 2
    assert metadata_output["data"]["standards_delta"]["registry"]["profile_id"] == "aios-core"
    assert metadata_output["data"]["standards_delta"]["registry"]["standard_count"] == 2
    assert metadata_output["data"]["standards_delta"]["latest_snapshot"]["id"] == "health-1"
    assert metadata_output["data"]["rtk"]["default_mode"] == "compressed"

    rtk_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "rtk",
        ]
    )
    assert rtk_exit == EXIT_OK
    rtk_output = json.loads(capsys.readouterr().out)
    assert rtk_output["ok"] is True
    assert rtk_output["data"]["state"] == "no_eligible_data"
    assert rtk_output["data"]["benefit_state"] == "no_eligible_data"
    assert rtk_output["data"]["metrics"]["event_count"] == 0

    dry_run_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "skills",
            "refresh",
        ]
    )
    assert dry_run_exit == EXIT_OK
    dry_run_output = json.loads(capsys.readouterr().out)
    assert dry_run_output["data"]["pending_count"] == 1
    assert dry_run_output["data"]["updated_count"] == 0

    apply_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "skills",
            "refresh",
            "--apply",
        ]
    )
    assert apply_exit == EXIT_OK
    apply_output = json.loads(capsys.readouterr().out)
    assert apply_output["data"]["updated_count"] == 1

    status_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "--config-root",
            str(config_root),
            "--vault-root",
            str(vault_root),
            "skills",
            "status",
        ]
    )
    assert status_exit == EXIT_OK
    status_output = json.loads(capsys.readouterr().out)
    assert status_output["data"]["summary"]["in_sync"] == 1


def test_start_work_creates_packet_and_links_current_session(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "current_session").write_text("s1", encoding="utf-8")
    _seed_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE sessions SET status = 'open' WHERE id = 's1'")
    conn.commit()
    conn.close()

    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "Audit AIOS onboarding and ship a scoped fix with tests",
        ]
    )

    assert start_exit == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["command"] == "start-work"
    data = output["data"]
    assert data["run"]["status"] == "in_progress"
    assert data["run"]["session_id"] == "s1"
    assert data["run"]["project_id"] == "p1"
    assert data["packet"]["policy_mode"] == "compact-ranked"
    assert data["packet"]["contract_version"] == "governed-handoff-v1"
    assert "Audit AIOS onboarding and ship a scoped fix with tests" in data["packet"]["markdown"]
    assert "Prompt And Handoff Contract" in data["packet"]["markdown"]
    assert "Required Checks And Escalations" in data["packet"]["markdown"]
    assert "Closeout And Writeback" in data["packet"]["markdown"]
    section_titles = [section["title"] for section in data["packet"]["sections"]]
    assert "Workflow Stages" in section_titles
    assert "Prompt And Handoff Contract" in section_titles
    assert "Required Checks And Escalations" in section_titles
    assert data["invocation"]["session_id"] == "s1"
    assert data["route"]["project"]["selected_project_id"] == "p1"
    assert data["route"]["selected_workflow"]["workflow_key"] == "implementation-delivery"
    assert data["next_agent_context"]["run_id"] == data["run"]["id"]
    assert data["next_agent_context"]["invocation_id"] == data["invocation"]["id"]

    conn = sqlite3.connect(db_path)
    linked = conn.execute(
        "SELECT run_id, invocation_id, objective FROM sessions WHERE id = 's1'"
    ).fetchone()
    assert linked == (
        data["run"]["id"],
        data["invocation"]["id"],
        "Audit AIOS onboarding and ship a scoped fix with tests",
    )
    packet_row = conn.execute(
        "SELECT run_id, packet_markdown, route_result_json, selection_trace_json FROM briefing_packets WHERE id = ?",
        (data["packet"]["id"],),
    ).fetchone()
    assert packet_row[0] == data["run"]["id"]
    assert "Applicable Success Criteria" in packet_row[1]
    route_result = json.loads(packet_row[2])
    assert route_result["project"]["selected_project_id"] == "p1"
    selection_trace = json.loads(packet_row[3])
    assert selection_trace["query"] == "Audit AIOS onboarding and ship a scoped fix with tests"
    assert selection_trace["route"]["route_id"] == data["run"]["route_id"]
    assert selection_trace["packet_contract"]["version"] == "governed-handoff-v1"
    assert selection_trace["packet_contract"]["workflow_key"] == "implementation-delivery"
    assert selection_trace["matched_objects"][0]["title"] == "Agent routing"
    assert selection_trace["token_budget"] == 900
    snapshot = conn.execute(
        "SELECT resume_snapshot_json FROM orchestration_runs WHERE id = ?",
        (data["run"]["id"],),
    ).fetchone()[0]
    resume_snapshot = json.loads(snapshot)
    assert resume_snapshot["current_stage"] == "packet_ready"
    assert resume_snapshot["packet_id"] == data["packet"]["id"]
    event_count = conn.execute(
        "SELECT COUNT(*) FROM orchestration_run_events WHERE run_id = ?",
        (data["run"]["id"],),
    ).fetchone()[0]
    assert event_count == 3
    conn.close()


def test_start_work_blocks_ambiguous_route_before_packet_creation(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('p2', 'Soundscape App', '/soundscape-app', '03 Projects/Soundscape App', 'active')
        """
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('p3', 'Soundscape Web', '/soundscape-web', '03 Projects/Soundscape Web', 'active')
        """
    )
    conn.commit()
    conn.close()

    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "Improve Soundscape onboarding and make it launch ready",
        ]
    )

    assert start_exit == aios_cli.EXIT_USAGE
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["error"]["code"] == "route-blocked"

    conn = sqlite3.connect(db_path)
    run_count = conn.execute(
        "SELECT COUNT(*) FROM orchestration_runs WHERE objective = ?",
        ("Improve Soundscape onboarding and make it launch ready",),
    ).fetchone()[0]
    packet_count = conn.execute("SELECT COUNT(*) FROM briefing_packets").fetchone()[0]
    assert run_count == 0
    assert packet_count == 0
    conn.close()


def test_rtk_cli_reports_token_regressive_events(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "aios.db"
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    _seed_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
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
          400, 640, 100, 160, 0.0, 0, '{}'
        )
        """
    )
    conn.commit()
    conn.close()

    exit_code = run_cli(["--json", "--db", str(db_path), "--logs-dir", str(logs_dir), "rtk"])

    assert exit_code == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["data"]["state"] == "token_regressive"
    assert output["data"]["benefit_state"] == "token_regressive"
    assert output["data"]["findings"][0]["code"] == "rtk_token_regressive"
