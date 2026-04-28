from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from typing import Any, Literal

Provenance = Literal["confirmed", "inferred", "missing", "contradictory"]


@dataclass(frozen=True)
class TrustedSignal:
    value: Any
    provenance: Provenance
    confidence: float
    source: dict[str, str]
    freshness: str
    explanation: str
    missing_reason: str | None = None
    contradiction: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return any(str(row["name"]) == column for row in conn.execute(f"PRAGMA table_info({table})").fetchall())


def _count(conn: sqlite3.Connection, table: str, where: str = "1=1") -> int:
    if not _table_exists(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE {where}").fetchone()
    return int(row["count"]) if row else 0


def _format_hour(hour: str | None, minute: str | None) -> str:
    parsed_hour = int(hour or "0")
    parsed_minute = int(minute or "0")
    suffix = "PM" if parsed_hour >= 12 else "AM"
    display_hour = 12 if parsed_hour % 12 == 0 else parsed_hour % 12
    return f"{display_hour}:{parsed_minute:02d} {suffix}"


def _parse_rrule(trigger: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for part in trigger.split(";"):
        key, separator, value = part.partition("=")
        if separator and key:
            parts[key] = value
    return parts


def automation_trigger_label(trigger: str) -> str:
    rule = _parse_rrule(trigger)
    days = [day for day in rule.get("BYDAY", "").split(",") if day]
    time = _format_hour(rule.get("BYHOUR"), rule.get("BYMINUTE"))
    if days == ["MO", "TU", "WE", "TH", "FR"]:
        return f"Weekdays at {time}"
    if set(days) == {"MO", "TU", "WE", "TH", "FR", "SA", "SU"} and len(days) == 7:
        return f"Daily at {time}"
    day_names = {
        "MO": "Mon",
        "TU": "Tue",
        "WE": "Wed",
        "TH": "Thu",
        "FR": "Fri",
        "SA": "Sat",
        "SU": "Sun",
    }
    if days:
        return f"{', '.join(day_names.get(day, day) for day in days)} at {time}"
    return trigger


def _latest_project_health(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row | None:
    if not _table_exists(conn, "standards_health_snapshots"):
        return None
    return conn.execute(
        """
        SELECT overall_score, critical_delta_count, unknown_coverage, created_at
        FROM standards_health_snapshots
        WHERE project_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()


def _project_signals(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(conn, "projects"):
        return {"items": [], "findings": []}

    columns = {
        "id": "id",
        "name": "name" if _column_exists(conn, "projects", "name") else "id",
        "status": "status" if _column_exists(conn, "projects", "status") else "'unknown'",
    }
    rows = conn.execute(
        f"""
        SELECT {columns["id"]} AS id, {columns["name"]} AS name, {columns["status"]} AS status
        FROM projects
        ORDER BY name ASC
        """
    ).fetchall()
    items: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for row in rows:
        project_id = str(row["id"])
        session_count = _count(conn, "sessions", f"project_id = '{project_id}'")
        latest_health = _latest_project_health(conn, project_id)
        if latest_health is None:
            health = TrustedSignal(
                value=None,
                provenance="missing",
                confidence=0,
                source={"label": "Standards health snapshot", "table": "standards_health_snapshots"},
                freshness="missing",
                explanation="No standards-health snapshot has been recorded for this project.",
                missing_reason="No standards_health_snapshots row exists for this project.",
            )
            findings.append(
                {
                    "surface": "projects",
                    "project_id": project_id,
                    "code": "project_health_missing",
                    "severity": "warning",
                    "summary": f"{row['name']} has no standards-health snapshot.",
                }
            )
        else:
            health = TrustedSignal(
                value=float(latest_health["overall_score"]),
                provenance="confirmed",
                confidence=0.9,
                source={"label": "Standards health snapshot", "table": "standards_health_snapshots", "field": "overall_score"},
                freshness=str(latest_health["created_at"]),
                explanation="Latest standards-health score on a 0-100 scale.",
            )

        status = TrustedSignal(
            value=str(row["status"]),
            provenance="confirmed" if session_count > 0 else "inferred",
            confidence=0.9 if session_count > 0 else 0.55,
            source={"label": "Project inventory", "table": "projects", "field": "status"},
            freshness=f"{session_count} recorded session(s)",
            explanation="Project status is persisted in inventory and qualified by linked session activity.",
            missing_reason=None if session_count > 0 else "No linked session activity has been recorded for this project.",
        )
        items.append(
            {
                "id": project_id,
                "name": str(row["name"]),
                "health_score": health.to_json(),
                "status": status.to_json(),
            }
        )

    return {"items": items, "findings": findings}


def _rtk_signals(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(conn, "rtk_compression_events"):
        return {
            "state": TrustedSignal(
                value="inactive",
                provenance="missing",
                confidence=0,
                source={"label": "RTK compression events", "table": "rtk_compression_events"},
                freshness="missing",
                explanation="RTK telemetry is not active because the compression event table does not exist.",
                missing_reason="rtk_compression_events table does not exist.",
            ).to_json(),
            "metrics": {"events": 0, "raw_tokens": 0, "compressed_tokens": 0, "tokens_saved": 0},
            "findings": [],
        }

    row = conn.execute(
        """
        SELECT
          COUNT(*) AS events,
          COALESCE(SUM(estimated_raw_tokens), 0) AS raw_tokens,
          COALESCE(SUM(estimated_compressed_tokens), 0) AS compressed_tokens,
          COALESCE(SUM(MAX(estimated_raw_tokens - estimated_compressed_tokens, 0)), 0) AS tokens_saved
        FROM rtk_compression_events
        """
    ).fetchone()
    events = int(row["events"])
    tokens_saved = int(row["tokens_saved"])
    state = "no_eligible_data" if events == 0 else "active" if tokens_saved > 0 else "inactive"
    return {
        "state": TrustedSignal(
            value=state,
            provenance="missing" if events == 0 else "confirmed",
            confidence=0.45 if events == 0 else 0.9,
            source={"label": "RTK compression events", "table": "rtk_compression_events"},
            freshness="no events" if events == 0 else "all recorded events",
            explanation=(
                "RTK is wired, but no compression events have been recorded."
                if events == 0
                else "RTK has recorded compression events."
            ),
            missing_reason="No eligible command output has produced an RTK telemetry event." if events == 0 else None,
        ).to_json(),
        "metrics": {
            "events": events,
            "raw_tokens": int(row["raw_tokens"]),
            "compressed_tokens": int(row["compressed_tokens"]),
            "tokens_saved": tokens_saved,
        },
        "findings": [],
    }


def _automation_signals() -> dict[str, Any]:
    seeded = [
        ("automation-1", "Daily ingest status", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0", 0.97, "healthy"),
        ("automation-2", "PR health report", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=11;BYMINUTE=30", 0.83, "warning"),
        ("automation-3", "Nightly import verify", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA,SU;BYHOUR=1;BYMINUTE=0", 0.62, "error"),
    ]
    items = []
    for automation_id, name, trigger, success_rate, status in seeded:
        label = automation_trigger_label(trigger)
        items.append(
            {
                "id": automation_id,
                "name": name,
                "trigger": TrustedSignal(
                    value=label,
                    provenance="inferred",
                    confidence=0.8,
                    source={"label": "Seeded automation schedule", "field": "trigger"},
                    freshness="seeded",
                    explanation="Readable schedule inferred from the persisted RRULE trigger.",
                ).to_json(),
                "success_rate": TrustedSignal(
                    value=success_rate,
                    provenance="inferred",
                    confidence=0.7,
                    source={"label": "Seeded automation health", "field": "successRate"},
                    freshness="seeded",
                    explanation="Success rate is seeded until durable automation run history is available.",
                ).to_json(),
                "status": TrustedSignal(
                    value=status,
                    provenance="inferred",
                    confidence=0.7,
                    source={"label": "Seeded automation health", "field": "status"},
                    freshness="seeded",
                    explanation="Status is seeded until durable automation run history is available.",
                ).to_json(),
            }
        )
    return {"items": items, "findings": []}


def capability_truth_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    projects = _project_signals(conn)
    rtk = _rtk_signals(conn)
    automations = _automation_signals()
    findings = [*projects["findings"], *rtk["findings"], *automations["findings"]]
    return {
        "summary": {
            "surfaces": 3,
            "findings": len(findings),
            "contract": "TrustedSignal(value, provenance, confidence, source, freshness, explanation, missing_reason, contradiction)",
        },
        "projects": projects,
        "rtk": rtk,
        "automations": automations,
        "findings": findings,
    }
