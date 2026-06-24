from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

GateName = Literal["AIOS", "Pre-CR", "Anti-Slop", "other"]
EventType = Literal[
    "commit_blocked",
    "iteration_forced",
    "warning_escalated",
    "gate_passed_after_fix",
    "override_requested",
    "override_accepted",
    "override_rejected",
]
Severity = Literal["info", "warning", "error", "critical"]
Category = Literal[
    "architecture",
    "security",
    "test",
    "lint",
    "typecheck",
    "complexity",
    "performance",
    "maintainability",
    "UX",
    "documentation",
    "process",
    "unknown",
]
Decision = Literal["pass", "warn", "block", "force_iteration", "override"]
GateDecision = Literal["block", "warn"]
ActorType = Literal["agent", "human", "ci", "unknown"]

SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|private[_-]?key|client[_-]?secret)\b"
    r"\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
)
AUDIT_DIR = Path(".aios") / "audit"
EVENTS_FILE = "gate-events.jsonl"
SUMMARY_FILE = "gate-summary.md"
LESSONS_FILE = "learning-lessons.md"
PROTECTED_BRANCHES = frozenset({"main", "master", "dev", "develop", "development"})
BRANCH_ENV_KEYS = (
    "AIOS_BRANCH",
    "GITHUB_REF_NAME",
    "GITHUB_HEAD_REF",
    "BRANCH_NAME",
    "VERCEL_GIT_COMMIT_REF",
)
DEV_ENV_KEYS = (
    "AIOS_DEV_ENVIRONMENT",
    "AIOS_DEV_ENV",
    "QUALITY_GATE_DEV_ENV",
    "GATE_CONNECTED_DEV_ENV",
)


class Evidence(TypedDict, total=False):
    file: str
    line_start: int
    line_end: int
    snippet: str
    reason: str


class GateAuditEvent(TypedDict):
    schema_version: str
    event_id: str
    timestamp: str
    repo: str
    branch: str | None
    commit_sha: str | None
    run_id: str | None
    actor_type: ActorType
    gate: GateName
    gate_version: str | None
    event_type: EventType
    severity: Severity
    category: Category
    rule_id: str
    rule_name: str
    decision: Decision
    summary: str
    evidence: list[Evidence]
    failure_pattern: str
    root_cause_hypothesis: str | None
    required_fix: str
    actual_fix: str | None
    learning_lesson: str
    dedupe_fingerprint: str
    related_event_ids: list[str]
    blocked_duration_seconds: int | None
    tokens_wasted_estimate: int | None
    notes: str | None


def redact_secrets(text: str) -> str:
    return SECRET_RE.sub(lambda match: f'{match.group(1)} = "[REDACTED]"', text)


