from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from services.rtk_integration import classify_rtk_metrics

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


def _project_health_state(latest_health: sqlite3.Row | None, repo_path: str | None) -> str:
    if repo_path and not Path(repo_path).expanduser().exists():
        return "missing_source"
    if latest_health is None:
        return "missing_snapshot"
    score = float(latest_health["overall_score"])
    if score >= 80:
        return "healthy"
    if score >= 50:
        return "degraded"
    return "unknown"


def _project_status_value(status: str, session_count: int, health_state: str) -> str:
    if health_state == "missing_source":
        return "missing_source"
    if status == "active" and session_count > 0:
        return "active_with_sessions"
    if status == "active":
        return "active_no_sessions"
    return status


def _project_signals(conn: sqlite3.Connection) -> dict[str, Any]:
    if not _table_exists(conn, "projects"):
        return {"items": [], "findings": []}

    columns = {
        "id": "id",
        "name": "name" if _column_exists(conn, "projects", "name") else "id",
        "status": "status" if _column_exists(conn, "projects", "status") else "'unknown'",
        "repo_path": "repo_path" if _column_exists(conn, "projects", "repo_path") else "NULL",
    }
    rows = conn.execute(
        f"""
        SELECT
          {columns["id"]} AS id,
          {columns["name"]} AS name,
          {columns["status"]} AS status,
          {columns["repo_path"]} AS repo_path
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
        repo_path = str(row["repo_path"]) if row["repo_path"] else None
        health_state_value = _project_health_state(latest_health, repo_path)
        if health_state_value == "missing_source":
            health = TrustedSignal(
                value=None,
                provenance="missing",
                confidence=0,
                source={"label": "Project repository", "table": "projects", "field": "repo_path"},
                freshness="missing",
                explanation="Project repository path is missing or does not exist, so health cannot be evaluated.",
                missing_reason=f"Project repo_path is not available on disk: {repo_path}",
            )
            findings.append(
                {
                    "surface": "projects",
                    "project_id": project_id,
                    "code": "project_missing_source",
                    "severity": "warning",
                    "summary": f"{row['name']} has no available repository source.",
                    "source": {"label": "Project repository", "table": "projects", "field": "repo_path"},
                    "freshness": "missing",
                    "confidence": 0,
                    "missing_reason": f"Project repo_path is not available on disk: {repo_path}",
                }
            )
        elif latest_health is None:
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
                    "source": {"label": "Standards health snapshot", "table": "standards_health_snapshots"},
                    "freshness": "missing",
                    "confidence": 0,
                    "missing_reason": "No standards_health_snapshots row exists for this project.",
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

        health_state = TrustedSignal(
            value=health_state_value,
            provenance="missing" if health_state_value.startswith("missing_") else "confirmed",
            confidence=0 if health_state_value.startswith("missing_") else 0.85,
            source={"label": "Project health state", "table": "projects"},
            freshness=health.freshness,
            explanation="Project health subtype derived from repository availability and latest standards-health snapshot.",
            missing_reason=health.missing_reason if health_state_value.startswith("missing_") else None,
        )
        status_value = _project_status_value(str(row["status"]), session_count, health_state_value)
        status = TrustedSignal(
            value=status_value,
            provenance="confirmed" if session_count > 0 else "inferred",
            confidence=0.9 if session_count > 0 else 0.55,
            source={"label": "Project inventory", "table": "projects", "field": "status"},
            freshness=f"{session_count} recorded session(s)",
            explanation="Project status is persisted in inventory and qualified by linked session activity and source availability.",
            missing_reason=None if session_count > 0 else "No linked session activity has been recorded for this project.",
        )
        items.append(
            {
                "id": project_id,
                "name": str(row["name"]),
                "health_score": health.to_json(),
                "health_state": health_state.to_json(),
                "status": status.to_json(),
                "repo_path": repo_path,
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
    metrics = {
        "event_count": events,
        "raw_tokens": int(row["raw_tokens"]),
        "compressed_tokens": int(row["compressed_tokens"]),
        "tokens_saved": int(row["tokens_saved"]),
    }
    classification = classify_rtk_metrics(metrics)
    findings = []
    if classification["benefit_state"] == "token_regressive":
        findings.append(
            {
                "surface": "rtk",
                "severity": "warning",
                "code": "rtk_token_regressive",
                "summary": "RTK has recorded events, but compressed tokens exceed raw tokens.",
            }
        )
    elif classification["benefit_state"] == "no_benefit":
        findings.append(
            {
                "surface": "rtk",
                "severity": "info",
                "code": "rtk_no_benefit",
                "summary": "RTK has recorded events, but no positive token savings.",
            }
        )
    return {
        "state": TrustedSignal(
            value=classification["state"],
            provenance="missing" if events == 0 else "confirmed",
            confidence=0.45 if events == 0 else 0.9,
            source={"label": "RTK compression events", "table": "rtk_compression_events"},
            freshness="no events" if events == 0 else "all recorded events",
            explanation=str(classification["explanation"]),
            missing_reason=classification["missing_reason"],
        ).to_json(),
        "benefit_state": classification["benefit_state"],
        "metrics": {
            "events": metrics["event_count"],
            "raw_tokens": metrics["raw_tokens"],
            "compressed_tokens": metrics["compressed_tokens"],
            "tokens_saved": metrics["tokens_saved"],
        },
        "findings": findings,
    }


def _automation_signals(conn: sqlite3.Connection) -> dict[str, Any]:
    seeded = [
        ("automation-1", "Daily ingest status", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0", 0.97, "healthy"),
        ("automation-2", "PR health report", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=11;BYMINUTE=30", 0.83, "warning"),
        ("automation-3", "Nightly import verify", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR,SA,SU;BYHOUR=1;BYMINUTE=0", 0.62, "error"),
    ]
    items = []
    findings = []
    has_history = _table_exists(conn, "automation_run_history")
    if not has_history:
        findings.append(
            {
                "surface": "automations",
                "code": "automation_history_missing",
                "severity": "warning",
                "summary": "Automation reliability is inferred because durable automation run history is missing.",
                "source": {"label": "Automation run history", "table": "automation_run_history"},
                "freshness": "missing",
                "confidence": 0,
                "missing_reason": "automation_run_history table does not exist.",
            }
        )

    for automation_id, name, trigger, _seeded_success_rate, _seeded_status in seeded:
        label = automation_trigger_label(trigger)
        history = None
        if has_history:
            history = conn.execute(
                """
                SELECT
                  COUNT(*) AS run_count,
                  COALESCE(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), 0) AS success_count,
                  COALESCE(SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END), 0) AS failure_count,
                  MAX(started_at) AS last_run_at
                FROM automation_run_history
                WHERE automation_id = ?
                """,
                (automation_id,),
            ).fetchone()
        run_count = int(history["run_count"]) if history else 0
        success_count = int(history["success_count"]) if history else 0
        failure_count = int(history["failure_count"]) if history else 0
        confirmed_success_rate = round(success_count / run_count, 3) if run_count else None
        confirmed_status = "unknown" if run_count == 0 else "error" if failure_count else "healthy"
        urgency = "watch" if run_count == 0 else "action_required" if failure_count else "none"
        missing_history = None if run_count else "No durable automation run history exists for this automation."
        items.append(
            {
                "id": automation_id,
                "name": name,
                "raw_trigger": trigger,
                "last_run_at": str(history["last_run_at"]) if history and history["last_run_at"] else None,
                "success_count": success_count,
                "failure_count": failure_count,
                "urgency": urgency,
                "trigger": TrustedSignal(
                    value=label,
                    provenance="inferred",
                    confidence=0.8,
                    source={"label": "Seeded automation schedule", "field": "trigger"},
                    freshness="seeded",
                    explanation="Readable schedule inferred from the persisted RRULE trigger.",
                ).to_json(),
                "success_rate": TrustedSignal(
                    value=confirmed_success_rate,
                    provenance="confirmed" if run_count else "missing",
                    confidence=0.9 if run_count else 0,
                    source={"label": "Automation run history", "table": "automation_run_history", "field": "status"},
                    freshness=f"{run_count} durable run(s)" if run_count else "missing",
                    explanation="Success rate is derived from durable automation run history.",
                    missing_reason=missing_history,
                ).to_json(),
                "status": TrustedSignal(
                    value=confirmed_status,
                    provenance="confirmed" if run_count else "missing",
                    confidence=0.9 if run_count else 0,
                    source={"label": "Automation run history", "table": "automation_run_history", "field": "status"},
                    freshness=f"{run_count} durable run(s)" if run_count else "missing",
                    explanation="Automation status is derived from durable automation run history.",
                    missing_reason=missing_history,
                ).to_json(),
            }
        )
    return {"items": items, "findings": findings}


def _prompt_library_signals(conn: sqlite3.Connection) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not _table_exists(conn, "prompt_library_links"):
        findings.append(
            {
                "surface": "prompt_library",
                "code": "prompt_library_links_missing",
                "severity": "warning",
                "summary": "Prompt Library visibility cannot be trusted because prompt_library_links is missing.",
            }
        )
        return {
            "visibility": TrustedSignal(
                value="unavailable",
                provenance="missing",
                confidence=0,
                source={"label": "Prompt library links", "table": "prompt_library_links"},
                freshness="missing",
                explanation="Prompt Library requires body-hash evidence in prompt_library_links before templates are visible.",
                missing_reason="prompt_library_links table does not exist.",
            ).to_json(),
            "linked_templates": 0,
            "findings": findings,
        }

    linked_templates = _count(conn, "prompt_library_links")
    if linked_templates == 0:
        findings.append(
            {
                "surface": "prompt_library",
                "code": "prompt_library_empty",
                "severity": "warning",
                "summary": "Prompt Library has no body-hash-backed visible templates.",
            }
        )

    return {
        "visibility": TrustedSignal(
            value="visible" if linked_templates > 0 else "empty",
            provenance="confirmed" if linked_templates > 0 else "missing",
            confidence=0.9 if linked_templates > 0 else 0.45,
            source={"label": "Prompt library links", "table": "prompt_library_links"},
            freshness=f"{linked_templates} linked template(s)",
            explanation=(
                "Prompt Library visibility is backed by prompt_library_links body-hash evidence."
                if linked_templates > 0
                else "Prompt Library is wired, but no body-hash-backed templates are currently visible."
            ),
            missing_reason=None if linked_templates > 0 else "No rows exist in prompt_library_links.",
        ).to_json(),
        "linked_templates": linked_templates,
        "findings": findings,
    }


def _knowledge_signals(conn: sqlite3.Connection) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    topic_count = _count(conn, "knowledge_topics")
    reference_count = _count(conn, "knowledge_references")
    relationship_count = _count(conn, "knowledge_relationships")

    if topic_count == 0:
        findings.append(
            {
                "surface": "knowledge",
                "code": "knowledge_topics_missing",
                "severity": "warning",
                "summary": "Knowledge has no indexed topics.",
            }
        )
    if topic_count > 0 and reference_count == 0:
        findings.append(
            {
                "surface": "knowledge",
                "code": "knowledge_references_missing",
                "severity": "warning",
                "summary": "Knowledge topics exist without source references.",
            }
        )

    reference_ratio = 0 if topic_count == 0 else reference_count / topic_count
    return {
        "topic_count": TrustedSignal(
            value=topic_count,
            provenance="confirmed" if topic_count > 0 else "missing",
            confidence=0.9 if topic_count > 0 else 0,
            source={"label": "Knowledge topics", "table": "knowledge_topics"},
            freshness=f"{topic_count} topic(s)",
            explanation=(
                "Knowledge indexing has persisted topics."
                if topic_count > 0
                else "Knowledge indexing has not persisted any topics."
            ),
            missing_reason=None if topic_count > 0 else "No rows exist in knowledge_topics.",
        ).to_json(),
        "reference_coverage": TrustedSignal(
            value=round(reference_ratio, 3),
            provenance="confirmed" if reference_count > 0 else "missing",
            confidence=0.85 if reference_count > 0 else 0.2,
            source={"label": "Knowledge references", "table": "knowledge_references"},
            freshness=f"{reference_count} reference(s) for {topic_count} topic(s)",
            explanation=(
                "Knowledge topics have persisted source references."
                if reference_count > 0
                else "Knowledge topics currently lack persisted source references."
            ),
            missing_reason="No rows exist in knowledge_references." if reference_count == 0 else None,
        ).to_json(),
        "relationship_count": TrustedSignal(
            value=relationship_count,
            provenance="confirmed" if relationship_count > 0 else "missing",
            confidence=0.85 if relationship_count > 0 else 0.35,
            source={"label": "Knowledge relationships", "table": "knowledge_relationships"},
            freshness=f"{relationship_count} relationship(s)",
            explanation=(
                "Knowledge graph has persisted relationships."
                if relationship_count > 0
                else "Knowledge graph does not yet have persisted relationships."
            ),
            missing_reason="No rows exist in knowledge_relationships." if relationship_count == 0 else None,
        ).to_json(),
        "findings": findings,
    }


def capability_truth_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    projects = _project_signals(conn)
    rtk = _rtk_signals(conn)
    automations = _automation_signals(conn)
    prompt_library = _prompt_library_signals(conn)
    knowledge = _knowledge_signals(conn)
    findings = [
        *projects["findings"],
        *rtk["findings"],
        *automations["findings"],
        *prompt_library["findings"],
        *knowledge["findings"],
    ]
    return {
        "summary": {
            "surfaces": 5,
            "findings": len(findings),
            "contract": "TrustedSignal(value, provenance, confidence, source, freshness, explanation, missing_reason, contradiction)",
        },
        "projects": projects,
        "rtk": rtk,
        "automations": automations,
        "prompt_library": prompt_library,
        "knowledge": knowledge,
        "findings": findings,
    }
