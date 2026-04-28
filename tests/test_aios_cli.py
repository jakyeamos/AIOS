from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.aios_cli import EXIT_OK, run_cli  # noqa: E402


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, status TEXT);
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
            active_invocation_id TEXT,
            packet_id TEXT,
            status_reason_json TEXT DEFAULT '{}',
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
            status TEXT,
            requires_approval INTEGER DEFAULT 0,
            created_at TEXT
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
            artifact_path TEXT,
            created_at TEXT
        );
        """
    )
    conn.execute("INSERT INTO projects (id, name, status) VALUES ('p1', 'AIOS', 'active')")
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
            id, project_id, layer_type, layer_key, title, summary, status, requires_approval, created_at
        )
        VALUES (
            'wb-1', 'p1', 'workflow', 'routing', 'Route serious work through AIOS',
            'Use the control plane packet before implementation work.', 'applied', 0, '2026-04-23T00:25:00Z'
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
            id, run_id, invocation_id, workflow_key, status, artifact_path, created_at
        )
        VALUES (
            'wr-1', 'run-1', 'inv-1', 'academic_paper_v1', 'completed',
            '/tmp/workflow-report.json', '2026-04-23T00:35:00Z'
        )
        """
    )
    conn.commit()
    conn.close()


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
    assert status_output["data"]["projects_active"] == 1


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
    assert any(finding["code"] == "project_health_missing" for finding in data["findings"])
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
    assert audit_output["data"]["handshake_coverage"]["legacy_fallback_policy"] == "disabled_by_default"

    start_exit = run_cli(
        [
            "--json",
            "--db",
            str(db_path),
            "--logs-dir",
            str(logs_dir),
            "start-work",
            "verify backend label",
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
            ("run-superseded", "superseded"),
            ("run-unknown", "mystery_state"),
        ],
    )
    conn.executemany(
        "INSERT INTO orchestration_run_events (id, run_id, to_status, summary, reason_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("e-blocked", "run-blocked", "blocked", "Waiting on dependency", "{}", "2026-04-23T00:31:00Z"),
            ("e-user", "run-user", "waiting_for_user", "Needs approval", "{}", "2026-04-23T00:32:00Z"),
            ("e-tool", "run-tool", "waiting_for_tool", "Tool pending", "{}", "2026-04-23T00:33:00Z"),
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
    assert data["summary"]["attention_count"] == 4
    assert data["summary"]["unsupported_state_count"] == 1
    assert "waiting_for_user" in data["contract"]["attention_states"]
    assert data["observed_run_status_counts"]["mystery_state"] == 1
    assert data["unsupported_states"] == ["mystery_state"]
    assert data["recent_attention_events"][0]["to_status"] == "failed_validation"


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
    ]
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
    assert data["summary"]["runs_with_learning"] == 1
    assert data["summary"]["no_learning_count"] == 2
    assert data["summary"]["pending_approval_count"] == 1
    assert data["classification_counts"]["workflow_evidence"] == 1
    assert data["classification_counts"]["prompt_template_evidence"] == 1
    assert data["classification_counts"]["no_learning_signal"] == 2


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
    assert data["summary"]["canonical_contract_count"] == 7
    assert data["summary"]["implemented_or_partial_count"] >= 6
    assert {
        "TrustedSignal",
        "InvocationBackend",
        "RunLifecycleEvent",
        "KnowledgeObject",
        "RetrievalTrace",
        "WorkflowLearningEvent",
        "EvaluationFinding",
    }.issubset(names)
    invocation = next(contract for contract in data["contracts"] if contract["name"] == "InvocationBackend")
    assert invocation["status"] == "implemented"
    assert invocation["source"] == "services/invocation_backends.py"


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
    assert metadata_output["data"]["workflow_orchestration"]["latest_execution_report"]["id"] == "wr-1"
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
            "Route serious agent work through AIOS",
            "--project",
            "p1",
        ]
    )

    assert start_exit == EXIT_OK
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["command"] == "start-work"
    data = output["data"]
    assert data["run"]["status"] == "in_progress"
    assert data["run"]["session_id"] == "s1"
    assert data["packet"]["policy_mode"] == "compact-ranked"
    assert "Route serious agent work through AIOS" in data["packet"]["markdown"]
    assert "Use explicit handshakes" in data["packet"]["markdown"]
    assert "Route serious work through AIOS" in data["packet"]["markdown"]
    assert "Agent routing" in data["packet"]["markdown"]
    assert data["invocation"]["session_id"] == "s1"
    assert data["next_agent_context"]["run_id"] == data["run"]["id"]
    assert data["next_agent_context"]["invocation_id"] == data["invocation"]["id"]

    conn = sqlite3.connect(db_path)
    linked = conn.execute(
        "SELECT run_id, invocation_id, objective FROM sessions WHERE id = 's1'"
    ).fetchone()
    assert linked == (
        data["run"]["id"],
        data["invocation"]["id"],
        "Route serious agent work through AIOS",
    )
    packet_row = conn.execute(
        "SELECT run_id, packet_markdown FROM briefing_packets WHERE id = ?",
        (data["packet"]["id"],),
    ).fetchone()
    assert packet_row[0] == data["run"]["id"]
    assert "Applicable Success Criteria" in packet_row[1]
    event_count = conn.execute(
        "SELECT COUNT(*) FROM orchestration_run_events WHERE run_id = ?",
        (data["run"]["id"],),
    ).fetchone()[0]
    assert event_count == 3
    conn.close()