def dedupe_fingerprint(
    gate: str,
    rule_id: str,
    files: Sequence[str],
    failure_pattern: str,
) -> str:
    payload = "\n".join(
        [
            gate.strip().lower(),
            rule_id.strip().lower(),
            *sorted(path.strip().lower() for path in files if path.strip()),
            failure_pattern.strip().lower(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def quality_gate_decision(
    repo_root: Path,
    *,
    branch: str | None = None,
    env: Mapping[str, str] | None = None,
) -> GateDecision:
    values = os.environ if env is None else env
    mode = _first_env(values, ("AIOS_QUALITY_GATE_MODE", "QUALITY_GATE_MODE"))
    if mode in {"warn", "warning", "soft"}:
        return "warn"
    if mode in {"block", "blocking", "hard"}:
        return "block"

    resolved_branch = branch or _first_env(values, BRANCH_ENV_KEYS)
    if resolved_branch is None and env is None:
        resolved_branch = _git_value(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if resolved_branch and _normalize_branch(resolved_branch) in PROTECTED_BRANCHES:
        return "block"

    if any(_truthy(values.get(key)) for key in DEV_ENV_KEYS):
        return "block"
    if values.get("VERCEL_ENV", "").strip().lower() in {"production", "development"}:
        return "block"

    return "warn" if resolved_branch else "block"


def build_gate_audit_event(
    *,
    repo_root: Path,
    gate: GateName,
    event_type: EventType,
    severity: Severity,
    category: Category,
    rule_id: str,
    rule_name: str,
    decision: Decision,
    summary: str,
    evidence: Sequence[Mapping[str, Any]] = (),
    failure_pattern: str,
    required_fix: str,
    learning_lesson: str,
    root_cause_hypothesis: str | None = None,
    actual_fix: str | None = None,
    related_event_ids: Sequence[str] = (),
    blocked_duration_seconds: int | None = None,
    tokens_wasted_estimate: int | None = None,
    notes: str | None = None,
    timestamp: datetime | None = None,
) -> GateAuditEvent:
    clean_evidence = [_clean_evidence(item) for item in evidence]
    files = [file for item in clean_evidence if (file := item.get("file"))]
    fingerprint = dedupe_fingerprint(gate, rule_id, files, failure_pattern)
    occurred_at = timestamp or datetime.now(UTC)
    event_seed = "|".join([fingerprint, event_type, occurred_at.isoformat()])
    event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, event_seed))
    return {
        "schema_version": "1.0",
        "event_id": event_id,
        "timestamp": occurred_at.isoformat().replace("+00:00", "Z"),
        "repo": repo_root.name,
        "branch": _git_value(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "commit_sha": _git_value(repo_root, ["rev-parse", "HEAD"]),
        "run_id": _run_id(),
        "actor_type": _actor_type(),
        "gate": gate,
        "gate_version": _git_value(repo_root, ["rev-parse", "--short", "HEAD"]),
        "event_type": event_type,
        "severity": severity,
        "category": category,
        "rule_id": rule_id,
        "rule_name": rule_name,
        "decision": decision,
        "summary": redact_secrets(summary),
        "evidence": clean_evidence,
        "failure_pattern": redact_secrets(failure_pattern),
        "root_cause_hypothesis": _optional_redacted(root_cause_hypothesis),
        "required_fix": redact_secrets(required_fix),
        "actual_fix": _optional_redacted(actual_fix),
        "learning_lesson": redact_secrets(learning_lesson),
        "dedupe_fingerprint": fingerprint,
        "related_event_ids": list(related_event_ids),
        "blocked_duration_seconds": blocked_duration_seconds,
        "tokens_wasted_estimate": tokens_wasted_estimate,
        "notes": _optional_redacted(notes),
    }


def append_gate_audit_event(repo_root: Path, event: GateAuditEvent) -> None:
    audit_dir = repo_root / AUDIT_DIR
    audit_dir.mkdir(parents=True, exist_ok=True)
    events_path = audit_dir / EVENTS_FILE
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
        handle.write("\n")
    events = _read_events(events_path)
    (audit_dir / SUMMARY_FILE).write_text(_render_summary(events), encoding="utf-8")
    (audit_dir / LESSONS_FILE).write_text(_render_lessons(events), encoding="utf-8")


def safe_append_gate_audit_event(repo_root: Path, event: GateAuditEvent) -> None:
    try:
        append_gate_audit_event(repo_root, event)
    except OSError:
        return
    except TypeError:
        return
    except ValueError:
        return


def _clean_evidence(item: Mapping[str, Any]) -> Evidence:
    evidence: Evidence = {}
    file_value = item.get("file")
    if isinstance(file_value, str):
        evidence["file"] = file_value
    for key in ("line_start", "line_end"):
        value = item.get(key)
        if isinstance(value, int) and value > 0:
            evidence[key] = value
    snippet = item.get("snippet")
    if isinstance(snippet, str) and snippet.strip():
        evidence["snippet"] = redact_secrets(snippet.strip()[:500])
    reason = item.get("reason")
    if isinstance(reason, str) and reason.strip():
        evidence["reason"] = redact_secrets(reason.strip()[:500])
    return evidence


def _read_events(path: Path) -> list[GateAuditEvent]:
    events: list[GateAuditEvent] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict) and payload.get("schema_version") == "1.0":
            events.append(payload)  # type: ignore[arg-type]
    return events


def _render_summary(events: Sequence[GateAuditEvent]) -> str:
    latest = events[-1] if events else None
    outcome = _outcome(latest)
    lines = [
        "# Gate Audit Summary",
        "",
        "## Current run outcome",
        "",
        f"- Outcome: {outcome}",
        "",
        "## Gate decisions",
        "",
    ]
    for event in events[-10:]:
        evidence_files = ", ".join(_event_files(event)) or "no file evidence"
        lines.append(
            f"- {event['gate']} {event['decision']} [{event['severity']}]: "
            f"{event['summary']} ({evidence_files})"
        )
    lines.extend(["", "## Repeated failure patterns", ""])
    for fingerprint, grouped in _repeated_groups(events).items():
        first = grouped[0]
        lines.append(
            f"- {first['failure_pattern']} ({len(grouped)} event(s), "
            f"{first['gate']}, {first['category']}, fingerprint `{fingerprint}`)"
        )
    lines.extend(["", "## Agent learning lessons", ""])
    for lesson in _lesson_counts(events):
        lines.append(f"- {lesson}")
    lines.extend(["", "## Commit-readiness status", "", f"- {_readiness(outcome)}", ""])
    return "\n".join(lines)


def _render_lessons(events: Sequence[GateAuditEvent]) -> str:
    repeated = _repeated_groups(events)
    lines = [
        "# Gate Learning Lessons",
        "",
        "## Active repeated failure patterns",
        "",
    ]
    if not repeated:
        lines.append("No repeated failure patterns have been recorded yet.")
    for grouped in repeated.values():
        first = grouped[0]
        gates = ", ".join(sorted({event["gate"] for event in grouped}))
        lines.extend(
            [
                f"### Pattern: {first['failure_pattern']}",
                f"- Seen: {len(grouped)} times",
                f"- Gates: {gates}",
                f"- Category: {first['category']}",
                f"- Common cause: {first['root_cause_hypothesis'] or 'Unknown from current evidence.'}",
                f"- Avoid by: {first['learning_lesson']}",
                f"- Example fix: {first['required_fix']}",
                "",
            ]
        )
    lines.extend(["## Current repo-specific rules learned from gate history", ""])
    for lesson in _lesson_counts(events):
        lines.append(f"- {lesson}")
    if not events:
        lines.append("- No gate-backed lessons recorded yet.")
    lines.extend(["", "## High-priority agent reminders", ""])
    critical = [
        event["learning_lesson"]
        for event in events
        if event["severity"] in {"error", "critical"} and event["learning_lesson"]
    ]
    for lesson in dict.fromkeys(critical[-5:]):
        lines.append(f"- {lesson}")
    if not critical:
        lines.append("- No high-priority gate-backed reminders recorded yet.")
    lines.append("")
    return "\n".join(lines)


def _repeated_groups(events: Sequence[GateAuditEvent]) -> dict[str, list[GateAuditEvent]]:
    grouped: dict[str, list[GateAuditEvent]] = defaultdict(list)
    for event in events:
        grouped[event["dedupe_fingerprint"]].append(event)
    return {fingerprint: rows for fingerprint, rows in grouped.items() if len(rows) > 1}


def _lesson_counts(events: Sequence[GateAuditEvent]) -> list[str]:
    counts = Counter(event["learning_lesson"] for event in events if event["learning_lesson"])
    return [lesson for lesson, _count in counts.most_common(8)]


def _event_files(event: GateAuditEvent) -> list[str]:
    return [file for item in event["evidence"] if (file := item.get("file"))]


def _outcome(event: GateAuditEvent | None) -> str:
    if event is None:
        return "unknown"
    if event["decision"] == "block":
        return "blocked"
    if event["decision"] == "force_iteration":
        return "forced iteration"
    if event["decision"] == "warn":
        return "warnings only"
    return "passed"


def _readiness(outcome: str) -> str:
    if outcome == "blocked":
        return "not ready to commit"
    if outcome == "forced iteration":
        return "requires human review"
    if outcome == "warnings only":
        return "ready only with override"
    if outcome == "passed":
        return "ready to commit"
    return "unknown"


def _git_value(repo_root: Path, args: Sequence[str]) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _first_env(env: Mapping[str, str], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = env.get(key)
        if value and value.strip():
            return value.strip()
    return None


def _normalize_branch(branch: str) -> str:
    value = branch.strip()
    for prefix in ("refs/heads/", "origin/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def _truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on", "block"}


def _run_id() -> str | None:
    for key in ("AIOS_RUN_ID", "AIOS_SESSION_ID", "GITHUB_RUN_ID", "CI_PIPELINE_ID"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def _actor_type() -> ActorType:
    value = os.environ.get("AIOS_ACTOR_TYPE", "").strip().lower()
    if value in {"agent", "human", "ci"}:
        return value  # type: ignore[return-value]
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return "ci"
    return "unknown"


def _optional_redacted(value: str | None) -> str | None:
    if value is None:
        return None
    return redact_secrets(value)
