from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.quality_pipeline import (  # noqa: E402
    ensure_quality_pipeline_schema,
    get_project_quality_pipeline,
)


def _base_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          repo_path TEXT NOT NULL,
          obsidian_path TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO projects (id, name, repo_path, obsidian_path, status)
        VALUES ('soundscape-app', 'soundscape-app', '~/Projects/soundscape-app', '.', 'active')
        """
    )
    ensure_quality_pipeline_schema(conn)
    return conn


def test_soundscape_standard_pipeline_uses_latest_gate_results(tmp_path: Path) -> None:
    config_path = tmp_path / "quality-pipeline.json"
    config_path.write_text(
        json.dumps(
            {
                "standard": {
                    "version": "2026-04-26",
                    "gates": [
                        {"key": "lint", "label": "Lint", "required": True},
                        {"key": "typecheck", "label": "Typecheck", "required": True},
                        {"key": "test", "label": "Test", "required": True},
                        {"key": "build", "label": "Build", "required": True},
                        {"key": "architecture", "label": "Architecture", "required": True},
                    ],
                },
                "projects": [
                    {
                        "project_id": "soundscape-app",
                        "full_pipeline": True,
                        "gates": {
                            "lint": {"command": "pnpm lint"},
                            "typecheck": {"command": "pnpm typecheck"},
                            "test": {"command": "pnpm test"},
                            "build": {"command": "pnpm build"},
                            "architecture": {"command": "node scripts/aios-architecture-check.mjs"},
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    conn = _base_conn()
    conn.execute(
        """
        INSERT INTO quality_pipeline_runs (
          id, project_id, gate_key, command, status, source, evidence_json, started_at, completed_at
        )
        VALUES (
          'run-lint', 'soundscape-app', 'lint', 'pnpm lint', 'pass', 'local',
          '["lint ok"]', '2026-04-26T00:00:00Z', '2026-04-26T00:01:00Z'
        )
        """
    )
    conn.commit()

    summary = get_project_quality_pipeline(conn, "soundscape-app", config_path=config_path)

    assert summary["overall_status"] == "warning"
    assert summary["full_pipeline"] is True
    assert summary["coverage"]["configured_required"] == 5
    lint_gate = next(gate for gate in summary["gates"] if gate["key"] == "lint")
    build_gate = next(gate for gate in summary["gates"] if gate["key"] == "build")
    assert lint_gate["status"] == "pass"
    assert lint_gate["latest_run_id"] == "run-lint"
    assert build_gate["status"] == "stale"
    assert build_gate["command"] == "pnpm build"


def test_missing_required_gate_is_visible(tmp_path: Path) -> None:
    config_path = tmp_path / "quality-pipeline.json"
    config_path.write_text(
        json.dumps(
            {
                "standard": {
                    "version": "2026-04-26",
                    "gates": [
                        {"key": "lint", "label": "Lint", "required": True},
                        {"key": "typecheck", "label": "Typecheck", "required": True},
                    ],
                },
                "projects": [
                    {
                        "project_id": "soundscape-app",
                        "gates": {
                            "lint": {"command": "pnpm lint"},
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    conn = _base_conn()

    summary = get_project_quality_pipeline(conn, "soundscape-app", config_path=config_path)

    assert summary["overall_status"] == "error"
    missing = next(gate for gate in summary["gates"] if gate["key"] == "typecheck")
    assert missing["status"] == "missing"
    assert missing["required"] is True


def test_pipeline_config_matches_generated_project_ids_by_name(tmp_path: Path) -> None:
    config_path = tmp_path / "quality-pipeline.json"
    config_path.write_text(
        json.dumps(
            {
                "standard": {
                    "version": "2026-04-26",
                    "gates": [{"key": "lint", "label": "Lint", "required": True}],
                },
                "projects": [
                    {
                        "project_id": "soundscape-app",
                        "gates": {"lint": {"command": "pnpm lint"}},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    conn = _base_conn()
    conn.execute("UPDATE projects SET id = 'fc3a2cf7bb27c243' WHERE id = 'soundscape-app'")
    conn.commit()

    summary = get_project_quality_pipeline(conn, "fc3a2cf7bb27c243", config_path=config_path)

    assert summary["project_id"] == "fc3a2cf7bb27c243"
    assert summary["coverage"]["configured_required"] == 1
    assert summary["gates"][0]["command"] == "pnpm lint"
