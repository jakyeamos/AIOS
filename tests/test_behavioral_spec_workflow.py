from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.project_maturity import (  # noqa: E402
    BEHAVIORAL_SPEC_WORKFLOW_KEY,
    assess_behavioral_spec_eligibility,
)
from services.task_routing import route_objective  # noqa: E402
from services.workflow_orchestration import (  # noqa: E402
    load_skill_registry,
    load_workflow_registry,
    validate_workflow_bindings,
)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_project(conn: sqlite3.Connection, root: Path) -> None:
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
            ('p-target', 'Target App', '{str(root.resolve())}', '03 Projects/Target App', 'active');
        """
    )


def _make_mature_next_app(root: Path) -> None:
    for name in (
        "dashboard",
        "settings",
        "admin",
        "search",
        "billing",
        "imports",
        "exports",
        "users",
    ):
        _write(root / "app" / name / "page.tsx", "export default function Page() { return null }\n")
    for name in ("users", "search", "billing", "imports", "exports"):
        _write(root / "app" / "api" / name / "route.ts", "export async function GET() {}\n")
    _write(root / "app" / "actions.ts", "export async function saveSettings() {}\n")
    _write(root / "middleware.ts", "export function middleware() { return null }\n")
    _write(root / "prisma" / "schema.prisma", "model User { id String @id }\n")
    _write(root / "tests" / "smoke.test.ts", "test('smoke', () => {})\n")
    _write(root / "components" / "AdminSearchPanel.tsx", "export function AdminSearchPanel() {}\n")


def test_mature_repo_is_eligible_with_explained_signals(tmp_path: Path) -> None:
    _make_mature_next_app(tmp_path)

    report = assess_behavioral_spec_eligibility(tmp_path)

    assert report.eligible is True
    assert report.passed_count >= 4
    assert report.signals["routes_or_screens"].passed is True
    assert report.signals["api_endpoints_or_server_actions"].passed is True
    assert report.signals["auth_or_permissions"].passed is True
    assert report.signals["persistent_data_model"].passed is True
    assert report.recommended_workflow == BEHAVIORAL_SPEC_WORKFLOW_KEY
    assert report.to_json()["signals"]["routes_or_screens"]["evidence"]


def test_small_repo_is_not_eligible_and_gets_lighter_recommendation(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "index.ts", "export const answer = 42\n")

    report = assess_behavioral_spec_eligibility(tmp_path)

    assert report.eligible is False
    assert report.passed_count < report.min_signals_required
    assert report.recommended_workflow != BEHAVIORAL_SPEC_WORKFLOW_KEY
    assert "basic smoke test loop" in report.lighter_recommendations


def test_explicit_opt_in_can_enable_workflow_for_small_repo(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "index.ts", "export const answer = 42\n")

    report = assess_behavioral_spec_eligibility(tmp_path, explicit_opt_in=True)

    assert report.eligible is True
    assert report.explicit_opt_in is True
    assert report.recommended_workflow == BEHAVIORAL_SPEC_WORKFLOW_KEY


def test_registered_workflow_contains_required_phases_schema_and_evidence_rules() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")

    workflow = workflows[BEHAVIORAL_SPEC_WORKFLOW_KEY]

    assert validate_workflow_bindings(workflows, skills) == []
    assert workflow.lifecycle_state == "candidate"
    assert [stage.key for stage in workflow.stages] == [
        "plan",
        "catalog_and_spec",
        "coverage_audit",
        "test",
        "fix",
        "re_test",
        "regression_cover",
        "boundary_audit",
        "final_report",
    ]
    contract = "\n".join(workflow.output_contract)
    assert "Feature ID" in contract
    assert "Last tested commit" in contract
    assert "No row may be marked Verified unless it has evidence" in contract
    assert "No row may be marked Regression-Covered unless" in contract
    assert "thermo-nuclear-simplification" in contract


def test_explicit_route_blocks_small_repo_with_eligibility_report(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "index.ts", "export const answer = 42\n")
    conn = sqlite3.connect(":memory:")
    _seed_project(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Run the behavioral-spec-verification-loop for Target App",
        cwd=str(tmp_path),
    ).to_json()

    assert route["status"] == "blocked"
    assert route["selected_workflow"]["workflow_key"] == BEHAVIORAL_SPEC_WORKFLOW_KEY
    assert route["blocked_reason"]
    assert route["maturity_report"]["eligible"] is False
    assert "basic smoke test loop" in route["maturity_report"]["lighter_recommendations"]


def test_explicit_route_allows_manual_override_with_eligibility_report(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "index.ts", "export const answer = 42\n")
    conn = sqlite3.connect(":memory:")
    _seed_project(conn, tmp_path)

    route = route_objective(
        conn,
        objective=("Run the behavioral-spec-verification-loop for Target App with explicit opt-in"),
        cwd=str(tmp_path),
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] == BEHAVIORAL_SPEC_WORKFLOW_KEY
    assert route["maturity_report"]["eligible"] is True
    assert route["maturity_report"]["explicit_opt_in"] is True


def test_behavioral_spec_workflow_does_not_become_default_lightweight_route(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    _seed_project(conn, tmp_path)

    route = route_objective(
        conn,
        objective="Audit Target App and ship a scoped fix with tests",
        cwd=str(tmp_path),
    ).to_json()

    assert route["status"] == "ready"
    assert route["selected_workflow"]["workflow_key"] != BEHAVIORAL_SPEC_WORKFLOW_KEY
