from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.task_routing import route_objective  # noqa: E402


def _seed_projects(conn: sqlite3.Connection, root: Path) -> None:
    conn.executescript(
        f"""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_path TEXT NOT NULL,
            obsidian_path TEXT NOT NULL,
            status TEXT NOT NULL
        );
        INSERT INTO projects (id, name, repo_path, obsidian_path, status) VALUES
            ('p-aios', 'AIOS', '{str((root / "AIOS").resolve())}', '03 Projects/AIOS', 'active'),
            ('p-soundscape-app', 'Soundscape App', '{str((root / "Soundscape-App").resolve())}', '03 Projects/Soundscape App', 'active'),
            ('p-soundscape-web', 'Soundscape Web', '{str((root / "Soundscape-Web").resolve())}', '03 Projects/Soundscape Web', 'active');
        """
    )


def test_route_objective_uses_current_project_when_cwd_matches(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Debug the failing runtime and fix the regression",
        cwd=str((tmp_path / "AIOS" / "services").resolve()),
    ).to_json()

    assert route["status"] == "ready"
    assert route["project"]["outcome"] == "exact"
    assert route["project"]["selected_project_id"] == "p-aios"
    assert route["selected_workflow"]["workflow_key"] == "failure-recovery"
    assert route["backend_recommendation"]["selected_surface"] == "codex"


def test_route_objective_blocks_on_ambiguous_project_names(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Improve Soundscape onboarding and make it launch ready",
    ).to_json()

    assert route["status"] == "blocked"
    assert route["project"]["outcome"] == "ambiguous"
    assert route["selected_workflow"] is None
    assert len(route["project"]["candidates"]) >= 2


def test_route_objective_blocks_when_no_project_matches(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Refactor the Mars Colony telemetry importer",
    ).to_json()

    assert route["status"] == "blocked"
    assert route["project"]["outcome"] == "unsupported"
    assert route["blocked_reason"] is not None


def test_route_objective_selects_implementation_route(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Audit AIOS onboarding and ship a scoped fix with tests",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == "implementation-delivery"
    assert route["prompt_recommendation"]["prompt_family"] is not None
    assert route["workflow_candidates"][0]["rationale"]
    assert "skill_recommendations" in route
    assert "workflow_alternatives" in route
    assert "success_rate=" in route["prompt_recommendation"]["rationale"]


def test_route_objective_routes_short_bugfix_to_implementation(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Fix the AIOS start-work route metadata bug",
        explicit_project_id="p-aios",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == "implementation-delivery"
    assert route["selected_workflow"]["workflow_family"] == "audit_and_implement"


def test_route_objective_routes_login_bugfix_to_implementation(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Fix the Soundscape App login redirect bug and verify the quality checks",
        explicit_project_id="p-soundscape-app",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] in {
        "implementation-delivery",
        "failure-recovery",
    }


def test_route_objective_routes_ui_story_verification_to_code_workflow(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Verify the AIOS operator UI user stories through the real interface",
        explicit_project_id="p-aios",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == "implementation-delivery"
    assert route["selected_workflow"]["workflow_key"] != "academic_paper_v1"


def test_route_objective_routes_academic_paper_to_content_workflow(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Write an academic paper with citations about AIOS routing",
        explicit_project_id="p-aios",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == "academic_paper_v1"


def test_route_objective_selects_audit_route(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Review AIOS architecture and audit launch readiness drift",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_family"] == "audit_only"


def test_route_objective_reports_prompt_fallback_when_registry_lacks_match(tmp_path: Path) -> None:
    prompt_registry = tmp_path / "prompt-registry.json"
    prompt_registry.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "id": "content_writing",
                        "prompt_family": "content_generation",
                        "route_status": "approved",
                        "classification": "content_writing",
                        "applicable_workflow_families": ["content_generation"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Audit AIOS onboarding and ship a scoped fix with tests",
        prompt_registry_path=prompt_registry,
    ).to_json()

    assert route["status"] == "ready"
    assert route["prompt_recommendation"]["route_status"] == "missing"
    assert route["prompt_recommendation"]["prompt_family"] is None
