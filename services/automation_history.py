from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.capability_truth import ensure_automation_run_history_schema

PIPELINE_AUTOMATION = {
    "id": "automation-1",
    "name": "Daily ingest status",
    "trigger": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0",
}

_LOG_LINE_RE = re.compile(r"^(?P<timestamp>\S+) \[pipeline\] (?P<message>.*)$")
_SUMMARY_RE = re.compile(r"(?P<ok>\d+) ok, (?P<skipped>\d+) skipped, (?P<failed>\d+) failed")


@dataclass(frozen=True)
class PipelineRun:
    started_at: str
    completed_at: str
    ok_count: int
    skipped_count: int
    failed_count: int

    @property
    def status(self) -> str:
        return "success" if self.failed_count == 0 else "failed"

    @property
    def failure_summary(self) -> str | None:
        if self.failed_count == 0:
            return None
        return f"{self.failed_count} pipeline phase(s) failed."


def _history_id(run: PipelineRun) -> str:
    digest = hashlib.sha256(f"{PIPELINE_AUTOMATION['id']}:{run.started_at}".encode()).hexdigest()[:16]
    return f"automation-history-{digest}"


def parse_pipeline_runs(log_path: Path) -> list[PipelineRun]:
    if not log_path.exists():
        return []

    runs: list[PipelineRun] = []
    active_start: str | None = None
    completed_at: str | None = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _LOG_LINE_RE.match(line)
        if not match:
            continue
        timestamp = match.group("timestamp")
        message = match.group("message")
        if message == "=== AIOS daily pipeline starting ===":
            active_start = timestamp
            completed_at = None
            continue
        if message == "=== pipeline complete ===" and active_start:
            completed_at = timestamp
            continue
        summary_match = _SUMMARY_RE.search(message)
        if active_start and completed_at and summary_match:
            runs.append(
                PipelineRun(
                    started_at=active_start,
                    completed_at=completed_at,
                    ok_count=int(summary_match.group("ok")),
                    skipped_count=int(summary_match.group("skipped")),
                    failed_count=int(summary_match.group("failed")),
                )
            )
            active_start = None
            completed_at = None
    return runs


def sync_pipeline_automation_history(conn: sqlite3.Connection, *, logs_dir: Path) -> dict[str, Any]:
    ensure_automation_run_history_schema(conn)
    log_path = logs_dir / "pipeline.log"
    runs = parse_pipeline_runs(log_path)
    inserted_or_updated = 0
    for run in runs:
        metadata = {
            "source": "pipeline.log",
            "ok_count": run.ok_count,
            "skipped_count": run.skipped_count,
            "failed_count": run.failed_count,
        }
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR REPLACE INTO automation_run_history (
              id,
              automation_id,
              automation_name,
              scheduled_trigger,
              expected_next_run_at,
              started_at,
              completed_at,
              status,
              failure_summary,
              approval_blockers_json,
              writeback_blockers_json,
              metadata_json
            )
            VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, '[]', '[]', ?)
            """,
            (
                _history_id(run),
                PIPELINE_AUTOMATION["id"],
                PIPELINE_AUTOMATION["name"],
                PIPELINE_AUTOMATION["trigger"],
                run.started_at,
                run.completed_at,
                run.status,
                run.failure_summary,
                json.dumps(metadata, sort_keys=True),
            ),
        )
        if conn.total_changes > before:
            inserted_or_updated += 1
    conn.commit()
    return {
        "summary": {
            "source": str(log_path),
            "parsed_run_count": len(runs),
            "inserted_or_updated_count": inserted_or_updated,
        },
        "automation": PIPELINE_AUTOMATION,
        "latest_run": {
            "started_at": runs[-1].started_at,
            "completed_at": runs[-1].completed_at,
            "status": runs[-1].status,
            "failed_count": runs[-1].failed_count,
        }
        if runs
        else None,
    }
