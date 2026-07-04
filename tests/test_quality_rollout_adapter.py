from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.evidence_artifacts import list_evidence_artifacts  # noqa: E402
from services.quality_rollout_adapter import launch_quality_rollout  # noqa: E402


def test_quality_rollout_adapter_captures_artifacts_and_records_evidence(tmp_path: Path) -> None:
    conn = sqlite3.connect(":memory:")
    output_dir = tmp_path / "rollout"

    def rollout_stub(**kwargs: object) -> dict[str, object]:
        output_path = Path(str(kwargs["output_dir"]))
        output_path.mkdir(parents=True)
        report_path = output_path / "001-demo-controller-report.json"
        validation_path = output_path / "001-demo-controller-report-validation.json"
        ledger_path = output_path / "rollout-ledger.json"
        report_path.write_text('{"schema":"quality-runner-controller-report-v0.1"}\n')
        validation_path.write_text('{"status":"accepted"}\n')
        ledger_path.write_text('{"schema":"quality-runner-rollout-ledger-v0.1"}\n')
        return {
            "schema": "quality-runner-rollout-result-v0.1",
            "status": "completed",
            "run_id_prefix": kwargs["run_id_prefix"],
            "output_dir": str(output_path),
            "ledger_path": str(ledger_path),
            "repo_count": 1,
            "accepted_reports": 1,
            "rejected_reports": 0,
            "failed_repos": [],
            "fleet_documents": {"phase_md": str(output_path / "fleet-remediation-phases.md")},
            "results": [
                {
                    "repo_path": "/tmp/demo",
                    "report_path": str(report_path),
                    "validation_path": str(validation_path),
                    "artifact_path": "/tmp/demo/.quality-runner/runs/demo-verify",
                }
            ],
        }

    payload = launch_quality_rollout(
        conn=conn,
        repo_list_path=None,
        repos=["/tmp/demo"],
        run_id_prefix="demo-rollout",
        output_dir=output_dir,
        profile=None,
        ci_status_json=None,
        timeout_seconds=120,
        workflow_timeout_seconds=None,
        verify_timeout_seconds=None,
        workflow_timeout_reason=None,
        total_timeout_seconds=None,
        total_timeout_reason=None,
        checkout_most_advanced_branch=False,
        allow_mutating_gates=False,
        task_id="task-1",
        run_id="run-1",
        session_id="session-1",
        rollout_func=rollout_stub,
    )

    index_path = Path(str(payload["artifact_index_path"]))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows = list_evidence_artifacts(conn, run_id="run-1")

    assert payload["schema"] == "aios-quality-rollout-adapter-v0.1"
    assert payload["controller_report_paths"] == [
        str(output_dir / "001-demo-controller-report.json")
    ]
    assert index["controller_report_paths"] == payload["controller_report_paths"]
    assert rows[0]["status"] == "pass"
    assert rows[0]["phase"] == "quality-rollout"
    assert rows[0]["parsed_summary"]
