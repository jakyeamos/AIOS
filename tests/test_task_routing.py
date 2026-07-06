from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.task_routing import route_objective  # noqa: E402
from services.workflow_orchestration import recommend_route_primitives  # noqa: E402


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


def test_route_objective_routes_gsd_phase_add_to_planning_governance(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Add a new GSD phase for planning governance",
        explicit_project_id="p-aios",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == "planning-governance"
    assert route["selected_workflow"]["workflow_family"] == "planning_governance"
    assert route["task_family"] == "audit_and_implement"
    assert "planning" in route["agent_recommendation"]["rationale"].lower()
    assert any(
        candidate["workflow_key"] == "planning-governance"
        and "planning detection" in candidate["rationale"]
        for candidate in route["workflow_candidates"]
    )


def test_route_objective_routes_known_gsd_execute_command_to_governed_lane(
    tmp_path: Path,
) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="gsd-execute-phase 24",
        explicit_project_id="p-aios",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == "implementation-delivery"
    assert route["task_family"] == "audit_and_implement"
    assert any(
        candidate["workflow_key"] == "implementation-delivery"
        and "GSD command" in candidate["rationale"]
        for candidate in route["workflow_candidates"]
    )


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


def test_route_objective_routes_investigation_language_to_audit(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective=(
            "Investigate why route-blocked happens for unmatched objectives and determine "
            "whether routing should be fixed"
        ),
        explicit_project_id="p-aios",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_family"] == "audit_only"


def test_route_objective_routes_tmcp_expert_rubric_to_expert_workflow(
    tmp_path: Path,
) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    for objective in (
        "Run the TMCP expert-rubric workflow for AIOS review evidence",
        "Use the TMCP expert workflow",
        "Use the TMCP expert workflow to judge this for AIOS",
        "Judge this with TMCP",
        "Judge this with TMCP for AIOS",
        "TMCP judge this AIOS routing evidence",
        "Use the TMCP expert UI rubric on Hoopscout",
    ):
        route = route_objective(
            conn,
            objective=objective,
            explicit_project_id="p-aios",
        ).to_json()

        assert route["status"] == "ready", objective
        assert route["selected_workflow"]["workflow_key"] == "expert_rubric_remediation_v1"
        assert route["selected_workflow"]["workflow_family"] == "audit_and_plan"


def test_route_objective_routes_quality_gate_adoption_to_gate_workflow(
    tmp_path: Path,
) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Create a quality gate adoption plan for this repo's commit gates",
        explicit_project_id="p-aios",
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == "repo_gate_adoption_v1"
    assert route["selected_workflow"]["workflow_family"] == "audit_and_plan"


def test_semantic_reasoner_routes_high_confidence_no_match() -> None:
    seen_request: dict[str, Any] = {}

    def reasoner(request: dict[str, object]) -> dict[str, object]:
        seen_request.update(request)
        return {
            "selected_workflow": "implementation-delivery",
            "confidence": 0.86,
            "rationale": "The user is asking AIOS to add a new routing capability.",
            "alternatives": [
                {"workflow_key": "divergent-strategy", "confidence": 0.41},
            ],
        }

    route = recommend_route_primitives(
        "Make the router understand intent instead of depending on exact words",
        semantic_reasoner=reasoner,
    )

    assert route["selected_workflow"]["workflow_key"] == "implementation-delivery"
    assert route["selected_workflow"]["routing_source"] == "semantic_reasoner"
    assert route["semantic_recommendation"]["confidence"] == 0.86
    assert (
        seen_request["objective"]
        == "Make the router understand intent instead of depending on exact words"
    )
    assert any(
        item["workflow_key"] == "implementation-delivery"
        for item in seen_request["available_workflows"]
    )


def test_semantic_reasoner_blocks_low_confidence_no_match() -> None:
    def reasoner(_request: dict[str, object]) -> dict[str, object]:
        return {
            "selected_workflow": "implementation-delivery",
            "confidence": 0.52,
            "rationale": "The request could mean implementation or planning.",
            "alternatives": [
                {"workflow_key": "divergent-strategy", "confidence": 0.49},
            ],
        }

    route = recommend_route_primitives(
        "Make it more flexible somehow",
        semantic_reasoner=reasoner,
    )

    assert route["selected_workflow"] is None
    assert route["semantic_recommendation"]["selected_workflow"] == "implementation-delivery"
    assert route["blocked_reason"] == "Semantic workflow confidence was below the route threshold."


def test_route_objective_accepts_semantic_reasoner(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    def reasoner(_request: dict[str, object]) -> dict[str, object]:
        return {
            "selected_workflow": "implementation-delivery",
            "confidence": 0.9,
            "rationale": "The objective asks for a routing implementation change.",
        }

    route = route_objective(
        conn,
        objective="Make the router understand intent instead of depending on exact words",
        explicit_project_id="p-aios",
        semantic_reasoner=reasoner,
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["routing_source"] == "semantic_reasoner"
    assert route["semantic_recommendation"]["confidence"] == 0.9


def test_route_objective_uses_configured_semantic_router_command(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    completed = type(
        "Completed",
        (),
        {
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "selected_workflow": "implementation-delivery",
                    "confidence": 0.91,
                    "rationale": "The objective asks for a routing implementation change.",
                }
            ),
            "stderr": "",
        },
    )()

    with (
        patch.dict(
            "os.environ",
            {"AIOS_WORKFLOW_SEMANTIC_ROUTER_CMD": "semantic-router --json"},
        ),
        patch("services.semantic_workflow_routing.subprocess.run", return_value=completed) as run,
    ):
        route = route_objective(
            conn,
            objective="Make the router understand intent instead of depending on exact words",
            explicit_project_id="p-aios",
        ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["routing_source"] == "semantic_reasoner"
    assert route["semantic_recommendation"]["confidence"] == 0.91
    assert run.call_args.args[0] == ["semantic-router", "--json"]
    request = json.loads(run.call_args.kwargs["input"])
    assert (
        request["objective"]
        == "Make the router understand intent instead of depending on exact words"
    )


def test_configured_semantic_router_command_failure_blocks_without_crashing(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_projects(conn, tmp_path)

    with (
        patch.dict(
            "os.environ",
            {"AIOS_WORKFLOW_SEMANTIC_ROUTER_CMD": "semantic-router --json"},
        ),
        patch(
            "services.semantic_workflow_routing.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["semantic-router", "--json"], 20),
        ),
    ):
        route = route_objective(
            conn,
            objective="Make the router understand intent instead of depending on exact words",
            explicit_project_id="p-aios",
        ).to_json()

    assert route["status"] == "blocked"
    assert route["semantic_recommendation"]["status"] == "invalid_workflow"
    assert "timed out" in route["semantic_recommendation"]["rationale"]


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
