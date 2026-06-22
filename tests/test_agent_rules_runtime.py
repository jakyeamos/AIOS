from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from services.agent_rules import agent_rules_context, load_agent_rules  # noqa: E402


def _load_session_start_module():
    module_path = ROOT / "bin" / "hook-session-start.py"
    spec = importlib.util.spec_from_file_location("hook_session_start", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_sync_installed_skills_module():
    module_path = ROOT / "bin" / "sync-installed-skills.py"
    spec = importlib.util.spec_from_file_location("sync_installed_skills", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_rules_loader_parses_config_rules() -> None:
    rules = load_agent_rules()

    assert [rule.title for rule in rules[:2]] == [
        "Surface conflicts, don't average them",
        "Read before you write",
    ]
    assert "Before adding code in a file" in rules[1].body
    assert "Fail loud" in agent_rules_context()


def test_session_packet_includes_agent_rules(monkeypatch) -> None:
    module = _load_session_start_module()
    monkeypatch.setattr(module, "vault_search", lambda _args: {"results": [], "count": 0})
    monkeypatch.setattr(module, "get_active_rules", lambda _conn, max_rules=3: [])
    monkeypatch.setattr(module, "get_review_queue_hint", lambda _conn: None)
    monkeypatch.setattr(module, "get_open_bug", lambda _conn, _project_id: None)
    monkeypatch.setattr(module, "get_cts_context", lambda _cwd, _objective: None)
    monkeypatch.setattr(module, "preview_applicable_criteria", lambda **_kwargs: {"criteria": []})
    monkeypatch.setattr(
        module,
        "resolve_task_standards",
        lambda **_kwargs: {"criteria": [], "standards": [], "execution_first_triggers": []},
    )

    packet = module.generate_packet(
        project_name="AIOS",
        project_id="project-1",
        conn=sqlite3.connect(":memory:"),
        cwd=str(ROOT),
        objective="Wire agent rules into session startup",
    )

    assert "**AIOS agent rules:**" in packet
    assert "Read before you write" in packet
    assert "Fail loud" in packet


def test_session_packet_includes_user_story_loop_for_app_verification(monkeypatch) -> None:
    module = _load_session_start_module()
    monkeypatch.setattr(module, "vault_search", lambda _args: {"results": [], "count": 0})
    monkeypatch.setattr(module, "get_active_rules", lambda _conn, max_rules=3: [])
    monkeypatch.setattr(module, "get_review_queue_hint", lambda _conn: None)
    monkeypatch.setattr(module, "get_open_bug", lambda _conn, _project_id: None)
    monkeypatch.setattr(module, "get_cts_context", lambda _cwd, _objective: None)
    monkeypatch.setattr(
        module,
        "resolve_task_standards",
        lambda **_kwargs: {"criteria": [], "standards": [], "execution_first_triggers": []},
    )

    packet = module.generate_packet(
        project_name="AIOS",
        project_id="project-1",
        conn=sqlite3.connect(":memory:"),
        cwd=str(ROOT),
        objective="Verify every feature in this app and fix UX errors",
    )

    assert "**User-story verification loop:**" in packet
    assert ".planning/user-story-verification.csv" in packet
    assert "`expected_behavior`" in packet
    assert "`retest_status`" in packet


def test_session_packet_skips_user_story_loop_for_narrow_backend_work(monkeypatch) -> None:
    module = _load_session_start_module()
    monkeypatch.setattr(module, "vault_search", lambda _args: {"results": [], "count": 0})
    monkeypatch.setattr(module, "get_active_rules", lambda _conn, max_rules=3: [])
    monkeypatch.setattr(module, "get_review_queue_hint", lambda _conn: None)
    monkeypatch.setattr(module, "get_open_bug", lambda _conn, _project_id: None)
    monkeypatch.setattr(module, "get_cts_context", lambda _cwd, _objective: None)
    monkeypatch.setattr(
        module,
        "resolve_task_standards",
        lambda **_kwargs: {"criteria": [], "standards": [], "execution_first_triggers": []},
    )

    packet = module.generate_packet(
        project_name="AIOS",
        project_id="project-1",
        conn=sqlite3.connect(":memory:"),
        cwd=str(ROOT),
        objective="Rename this helper and update its unit test",
    )

    assert "**User-story verification loop:**" not in packet


def test_session_packet_includes_resume_snapshot(monkeypatch) -> None:
    module = _load_session_start_module()
    monkeypatch.setattr(module, "vault_search", lambda _args: {"results": [], "count": 0})
    monkeypatch.setattr(module, "get_active_rules", lambda _conn, max_rules=3: [])
    monkeypatch.setattr(module, "get_review_queue_hint", lambda _conn: None)
    monkeypatch.setattr(module, "get_open_bug", lambda _conn, _project_id: None)
    monkeypatch.setattr(module, "get_cts_context", lambda _cwd, _objective: None)
    monkeypatch.setattr(module, "preview_applicable_criteria", lambda **_kwargs: {"criteria": []})
    monkeypatch.setattr(
        module,
        "resolve_task_standards",
        lambda **_kwargs: {"criteria": [], "standards": [], "execution_first_triggers": []},
    )

    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
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
            resume_snapshot_json TEXT DEFAULT '{}'
        );
        """
    )
    conn.execute(
        """
        INSERT INTO orchestration_runs (id, status, resume_snapshot_json)
        VALUES ('run-1', 'waiting_for_user', ?)
        """,
        (
            '{"current_stage":"awaiting_approval","next_recommended_action":"Review pending writeback.","pending_approval_count":1}',
        ),
    )
    conn.execute(
        """
        INSERT INTO sessions (id, run_id, runtime_metadata_json)
        VALUES ('session-1', 'run-1', '{}')
        """
    )

    packet = module.generate_packet(
        project_name="AIOS",
        project_id="project-1",
        conn=conn,
        cwd=str(ROOT),
        objective="Resume serious work",
        session_id="session-1",
    )

    assert "**Resume snapshot:**" in packet
    assert "awaiting_approval" in packet
    assert "Review pending writeback." in packet


def test_session_packet_includes_standards_resolution(monkeypatch) -> None:
    module = _load_session_start_module()
    monkeypatch.setattr(module, "vault_search", lambda _args: {"results": [], "count": 0})
    monkeypatch.setattr(module, "get_active_rules", lambda _conn, max_rules=3: [])
    monkeypatch.setattr(module, "get_review_queue_hint", lambda _conn: None)
    monkeypatch.setattr(module, "get_open_bug", lambda _conn, _project_id: None)
    monkeypatch.setattr(module, "get_cts_context", lambda _cwd, _objective: None)
    monkeypatch.setattr(
        module,
        "resolve_task_standards",
        lambda **_kwargs: {
            "criteria": [{"id": "execution-first-verification", "blocking": True}],
            "standards": [
                {
                    "standard_id": "testing.trust_signal",
                    "domain": "testing",
                    "weight": 8,
                }
            ],
            "execution_first_triggers": ["core/shared logic modification"],
        },
    )

    packet = module.generate_packet(
        project_name="AIOS",
        project_id="project-1",
        conn=sqlite3.connect(":memory:"),
        cwd=str(ROOT),
        objective="Implement workflow state update",
    )

    assert "**Applicable success criteria:**" in packet
    assert "execution-first-verification" in packet
    assert "**Applicable standards:**" in packet
    assert "testing.trust_signal" in packet
    assert "**Execution-first triggers:**" in packet
    assert "core/shared logic modification" in packet


def test_synced_installed_skill_preserves_source_metadata(tmp_path: Path) -> None:
    module = _load_sync_installed_skills_module()
    skill_dir = tmp_path / "example-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: example-skill
description: Generate focused implementation output
---

Body.
""",
        encoding="utf-8",
    )

    spec = module.skill_from_file(skill_dir)

    assert spec is not None
    assert spec["source_path"] == str(skill_md)
    assert spec["installed_name"] == "example-skill"
    assert not any(key.startswith("_") for key in spec)
