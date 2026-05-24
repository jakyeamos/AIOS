from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from services.capability_truth import Provenance

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "config" / "standards" / "registry.json"

AssessmentStatus = Literal["pass", "partial", "fail", "unknown", "waived", "not_applicable"]
KNOWN_PROVENANCE_STATES: tuple[Provenance, ...] = (
    "confirmed",
    "inferred",
    "missing",
    "contradictory",
)

PENALTY_MULTIPLIERS: dict[AssessmentStatus, float] = {
    "pass": 0.0,
    "partial": 0.5,
    "fail": 1.0,
    "unknown": 0.75,
    "waived": 0.0,
    "not_applicable": 0.0,
}
MAX_PENALTY_MULTIPLIER = 1.25


@dataclass(frozen=True)
class StandardDefinition:
    id: str
    profile_id: str
    title: str
    description: str
    domain: str
    weight: float
    severity_if_missing: int
    evaluation_method: str
    expected_state: dict[str, Any]
    remediation_playbook: dict[str, Any]
    blocking_dependencies: tuple[str, ...]
    version: str
    introduced_version: str
    applicability: dict[str, Any]
    waiver_policy: dict[str, Any]
    related_criteria: tuple[str, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EvaluatedStandard:
    standard: StandardDefinition
    status: AssessmentStatus
    reason: str
    measured_state: dict[str, Any]
    evidence: tuple[str, ...]
    evaluator_type: str
    confidence: float
    regression_flag: bool
    waiver_rationale: str | None
    waiver_owner: str | None
    waiver_review_at: str | None
    waiver_affects_portfolio: bool


@dataclass(frozen=True)
class DeltaExplanation:
    standard_id: str
    domain: str
    status: AssessmentStatus
    provenance: Provenance
    confidence: float
    freshness: str
    evidence: tuple[str, ...]
    contradiction: str | None
    remediation_summary: str
    remediation_effort: float
    remediation_leverage: float
    priority_score: float
    priority_bucket: str
    measured_state: dict[str, Any]
    expected_state: dict[str, Any]
    reason: str


class ManualAssessmentOverride(TypedDict, total=False):
    status: AssessmentStatus
    reason: str
    measured_state: dict[str, Any]
    evidence: list[str]
    confidence: float
    regression_flag: bool
    waiver_rationale: str
    waiver_owner: str
    waiver_review_at: str
    waiver_affects_portfolio: bool


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return loaded if isinstance(loaded, list) else []


def _json_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return loaded


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    if not _table_exists(conn, name):
        return set()
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({name})").fetchall()}


def _version_tuple(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in value.split("."):
        token = token.strip()
        if token.isdigit():
            parts.append(int(token))
        elif token:
            digits = "".join(char for char in token if char.isdigit())
            parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _version_gt(left: str, right: str) -> bool:
    return _version_tuple(left) > _version_tuple(right)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def load_registry(
    path: Path = DEFAULT_REGISTRY_PATH,
) -> tuple[dict[str, Any], list[StandardDefinition]]:
    loaded = _load_json(path)
    profile = loaded.get("profile")
    standards_raw = loaded.get("standards")
    if not isinstance(profile, dict):
        raise ValueError("Standards registry missing profile object")
    if not isinstance(standards_raw, list):
        raise ValueError("Standards registry missing standards list")

    profile_id = str(profile.get("id", "")).strip()
    if not profile_id:
        raise ValueError("Standards profile id is required")

    standards: list[StandardDefinition] = []
    for item in standards_raw:
        if not isinstance(item, dict):
            continue
        standard_id = str(item.get("id", "")).strip()
        if not standard_id:
            continue
        blocking_dependencies = item.get("blocking_dependencies") or []
        related_criteria = item.get("related_criteria") or []
        standards.append(
            StandardDefinition(
                id=standard_id,
                profile_id=profile_id,
                title=str(item.get("title", standard_id)),
                description=str(item.get("description", "")),
                domain=str(item.get("domain", "uncategorized")),
                weight=float(item.get("weight", 1.0)),
                severity_if_missing=int(item.get("severity_if_missing", 3)),
                evaluation_method=str(item.get("evaluation_method", "manual")),
                expected_state=cast(dict[str, Any], item.get("expected_state") or {}),
                remediation_playbook=cast(dict[str, Any], item.get("remediation_playbook") or {}),
                blocking_dependencies=tuple(
                    str(dep) for dep in blocking_dependencies if isinstance(dep, str) and dep
                ),
                version=str(item.get("version") or profile.get("version") or "0.0.0"),
                introduced_version=str(
                    item.get("introduced_version")
                    or item.get("version")
                    or profile.get("version")
                    or "0.0.0"
                ),
                applicability=cast(dict[str, Any], item.get("applicability") or {}),
                waiver_policy=cast(dict[str, Any], item.get("waiver_policy") or {}),
                related_criteria=tuple(
                    str(criterion) for criterion in related_criteria if isinstance(criterion, str)
                ),
                metadata=cast(dict[str, Any], item.get("metadata") or {}),
            )
        )

    return profile, standards


def ensure_standards_health_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS standards_profiles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            version TEXT NOT NULL,
            default_attached_version TEXT NOT NULL,
            domains_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS standards_definitions (
            id TEXT PRIMARY KEY,
            standard_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            domain TEXT NOT NULL,
            weight REAL NOT NULL,
            severity_if_missing INTEGER NOT NULL,
            evaluation_method TEXT NOT NULL,
            expected_state_json TEXT NOT NULL DEFAULT '{}',
            remediation_playbook_json TEXT NOT NULL DEFAULT '{}',
            blocking_dependencies_json TEXT NOT NULL DEFAULT '[]',
            version TEXT NOT NULL,
            introduced_version TEXT NOT NULL,
            applicability_json TEXT NOT NULL DEFAULT '{}',
            waiver_policy_json TEXT NOT NULL DEFAULT '{}',
            related_criteria_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            is_latest INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(standard_id, profile_id, version)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_standards_definitions_profile
          ON standards_definitions(profile_id, is_latest, domain)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_standards_profiles (
            project_id TEXT PRIMARY KEY REFERENCES projects(id),
            profile_id TEXT NOT NULL,
            attached_version TEXT NOT NULL,
            latest_version TEXT NOT NULL,
            migration_mode TEXT NOT NULL DEFAULT 'current',
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS standards_assessments (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            project_id TEXT NOT NULL REFERENCES projects(id),
            standard_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            standard_version TEXT NOT NULL,
            status TEXT NOT NULL,
            measured_state_json TEXT NOT NULL DEFAULT '{}',
            expected_state_snapshot_json TEXT NOT NULL DEFAULT '{}',
            reason TEXT,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            last_evaluated_at TEXT NOT NULL,
            evaluator_type TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            regression_flag INTEGER NOT NULL DEFAULT 0,
            waiver_rationale TEXT,
            waiver_owner TEXT,
            waiver_review_at TEXT,
            waiver_affects_portfolio INTEGER NOT NULL DEFAULT 1,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_standards_assessments_project
          ON standards_assessments(project_id, last_evaluated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS standards_manual_overrides (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            standard_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            UNIQUE(project_id, standard_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS standards_delta_items (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            project_id TEXT NOT NULL REFERENCES projects(id),
            standard_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            standard_version TEXT NOT NULL,
            domain TEXT NOT NULL,
            severity INTEGER NOT NULL,
            status TEXT NOT NULL,
            summary TEXT NOT NULL,
            remediation_playbook_json TEXT NOT NULL DEFAULT '{}',
            estimated_health_impact REAL NOT NULL DEFAULT 0,
            blockers_json TEXT NOT NULL DEFAULT '[]',
            foundational INTEGER NOT NULL DEFAULT 0,
            downstream INTEGER NOT NULL DEFAULT 0,
            linked_task_ids_json TEXT NOT NULL DEFAULT '[]',
            priority_score REAL NOT NULL DEFAULT 0,
            priority_bucket TEXT NOT NULL DEFAULT 'high_leverage',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_standards_delta_items_project
          ON standards_delta_items(project_id, updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS standards_backfill_tasks (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL,
            project_id TEXT NOT NULL REFERENCES projects(id),
            delta_item_id TEXT NOT NULL REFERENCES standards_delta_items(id),
            standard_id TEXT NOT NULL,
            title TEXT NOT NULL,
            problem_statement TEXT NOT NULL,
            expected_state TEXT NOT NULL,
            acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
            effort REAL NOT NULL DEFAULT 1,
            dependency_chain_json TEXT NOT NULL DEFAULT '[]',
            expected_health_impact REAL NOT NULL DEFAULT 0,
            owner TEXT,
            blocked_reason TEXT,
            due_at TEXT,
            review_at TEXT,
            priority_score REAL NOT NULL DEFAULT 0,
            priority_bucket TEXT NOT NULL DEFAULT 'high_leverage',
            blocked INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_standards_backfill_tasks_project
          ON standards_backfill_tasks(project_id, updated_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS standards_health_snapshots (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            profile_id TEXT NOT NULL,
            attached_version TEXT NOT NULL,
            latest_version TEXT NOT NULL,
            standards_version TEXT NOT NULL,
            overall_score REAL NOT NULL,
            weighted_delta REAL NOT NULL,
            max_penalty REAL NOT NULL,
            unmet_standards_count INTEGER NOT NULL,
            critical_delta_count INTEGER NOT NULL,
            regression_count INTEGER NOT NULL,
            unknown_count INTEGER NOT NULL,
            unknown_coverage REAL NOT NULL,
            evaluation_confidence REAL NOT NULL,
            domain_scores_json TEXT NOT NULL DEFAULT '{}',
            score_explain_json TEXT NOT NULL DEFAULT '{}',
            migration_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_standards_health_snapshots_project
          ON standards_health_snapshots(project_id, created_at DESC)
        """
    )


def _upsert_profile(conn: sqlite3.Connection, profile: dict[str, Any]) -> None:
    profile_id = str(profile.get("id"))
    title = str(profile.get("title") or profile_id)
    version = str(profile.get("version") or "0.0.0")
    default_attached_version = str(profile.get("default_attached_version") or version)
    domains = [str(item) for item in profile.get("domains", []) if isinstance(item, str)]
    metadata = cast(dict[str, Any], profile.get("metadata") or {})
    now = _now_iso()

    conn.execute(
        """
        INSERT INTO standards_profiles (
            id,
            title,
            version,
            default_attached_version,
            domains_json,
            metadata_json,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            version = excluded.version,
            default_attached_version = excluded.default_attached_version,
            domains_json = excluded.domains_json,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            profile_id,
            title,
            version,
            default_attached_version,
            _json(domains),
            _json(metadata),
            now,
            now,
        ),
    )


def _upsert_standards(
    conn: sqlite3.Connection,
    profile: dict[str, Any],
    standards: list[StandardDefinition],
) -> None:
    profile_id = str(profile.get("id"))
    latest_version = str(profile.get("version") or "0.0.0")
    now = _now_iso()

    for standard in standards:
        definition_id = f"{standard.id}@{standard.version}"
        is_latest = int(not _version_gt(latest_version, standard.version))
        if _version_gt(latest_version, standard.version):
            is_latest = 0

        conn.execute(
            """
            INSERT INTO standards_definitions (
                id,
                standard_id,
                profile_id,
                title,
                description,
                domain,
                weight,
                severity_if_missing,
                evaluation_method,
                expected_state_json,
                remediation_playbook_json,
                blocking_dependencies_json,
                version,
                introduced_version,
                applicability_json,
                waiver_policy_json,
                related_criteria_json,
                metadata_json,
                is_latest,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(standard_id, profile_id, version) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                domain = excluded.domain,
                weight = excluded.weight,
                severity_if_missing = excluded.severity_if_missing,
                evaluation_method = excluded.evaluation_method,
                expected_state_json = excluded.expected_state_json,
                remediation_playbook_json = excluded.remediation_playbook_json,
                blocking_dependencies_json = excluded.blocking_dependencies_json,
                introduced_version = excluded.introduced_version,
                applicability_json = excluded.applicability_json,
                waiver_policy_json = excluded.waiver_policy_json,
                related_criteria_json = excluded.related_criteria_json,
                metadata_json = excluded.metadata_json,
                is_latest = excluded.is_latest
            """,
            (
                definition_id,
                standard.id,
                profile_id,
                standard.title,
                standard.description,
                standard.domain,
                standard.weight,
                standard.severity_if_missing,
                standard.evaluation_method,
                _json(standard.expected_state),
                _json(standard.remediation_playbook),
                _json(list(standard.blocking_dependencies)),
                standard.version,
                standard.introduced_version,
                _json(standard.applicability),
                _json(standard.waiver_policy),
                _json(list(standard.related_criteria)),
                _json(standard.metadata),
                is_latest,
                now,
            ),
        )


def seed_registry(
    conn: sqlite3.Connection,
    *,
    path: Path = DEFAULT_REGISTRY_PATH,
) -> tuple[dict[str, Any], list[StandardDefinition]]:
    ensure_standards_health_schema(conn)
    profile, standards = load_registry(path)
    _upsert_profile(conn, profile)
    _upsert_standards(conn, profile, standards)
    return profile, standards


def _ensure_project_binding(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    profile: dict[str, Any],
) -> tuple[str, str]:
    profile_id = str(profile.get("id"))
    latest_version = str(profile.get("version") or "0.0.0")
    default_attached = str(profile.get("default_attached_version") or latest_version)
    now = _now_iso()

    row = conn.execute(
        """
        SELECT attached_version, latest_version
        FROM project_standards_profiles
        WHERE project_id = ?
        LIMIT 1
        """,
        (project_id,),
    ).fetchone()

    if row is None:
        conn.execute(
            """
            INSERT INTO project_standards_profiles (
                project_id,
                profile_id,
                attached_version,
                latest_version,
                migration_mode,
                updated_at
            )
            VALUES (?, ?, ?, ?, 'current', ?)
            """,
            (project_id, profile_id, default_attached, latest_version, now),
        )
        return default_attached, latest_version

    attached_version = str(row[0] or default_attached)
    conn.execute(
        """
        UPDATE project_standards_profiles
        SET profile_id = ?, latest_version = ?, updated_at = ?
        WHERE project_id = ?
        """,
        (profile_id, latest_version, now, project_id),
    )
    return attached_version, latest_version


def _project_repo_path(conn: sqlite3.Connection, project_id: str) -> Path | None:
    row = conn.execute(
        "SELECT repo_path FROM projects WHERE id = ? LIMIT 1", (project_id,)
    ).fetchone()
    if row is None or not row[0]:
        return None
    repo = Path(str(row[0])).expanduser()
    if not repo.is_absolute():
        repo = (REPO_ROOT / repo).resolve()
    return repo


def _latest_status_map(conn: sqlite3.Connection, project_id: str) -> dict[str, AssessmentStatus]:
    if not _table_exists(conn, "standards_assessments"):
        return {}

    rows = conn.execute(
        """
        SELECT standard_id, status
        FROM standards_assessments
        WHERE project_id = ?
        ORDER BY last_evaluated_at DESC
        """,
        (project_id,),
    ).fetchall()
    latest: dict[str, AssessmentStatus] = {}
    for standard_id, status in rows:
        key = str(standard_id)
        if key in latest:
            continue
        value = str(status)
        if value in PENALTY_MULTIPLIERS:
            latest[key] = cast(AssessmentStatus, value)
    return latest


def _load_manual_overrides(
    conn: sqlite3.Connection,
    project_id: str,
) -> dict[str, ManualAssessmentOverride]:
    if not _table_exists(conn, "standards_manual_overrides"):
        return {}
    rows = conn.execute(
        """
        SELECT standard_id, payload_json
        FROM standards_manual_overrides
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchall()
    overrides: dict[str, ManualAssessmentOverride] = {}
    for row in rows:
        payload = _json_dict(row[1])
        if payload:
            overrides[str(row[0])] = cast(ManualAssessmentOverride, payload)
    return overrides


def persist_manual_override(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    standard_id: str,
    override: ManualAssessmentOverride,
    actor: str,
) -> dict[str, Any]:
    ensure_standards_health_schema(conn)
    now = _now_iso()
    override_id = f"standards-override-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO standards_manual_overrides (
            id, project_id, standard_id, payload_json, actor, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, standard_id)
        DO UPDATE SET
            payload_json = excluded.payload_json,
            actor = excluded.actor,
            updated_at = excluded.updated_at
        """,
        (override_id, project_id, standard_id, _json(dict(override)), actor, now, now),
    )
    return {
        "project_id": project_id,
        "standard_id": standard_id,
        "status": override.get("status"),
        "actor": actor,
        "rationale": override.get("reason"),
        "persisted_at": now,
    }


def _find_security_signal(
    conn: sqlite3.Connection, project_id: str
) -> tuple[AssessmentStatus, str, float, list[str]]:
    if not _table_exists(conn, "success_criteria_findings"):
        return "unknown", "No success-criteria findings table was available.", 0.3, []

    rows = conn.execute(
        """
        SELECT level, summary
        FROM success_criteria_findings f
        INNER JOIN success_criteria_evaluations e ON e.id = f.evaluation_id
        WHERE e.project_id = ?
          AND f.criterion_id = 'security-review'
        ORDER BY f.created_at DESC
        LIMIT 5
        """,
        (project_id,),
    ).fetchall()

    if not rows:
        return "unknown", "No security-review findings were recorded yet.", 0.35, []

    evidence = [str(row[1]) for row in rows]
    levels = {str(row[0]) for row in rows}
    if "blocker" in levels:
        return "fail", "Security-review blocker findings are still open.", 0.9, evidence
    if "warning" in levels:
        return "partial", "Security-review warnings require follow-up.", 0.8, evidence
    return (
        "pass",
        "Recent security-review findings did not surface warnings/blockers.",
        0.75,
        evidence,
    )


def _unresolved_critical_findings(
    conn: sqlite3.Connection, project_id: str
) -> tuple[int, list[str]]:
    if not _table_exists(conn, "consistency_findings"):
        return 0, []
    rows = conn.execute(
        """
        SELECT rule_key, summary
        FROM consistency_findings
        WHERE project_id = ?
          AND severity = 'error'
          AND COALESCE(resolution_status, 'open') IN ('open', 'reopened')
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (project_id,),
    ).fetchall()
    return len(rows), [f"{row[0]}: {row[1]}" for row in rows]


def _evaluate_known_standard(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    standard: StandardDefinition,
    repo_path: Path | None,
) -> tuple[AssessmentStatus, str, float, dict[str, Any], list[str], str]:
    standard_id = standard.id

    if standard_id == "architecture.boundary_enforcement":
        config_path = REPO_ROOT / "config" / "architecture-enforcement" / "projects.json"
        if not config_path.exists():
            return "unknown", "Architecture enforcement registry is missing.", 0.2, {}, [], "auto"
        loaded = _load_json(config_path)
        projects = loaded.get("projects", [])
        project_found = any(
            isinstance(item, dict) and str(item.get("id")) == project_id
            for item in projects
            if isinstance(projects, list)
        )
        if project_found:
            return (
                "pass",
                "Project is bound in the architecture enforcement registry.",
                0.9,
                {"registry_path": str(config_path)},
                [str(config_path)],
                "auto",
            )
        return (
            "fail",
            "Project is missing from the architecture enforcement registry.",
            0.85,
            {"registry_path": str(config_path)},
            [str(config_path)],
            "auto",
        )

    if standard_id == "code_quality.lint_ratchet":
        if repo_path is None or not repo_path.exists():
            return "unknown", "Project repository path is unavailable.", 0.25, {}, [], "auto"
        package_json = repo_path / "package.json"
        pyproject = repo_path / "pyproject.toml"
        lint_signal = False
        evidence: list[str] = []
        if package_json.exists():
            try:
                payload = _load_json(package_json)
                scripts = payload.get("scripts")
                lint_signal = isinstance(scripts, dict) and "lint" in scripts
                if lint_signal:
                    evidence.append(str(package_json))
            except Exception:
                lint_signal = False
        if pyproject.exists():
            lint_signal = True
            evidence.append(str(pyproject))

        if lint_signal:
            return (
                "pass",
                "Lint/static-check signal exists for this repository.",
                0.75,
                {"repo_path": str(repo_path)},
                evidence,
                "auto",
            )
        return (
            "partial",
            "No obvious lint/static-check command was detected.",
            0.6,
            {"repo_path": str(repo_path)},
            [str(repo_path)],
            "auto",
        )

    if standard_id == "testing.trust_signal":
        if not _table_exists(conn, "success_criteria_evaluations"):
            return "unknown", "Success-criteria evaluations are unavailable.", 0.2, {}, [], "auto"
        row = conn.execute(
            """
            SELECT pass_count, warning_count, blocker_count, summary
            FROM success_criteria_evaluations
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        if row is None:
            return (
                "unknown",
                "No success-criteria evaluation has been recorded for this project.",
                0.3,
                {},
                [],
                "auto",
            )
        pass_count, warning_count, blocker_count, summary = (
            int(row[0]),
            int(row[1]),
            int(row[2]),
            str(row[3]),
        )
        measured = {
            "pass_count": pass_count,
            "warning_count": warning_count,
            "blocker_count": blocker_count,
            "summary": summary,
        }
        if blocker_count > 0:
            return (
                "fail",
                "Testing trust has blocker-level findings.",
                0.9,
                measured,
                [summary],
                "auto",
            )
        if warning_count > 0:
            return (
                "partial",
                "Testing trust has warning-level findings.",
                0.8,
                measured,
                [summary],
                "auto",
            )
        if pass_count > 0:
            return (
                "pass",
                "Testing trust passed in the latest criteria evaluation.",
                0.85,
                measured,
                [summary],
                "auto",
            )
        return (
            "unknown",
            "Testing trust has not produced meaningful evidence yet.",
            0.4,
            measured,
            [summary],
            "auto",
        )

    if standard_id == "security.review_traceability":
        status, reason, confidence, evidence = _find_security_signal(conn, project_id)
        return status, reason, confidence, {}, evidence, "semi_auto"

    if standard_id == "observability.run_signal_integrity":
        run_count = 0
        event_count = 0
        report_count = 0
        if _table_exists(conn, "orchestration_runs"):
            run_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM orchestration_runs WHERE project_id = ?", (project_id,)
                ).fetchone()[0]
            )
        if _table_exists(conn, "orchestration_run_events") and "project_id" in _table_columns(
            conn, "orchestration_run_events"
        ):
            event_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM orchestration_run_events WHERE project_id = ?",
                    (project_id,),
                ).fetchone()[0]
            )
        if _table_exists(conn, "workflow_execution_reports"):
            report_count = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM workflow_execution_reports wr
                    INNER JOIN orchestration_runs r ON r.id = wr.run_id
                    WHERE r.project_id = ?
                    """,
                    (project_id,),
                ).fetchone()[0]
            )

        measured = {
            "run_count": run_count,
            "event_count": event_count,
            "report_count": report_count,
        }
        if run_count > 0 and event_count > 0 and report_count > 0:
            return (
                "pass",
                "Run/event/report observability signals are all present.",
                0.9,
                measured,
                ["orchestration tables"],
                "auto",
            )
        if run_count > 0 and (event_count > 0 or report_count > 0):
            return (
                "partial",
                "Observability signals exist but are incomplete.",
                0.75,
                measured,
                ["orchestration tables"],
                "auto",
            )
        return (
            "unknown",
            "No workflow observability signal has been captured yet.",
            0.35,
            measured,
            [],
            "auto",
        )

    if standard_id == "documentation.truth_file_currency":
        if repo_path is None or not repo_path.exists():
            return "unknown", "Project repository path is unavailable.", 0.25, {}, [], "auto"
        project_file = repo_path / "PROJECT.md"
        if project_file.exists():
            return (
                "pass",
                "Project truth file exists.",
                0.8,
                {"truth_file": str(project_file)},
                [str(project_file)],
                "auto",
            )
        return (
            "fail",
            "Project truth file is missing.",
            0.85,
            {"truth_file": str(project_file)},
            [str(project_file)],
            "auto",
        )

    if standard_id == "workflow_agent_control.explicit_handshake":
        if not _table_exists(conn, "sessions"):
            return "unknown", "Sessions table is unavailable.", 0.2, {}, [], "auto"
        rows = conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN run_id IS NOT NULL THEN 1 ELSE 0 END) AS with_run,
                   SUM(CASE WHEN invocation_id IS NOT NULL THEN 1 ELSE 0 END) AS with_invocation
            FROM sessions
            WHERE project_id = ?
            """,
            (project_id,),
        ).fetchone()
        total = int(rows[0] or 0)
        with_run = int(rows[1] or 0)
        with_invocation = int(rows[2] or 0)
        linkage_ratio = (
            min(_safe_ratio(with_run, total), _safe_ratio(with_invocation, total))
            if total > 0
            else 0.0
        )
        measured = {
            "total_sessions": total,
            "sessions_with_run_id": with_run,
            "sessions_with_invocation_id": with_invocation,
            "linkage_ratio": linkage_ratio,
        }
        if total == 0:
            return "unknown", "No sessions exist for this project yet.", 0.3, measured, [], "auto"
        if linkage_ratio >= 0.9:
            return (
                "pass",
                "Explicit run/session handshake coverage is healthy.",
                0.9,
                measured,
                [],
                "auto",
            )
        if linkage_ratio >= 0.6:
            return (
                "partial",
                "Run/session handshake coverage is incomplete.",
                0.75,
                measured,
                [],
                "auto",
            )
        return "fail", "Run/session handshake coverage is poor.", 0.8, measured, [], "auto"

    if standard_id == "release_ci_discipline.automated_checks":
        if repo_path is None or not repo_path.exists():
            return "unknown", "Project repository path is unavailable.", 0.25, {}, [], "auto"
        workflows_dir = repo_path / ".github" / "workflows"
        if not workflows_dir.exists():
            return (
                "partial",
                "No CI workflows directory was found.",
                0.6,
                {"workflows_dir": str(workflows_dir)},
                [str(workflows_dir)],
                "auto",
            )
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        if workflow_files:
            return (
                "pass",
                "CI workflow files are present.",
                0.75,
                {"workflow_count": len(workflow_files)},
                [str(path) for path in workflow_files[:3]],
                "auto",
            )
        return (
            "partial",
            "Workflows directory exists but no YAML workflows were found.",
            0.55,
            {"workflows_dir": str(workflows_dir)},
            [str(workflows_dir)],
            "auto",
        )

    if standard_id == "product_readiness.command_center_operability":
        unresolved_count, unresolved_evidence = _unresolved_critical_findings(conn, project_id)
        required_paths = [
            REPO_ROOT / "aios-ui" / "app" / "page.tsx",
            REPO_ROOT / "aios-ui" / "components" / "projects" / "TaskiProjectSurface.tsx",
            REPO_ROOT / "docs" / "aios-ui-command-center-handoff.md",
        ]
        existing = [str(path) for path in required_paths if path.exists()]
        if unresolved_count > 0:
            return (
                "fail",
                f"{unresolved_count} unresolved critical evaluator findings are still open.",
                0.9,
                {"unresolved_critical_findings": unresolved_count, "required_paths": existing},
                unresolved_evidence,
                "semi_auto",
            )
        if len(existing) == len(required_paths):
            return (
                "pass",
                "Control-surface primitives are present for project health operations.",
                0.7,
                {"required_paths": existing},
                existing,
                "semi_auto",
            )
        if existing:
            return (
                "partial",
                "Some control-surface primitives exist but readiness is incomplete.",
                0.55,
                {"required_paths": existing},
                existing,
                "semi_auto",
            )
        return (
            "unknown",
            "No product-readiness control-surface evidence was found.",
            0.3,
            {"required_paths": []},
            [],
            "semi_auto",
        )

    if standard_id == "maintainability.dead_code_signal":
        return (
            "unknown",
            "Dead-code evaluator not yet wired; use 'aios standards-override' to record vulture/knip results manually.",
            0.2,
            {"required_tool": "vulture_or_knip"},
            [],
            "auto",
        )

    if standard_id == "ux.operator_clarity":
        return (
            "unknown",
            "Operator-clarity is a manual evaluator; use 'aios standards-override --status pass --rationale ...' once the operator surface is reviewed.",
            0.2,
            {},
            [],
            "manual",
        )

    if standard_id == "launch_readiness.deployable":
        return (
            "unknown",
            "Launch-readiness is a semi-auto evaluator awaiting CI evidence wiring; use 'aios standards-override' for now.",
            0.25,
            {},
            [],
            "semi_auto",
        )

    if standard_id == "agent_readiness.handoff_packet":
        if not _table_exists(conn, "briefing_packets"):
            return (
                "unknown",
                "No briefing_packets row exists for this project yet; agent-readiness will flip once a handoff packet is recorded.",
                0.3,
                {"row_count": 0},
                [],
                "auto",
            )
        try:
            row = conn.execute(
                """
                SELECT selected_standards_json, selected_criteria_json
                FROM briefing_packets
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return (
                "unknown",
                "briefing_packets exists but selected criteria/standards columns are unavailable; rerun schema migration.",
                0.3,
                {"schema_columns": "missing"},
                [],
                "auto",
            )
        if row is None:
            return (
                "unknown",
                "No briefing_packets row exists for this project yet; agent-readiness will flip once a handoff packet is recorded.",
                0.3,
                {"row_count": 0},
                [],
                "auto",
            )
        selected_standards = _json_list(row[0])
        selected_criteria = _json_list(row[1])
        measured = {
            "selected_standards_count": len(selected_standards),
            "selected_criteria_count": len(selected_criteria),
        }
        if selected_standards and selected_criteria:
            return (
                "pass",
                "Latest briefing packet includes resolved standards and criteria.",
                0.75,
                measured,
                ["briefing_packets"],
                "auto",
            )
        if selected_standards or selected_criteria:
            return (
                "partial",
                "Latest briefing packet contains only one of resolved standards or criteria.",
                0.6,
                measured,
                ["briefing_packets"],
                "auto",
            )
        return (
            "unknown",
            "Latest briefing packet has no resolved standards or criteria.",
            0.4,
            measured,
            ["briefing_packets"],
            "auto",
        )

    if standard_id == "standards_compliance.profile_attached":
        if not _table_exists(conn, "project_standards_profiles"):
            return (
                "unknown",
                "Project standards profile table is unavailable; attach a profile to enable standards-compliance scoring.",
                0.3,
                {"profile_attached": False},
                [],
                "auto",
            )
        profile_row = conn.execute(
            "SELECT profile_id FROM project_standards_profiles WHERE project_id = ? LIMIT 1",
            (project_id,),
        ).fetchone()
        if profile_row is None:
            return (
                "unknown",
                "Project has no row in project_standards_profiles; attach a profile to enable standards-compliance scoring.",
                0.3,
                {"profile_attached": False},
                [],
                "auto",
            )
        snapshot_row = None
        if _table_exists(conn, "standards_health_snapshots"):
            snapshot_row = conn.execute(
                """
                SELECT unknown_coverage
                FROM standards_health_snapshots
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if snapshot_row is None:
            return (
                "unknown",
                "Project has a profile attached but no health snapshot exists yet; rescore after the next session-close.",
                0.4,
                {"profile_attached": True},
                ["project_standards_profiles"],
                "auto",
            )
        unknown_coverage = float(snapshot_row[0] or 0.0)
        measured = {"profile_attached": True, "unknown_coverage": unknown_coverage}
        if unknown_coverage < 0.4:
            return (
                "pass",
                "Project has a standards profile and unknown coverage is below threshold.",
                0.85,
                measured,
                ["project_standards_profiles", "standards_health_snapshots"],
                "auto",
            )
        if unknown_coverage < 0.7:
            return (
                "partial",
                "Project has a standards profile but unknown coverage needs reduction.",
                0.7,
                measured,
                ["project_standards_profiles", "standards_health_snapshots"],
                "auto",
            )
        return (
            "fail",
            "Project has a standards profile but unknown coverage is too high.",
            0.75,
            measured,
            ["project_standards_profiles", "standards_health_snapshots"],
            "auto",
        )

    return (
        "unknown",
        "No evaluator implementation exists for this standard yet.",
        0.2,
        {},
        [],
        "manual",
    )


def _compute_score(evaluations: list[EvaluatedStandard]) -> dict[str, Any]:
    domain_penalties: dict[str, float] = defaultdict(float)
    domain_max: dict[str, float] = defaultdict(float)
    domain_weights: dict[str, float] = defaultdict(float)
    domain_confidence_weighted: dict[str, float] = defaultdict(float)

    total_penalty = 0.0
    max_penalty = 0.0
    unmet = 0
    critical = 0
    regressions = 0
    unknown_count = 0
    unknown_weight = 0.0

    for evaluation in evaluations:
        if evaluation.status == "not_applicable":
            continue

        weight = evaluation.standard.weight
        domain = evaluation.standard.domain
        domain_max[domain] += weight * MAX_PENALTY_MULTIPLIER
        domain_weights[domain] += weight
        domain_confidence_weighted[domain] += weight * max(0.0, min(1.0, evaluation.confidence))

        multiplier = PENALTY_MULTIPLIERS[evaluation.status]
        if evaluation.status == "fail" and evaluation.regression_flag:
            multiplier = MAX_PENALTY_MULTIPLIER
            regressions += 1
        penalty = weight * multiplier

        domain_penalties[domain] += penalty
        total_penalty += penalty
        max_penalty += weight * MAX_PENALTY_MULTIPLIER

        if evaluation.status in {"partial", "fail", "unknown"}:
            unmet += 1
            if evaluation.standard.severity_if_missing >= 4:
                critical += 1

        if evaluation.status == "unknown":
            unknown_count += 1
            unknown_weight += weight

    overall_score = 100.0
    if max_penalty > 0:
        overall_score = max(
            0.0, min(100.0, round((1.0 - (total_penalty / max_penalty)) * 100.0, 2))
        )

    domain_scores: dict[str, float] = {}
    domain_confidence: dict[str, float] = {}
    for domain, penalty in domain_penalties.items():
        denominator = domain_max[domain]
        if denominator <= 0:
            domain_scores[domain] = 100.0
        else:
            domain_scores[domain] = max(
                0.0, min(100.0, round((1.0 - (penalty / denominator)) * 100.0, 2))
            )
        domain_confidence[domain] = round(
            _safe_ratio(domain_confidence_weighted[domain], domain_weights[domain]),
            3,
        )

    total_weight = sum(domain_weights.values())
    evaluation_confidence = round(
        _safe_ratio(sum(domain_confidence_weighted.values()), total_weight),
        3,
    )
    unknown_coverage = round(_safe_ratio(unknown_weight, total_weight), 3)

    return {
        "overall_score": overall_score,
        "weighted_delta": round(total_penalty, 3),
        "max_penalty": round(max_penalty, 3),
        "unmet_standards_count": unmet,
        "critical_delta_count": critical,
        "regression_count": regressions,
        "unknown_count": unknown_count,
        "unknown_coverage": unknown_coverage,
        "evaluation_confidence": evaluation_confidence,
        "domain_scores": {
            domain: {
                "score": score,
                "confidence": domain_confidence.get(domain, 0.0),
                "weight": round(domain_weights.get(domain, 0.0), 3),
            }
            for domain, score in domain_scores.items()
        },
    }


def _priority_bucket(
    *,
    status: AssessmentStatus,
    foundational: bool,
    blocked: bool,
    effort: float,
) -> str:
    if status == "waived":
        return "waived_deferred"
    if blocked:
        return "blocked"
    if foundational:
        return "foundational"
    if effort <= 1.5:
        return "quick_wins"
    return "high_leverage"


def _build_delta_items(
    evaluations: list[EvaluatedStandard],
    score: dict[str, Any],
) -> list[dict[str, Any]]:
    max_penalty = float(score["max_penalty"])
    if max_penalty <= 0:
        max_penalty = 1.0

    status_by_standard = {item.standard.id: item.status for item in evaluations}
    unlock_map: dict[str, int] = defaultdict(int)
    for evaluation in evaluations:
        for dependency in evaluation.standard.blocking_dependencies:
            unlock_map[dependency] += 1

    delta_items: list[dict[str, Any]] = []
    for evaluation in evaluations:
        if evaluation.status in {"pass", "not_applicable"}:
            continue

        standard = evaluation.standard
        multiplier = PENALTY_MULTIPLIERS[evaluation.status]
        if evaluation.status == "fail" and evaluation.regression_flag:
            multiplier = MAX_PENALTY_MULTIPLIER
        penalty = standard.weight * multiplier
        estimated_impact = round((penalty / max_penalty) * 100.0, 2)

        unresolved_blockers = [
            dependency
            for dependency in standard.blocking_dependencies
            if status_by_standard.get(dependency) not in {"pass", "waived", "not_applicable"}
        ]

        remediation = standard.remediation_playbook
        effort = max(float(remediation.get("effort", 1.0)), 0.25)
        leverage = max(float(remediation.get("leverage", 1.0)), 0.1)
        dependency_unlock = max(1.0, float(unlock_map.get(standard.id, 0) + 1))
        regression_penalty = MAX_PENALTY_MULTIPLIER if evaluation.regression_flag else 1.0
        priority_score = round(
            (
                float(standard.severity_if_missing)
                * leverage
                * dependency_unlock
                * regression_penalty
            )
            / effort,
            3,
        )

        foundational = bool(standard.metadata.get("foundational", False))
        blocked = len(unresolved_blockers) > 0

        delta_items.append(
            {
                "standard_id": standard.id,
                "profile_id": standard.profile_id,
                "standard_version": standard.version,
                "domain": standard.domain,
                "severity": standard.severity_if_missing,
                "status": evaluation.status,
                "summary": evaluation.reason,
                "remediation_playbook": remediation,
                "estimated_health_impact": estimated_impact,
                "blockers": unresolved_blockers,
                "foundational": foundational,
                "downstream": not foundational,
                "priority_score": priority_score,
                "priority_bucket": _priority_bucket(
                    status=evaluation.status,
                    foundational=foundational,
                    blocked=blocked,
                    effort=effort,
                ),
                "effort": effort,
                "expected_state": standard.expected_state,
            }
        )

    delta_items.sort(key=lambda item: item["priority_score"], reverse=True)
    return delta_items


def _has_contradiction(status: AssessmentStatus, cross_signals: dict[str, Any]) -> bool:
    findings_by_criterion = cross_signals.get("findings_by_criterion")
    if status != "pass" or not isinstance(findings_by_criterion, dict):
        return False
    return any(int(count or 0) > 0 for count in findings_by_criterion.values())


def _classify_provenance(
    *,
    status: AssessmentStatus,
    confidence: float,
    evidence: tuple[str, ...] | list[str],
    evaluator_type: str,
    cross_signals: dict[str, Any] | None,
) -> Provenance:
    if status == "unknown" or len(evidence) == 0:
        return "missing"
    if cross_signals and _has_contradiction(status, cross_signals):
        return "contradictory"
    if evaluator_type == "auto" and confidence >= 0.75:
        return "confirmed"
    return "inferred"


def _findings_by_criterion(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    within_days: int = 14,
) -> dict[str, int]:
    """Return recent open criteria findings for contradiction checks."""
    cutoff = (datetime.now(UTC) - timedelta(days=within_days)).isoformat()
    counts: dict[str, int] = defaultdict(int)
    if _table_exists(conn, "success_criteria_findings") and _table_exists(
        conn, "success_criteria_evaluations"
    ):
        rows = conn.execute(
            """
            SELECT f.criterion_id, COUNT(*)
            FROM success_criteria_findings f
            INNER JOIN success_criteria_evaluations e ON e.id = f.evaluation_id
            WHERE e.project_id = ?
              AND COALESCE(f.resolution_status, 'open') = 'open'
              AND f.level IN ('warning', 'blocker')
              AND f.created_at >= ?
            GROUP BY f.criterion_id
            """,
            (project_id, cutoff),
        ).fetchall()
        for row in rows:
            counts[str(row[0])] += int(row[1] or 0)
    if _table_exists(conn, "success_criteria_stage_findings") and _table_exists(
        conn, "orchestration_runs"
    ):
        rows = conn.execute(
            """
            SELECT f.criterion_id, COUNT(*)
            FROM success_criteria_stage_findings f
            INNER JOIN orchestration_runs r ON r.id = f.run_id
            WHERE r.project_id = ?
              AND COALESCE(f.resolution_status, 'open') = 'open'
              AND f.level IN ('warning', 'blocker')
              AND f.created_at >= ?
            GROUP BY f.criterion_id
            """,
            (project_id, cutoff),
        ).fetchall()
        for row in rows:
            counts[str(row[0])] += int(row[1] or 0)
    return dict(counts)


def _detect_contradiction(
    evaluation: EvaluatedStandard,
    capability_signals: dict[str, Any] | None,
) -> str | None:
    if not evaluation.standard.related_criteria or not capability_signals:
        return None
    findings_by_criterion = capability_signals.get("findings_by_criterion")
    if not isinstance(findings_by_criterion, dict):
        return None
    for criterion_id in evaluation.standard.related_criteria:
        blockers = int(findings_by_criterion.get(criterion_id, 0) or 0)
        if evaluation.status == "pass" and blockers > 0:
            return (
                f"Standard reports pass but {blockers} open finding(s) exist on related "
                f"criterion '{criterion_id}'."
            )
        if evaluation.status == "fail" and blockers == 0 and evaluation.confidence < 0.5:
            return (
                f"Standard reports fail with low confidence ({evaluation.confidence}) but no "
                f"findings recorded on related criterion '{criterion_id}'."
            )
    return None


def build_explanation(
    *,
    evaluation: EvaluatedStandard,
    delta_item: dict[str, Any] | None,
    capability_signals: dict[str, Any] | None = None,
    freshness: str | None = None,
) -> DeltaExplanation:
    remediation = (
        cast(dict[str, Any], delta_item.get("remediation_playbook"))
        if delta_item and isinstance(delta_item.get("remediation_playbook"), dict)
        else evaluation.standard.remediation_playbook
    )
    contradiction = _detect_contradiction(evaluation, capability_signals)
    cross_signals = (
        {
            "findings_by_criterion": {
                criterion: 1 for criterion in evaluation.standard.related_criteria
            }
        }
        if contradiction
        else capability_signals
    )
    return DeltaExplanation(
        standard_id=evaluation.standard.id,
        domain=evaluation.standard.domain,
        status=evaluation.status,
        provenance=_classify_provenance(
            status=evaluation.status,
            confidence=evaluation.confidence,
            evidence=evaluation.evidence,
            evaluator_type=evaluation.evaluator_type,
            cross_signals=cross_signals,
        ),
        confidence=evaluation.confidence,
        freshness=freshness or _now_iso(),
        evidence=evaluation.evidence,
        contradiction=contradiction,
        remediation_summary=str(remediation.get("summary", "")),
        remediation_effort=float(remediation.get("effort", 1.0) or 1.0),
        remediation_leverage=float(remediation.get("leverage", 1.0) or 1.0),
        priority_score=float(delta_item.get("priority_score", 0.0) if delta_item else 0.0),
        priority_bucket=str(
            delta_item.get("priority_bucket", "high_leverage") if delta_item else "high_leverage"
        ),
        measured_state=evaluation.measured_state,
        expected_state=evaluation.standard.expected_state,
        reason=evaluation.reason,
    )


def project_delta_explanations(
    conn: sqlite3.Connection,
    project_id: str,
) -> list[DeltaExplanation]:
    snapshot = latest_snapshot(conn, project_id)
    if snapshot is None:
        return []
    _, standards = load_registry()
    standards_by_id = {standard.id: standard for standard in standards}
    capability_signals = {"findings_by_criterion": _findings_by_criterion(conn, project_id)}
    rows = conn.execute(
        """
        SELECT
            a.standard_id,
            a.status,
            a.measured_state_json,
            a.reason,
            a.evidence_json,
            a.last_evaluated_at,
            a.evaluator_type,
            a.confidence,
            a.regression_flag,
            a.waiver_rationale,
            a.waiver_owner,
            a.waiver_review_at,
            a.waiver_affects_portfolio,
            d.remediation_playbook_json,
            d.priority_score,
            d.priority_bucket
        FROM standards_assessments a
        LEFT JOIN standards_delta_items d
          ON d.snapshot_id = a.snapshot_id AND d.standard_id = a.standard_id
        WHERE a.snapshot_id = ?
        ORDER BY COALESCE(d.priority_score, 0) DESC, a.standard_id ASC
        """,
        (snapshot["id"],),
    ).fetchall()
    explanations: list[DeltaExplanation] = []
    for row in rows:
        standard = standards_by_id.get(str(row[0]))
        if standard is None:
            continue
        delta_item = None
        if row[13] is not None or row[14] is not None or row[15] is not None:
            delta_item = {
                "remediation_playbook": _json_dict(row[13]),
                "priority_score": float(row[14] or 0.0),
                "priority_bucket": str(row[15] or "high_leverage"),
            }
        evaluation = EvaluatedStandard(
            standard=standard,
            status=cast(AssessmentStatus, row[1]),
            reason=str(row[3] or ""),
            measured_state=_json_dict(row[2]),
            evidence=tuple(str(item) for item in _json_list(row[4])),
            evaluator_type=str(row[6] or "manual"),
            confidence=float(row[7] or 0.0),
            regression_flag=bool(row[8]),
            waiver_rationale=str(row[9]) if row[9] is not None else None,
            waiver_owner=str(row[10]) if row[10] is not None else None,
            waiver_review_at=str(row[11]) if row[11] is not None else None,
            waiver_affects_portfolio=bool(row[12]),
        )
        explanations.append(
            build_explanation(
                evaluation=evaluation,
                delta_item=delta_item,
                capability_signals=capability_signals,
                freshness=str(row[5] or snapshot["created_at"]),
            )
        )
    explanations.sort(key=lambda item: (-item.priority_score, item.standard_id))
    return explanations


def _build_task_rows(
    *,
    project_id: str,
    snapshot_id: str,
    delta_items: list[dict[str, Any]],
    created_at: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for item in delta_items:
        if item["status"] in {"waived", "unknown"} and item["priority_bucket"] == "waived_deferred":
            continue

        task_id = f"taski-standard-{uuid.uuid4()}"
        acceptance = [
            f"Standard `{item['standard_id']}` reaches pass or waived-with-review state.",
            "Expected state and evidence links are recorded in standards assessment artifacts.",
        ]
        blocked = item["priority_bucket"] == "blocked"
        tasks.append(
            {
                "id": task_id,
                "snapshot_id": snapshot_id,
                "project_id": project_id,
                "delta_item_id": None,
                "standard_id": item["standard_id"],
                "title": f"Backfill {item['standard_id']}",
                "problem_statement": item["summary"],
                "expected_state": json.dumps(item["expected_state"], ensure_ascii=False),
                "acceptance_criteria": acceptance,
                "effort": item["effort"],
                "dependency_chain": item["blockers"],
                "expected_health_impact": item["estimated_health_impact"],
                "owner": None,
                "priority_score": item["priority_score"],
                "priority_bucket": item["priority_bucket"],
                "blocked": blocked,
                "status": "blocked" if blocked else "open",
                "created_at": created_at,
            }
        )
    return tasks


def _persist_assessments(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    project_id: str,
    evaluations: list[EvaluatedStandard],
    created_at: str,
) -> None:
    for evaluation in evaluations:
        conn.execute(
            """
            INSERT INTO standards_assessments (
                id,
                snapshot_id,
                project_id,
                standard_id,
                profile_id,
                standard_version,
                status,
                measured_state_json,
                expected_state_snapshot_json,
                reason,
                evidence_json,
                last_evaluated_at,
                evaluator_type,
                confidence,
                regression_flag,
                waiver_rationale,
                waiver_owner,
                waiver_review_at,
                waiver_affects_portfolio,
                metadata_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"assessment-{uuid.uuid4()}",
                snapshot_id,
                project_id,
                evaluation.standard.id,
                evaluation.standard.profile_id,
                evaluation.standard.version,
                evaluation.status,
                _json(evaluation.measured_state),
                _json(evaluation.standard.expected_state),
                evaluation.reason,
                _json(list(evaluation.evidence)),
                created_at,
                evaluation.evaluator_type,
                evaluation.confidence,
                int(evaluation.regression_flag),
                evaluation.waiver_rationale,
                evaluation.waiver_owner,
                evaluation.waiver_review_at,
                int(evaluation.waiver_affects_portfolio),
                _json({"related_criteria": list(evaluation.standard.related_criteria)}),
                created_at,
            ),
        )


def _persist_delta_and_tasks(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    project_id: str,
    delta_items: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    created_at: str,
) -> tuple[int, int]:
    task_ids_by_standard: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        task_ids_by_standard[task["standard_id"]].append(task["id"])

    delta_ids_by_standard: dict[str, str] = {}
    for item in delta_items:
        delta_id = f"delta-{uuid.uuid4()}"
        delta_ids_by_standard[item["standard_id"]] = delta_id
        conn.execute(
            """
            INSERT INTO standards_delta_items (
                id,
                snapshot_id,
                project_id,
                standard_id,
                profile_id,
                standard_version,
                domain,
                severity,
                status,
                summary,
                remediation_playbook_json,
                estimated_health_impact,
                blockers_json,
                foundational,
                downstream,
                linked_task_ids_json,
                priority_score,
                priority_bucket,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delta_id,
                snapshot_id,
                project_id,
                item["standard_id"],
                item["profile_id"],
                item["standard_version"],
                item["domain"],
                item["severity"],
                item["status"],
                item["summary"],
                _json(item["remediation_playbook"]),
                item["estimated_health_impact"],
                _json(item["blockers"]),
                int(item["foundational"]),
                int(item["downstream"]),
                _json(task_ids_by_standard.get(item["standard_id"], [])),
                item["priority_score"],
                item["priority_bucket"],
                created_at,
                created_at,
            ),
        )

    for task in tasks:
        delta_item_id = delta_ids_by_standard.get(task["standard_id"])
        if delta_item_id is None:
            continue
        conn.execute(
            """
            INSERT INTO standards_backfill_tasks (
                id,
                snapshot_id,
                project_id,
                delta_item_id,
                standard_id,
                title,
                problem_statement,
                expected_state,
                acceptance_criteria_json,
                effort,
                dependency_chain_json,
                expected_health_impact,
                owner,
                blocked_reason,
                due_at,
                review_at,
                priority_score,
                priority_bucket,
                blocked,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["id"],
                snapshot_id,
                project_id,
                delta_item_id,
                task["standard_id"],
                task["title"],
                task["problem_statement"],
                task["expected_state"],
                _json(task["acceptance_criteria"]),
                task["effort"],
                _json(task["dependency_chain"]),
                task["expected_health_impact"],
                task["owner"],
                None,
                None,
                None,
                task["priority_score"],
                task["priority_bucket"],
                int(task["blocked"]),
                task["status"],
                created_at,
                created_at,
            ),
        )

    return len(delta_items), len(tasks)


def _persist_snapshot(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    project_id: str,
    profile_id: str,
    attached_version: str,
    latest_version: str,
    score: dict[str, Any],
    migration: dict[str, Any],
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO standards_health_snapshots (
            id,
            project_id,
            profile_id,
            attached_version,
            latest_version,
            standards_version,
            overall_score,
            weighted_delta,
            max_penalty,
            unmet_standards_count,
            critical_delta_count,
            regression_count,
            unknown_count,
            unknown_coverage,
            evaluation_confidence,
            domain_scores_json,
            score_explain_json,
            migration_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            project_id,
            profile_id,
            attached_version,
            latest_version,
            latest_version,
            score["overall_score"],
            score["weighted_delta"],
            score["max_penalty"],
            score["unmet_standards_count"],
            score["critical_delta_count"],
            score["regression_count"],
            score["unknown_count"],
            score["unknown_coverage"],
            score["evaluation_confidence"],
            _json(score["domain_scores"]),
            _json(
                {
                    "penalty_multipliers": PENALTY_MULTIPLIERS,
                    "regressed_fail_multiplier": MAX_PENALTY_MULTIPLIER,
                }
            ),
            _json(migration),
            created_at,
        ),
    )


def evaluate_and_record(
    conn: sqlite3.Connection,
    *,
    project_id: str | None,
    project_name: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    trigger_kind: str = "session_close",
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    overrides: dict[str, ManualAssessmentOverride] | None = None,
) -> dict[str, Any]:
    if not project_id:
        return {
            "snapshot_id": None,
            "summary": "Standards health skipped: session was not linked to a project.",
            "health_score": None,
            "critical_delta_count": 0,
            "unmet_standards_count": 0,
            "regression_count": 0,
            "unknown_count": 0,
            "delta_item_count": 0,
            "backfill_task_count": 0,
            "trigger_kind": trigger_kind,
        }

    ensure_standards_health_schema(conn)
    profile, standards = seed_registry(conn, path=registry_path)
    profile_id = str(profile.get("id"))
    attached_version, latest_version = _ensure_project_binding(
        conn,
        project_id=project_id,
        profile=profile,
    )

    repo_path = _project_repo_path(conn, project_id)
    previous_status = _latest_status_map(conn, project_id)
    created_at = _now_iso()

    applied_overrides = {
        **_load_manual_overrides(conn, project_id),
        **(overrides or {}),
    }
    migration_items: list[dict[str, Any]] = []
    evaluations: list[EvaluatedStandard] = []

    for standard in standards:
        if standard.profile_id != profile_id:
            continue

        override = applied_overrides.get(standard.id)
        if _version_gt(standard.introduced_version, attached_version) and override is None:
            migration_items.append(
                {
                    "standard_id": standard.id,
                    "title": standard.title,
                    "domain": standard.domain,
                    "introduced_version": standard.introduced_version,
                    "weight": standard.weight,
                }
            )
            evaluations.append(
                EvaluatedStandard(
                    standard=standard,
                    status="not_applicable",
                    reason=(
                        f"Standard introduced in {standard.introduced_version}; project is pinned to {attached_version}."
                    ),
                    measured_state={"attached_version": attached_version},
                    evidence=(),
                    evaluator_type="migration",
                    confidence=1.0,
                    regression_flag=False,
                    waiver_rationale=None,
                    waiver_owner=None,
                    waiver_review_at=None,
                    waiver_affects_portfolio=True,
                )
            )
            continue

        if override is not None:
            status = cast(AssessmentStatus, override.get("status", "unknown"))
            reason = str(override.get("reason") or "Manual override applied.")
            measured_state = cast(dict[str, Any], override.get("measured_state") or {})
            evidence = tuple(str(item) for item in override.get("evidence", []) if item)
            confidence = float(override.get("confidence", 0.95))
            regression_flag = bool(override.get("regression_flag", False))
            evaluator_type = "manual"
            waiver_rationale = override.get("waiver_rationale")
            waiver_owner = override.get("waiver_owner")
            waiver_review_at = override.get("waiver_review_at")
            waiver_affects_portfolio = bool(override.get("waiver_affects_portfolio", True))
        else:
            (
                status,
                reason,
                confidence,
                measured_state,
                evidence_list,
                evaluator_type,
            ) = _evaluate_known_standard(
                conn,
                project_id=project_id,
                standard=standard,
                repo_path=repo_path,
            )
            evidence = tuple(evidence_list)
            waiver_rationale = None
            waiver_owner = None
            waiver_review_at = None
            waiver_affects_portfolio = True
            regression_flag = status == "fail" and previous_status.get(
                standard.id, "not_applicable"
            ) not in {"fail", "not_applicable"}

        if status == "waived" and not waiver_rationale:
            waiver_rationale = "Waived without rationale (should be updated by reviewer)."

        evaluations.append(
            EvaluatedStandard(
                standard=standard,
                status=status,
                reason=reason,
                measured_state=measured_state,
                evidence=evidence,
                evaluator_type=evaluator_type,
                confidence=max(0.0, min(1.0, confidence)),
                regression_flag=regression_flag,
                waiver_rationale=waiver_rationale,
                waiver_owner=waiver_owner,
                waiver_review_at=waiver_review_at,
                waiver_affects_portfolio=waiver_affects_portfolio,
            )
        )

    score = _compute_score(evaluations)
    delta_items = _build_delta_items(evaluations, score)
    tasks = _build_task_rows(
        project_id=project_id,
        snapshot_id="pending",
        delta_items=delta_items,
        created_at=created_at,
    )

    snapshot_id = f"health-snapshot-{uuid.uuid4()}"

    for task in tasks:
        task["snapshot_id"] = snapshot_id

    migration = {
        "attached_version": attached_version,
        "latest_version": latest_version,
        "migration_delta_count": len(migration_items),
        "migration_weight": round(sum(float(item["weight"]) for item in migration_items), 3),
        "items": migration_items,
    }

    _persist_snapshot(
        conn,
        snapshot_id=snapshot_id,
        project_id=project_id,
        profile_id=profile_id,
        attached_version=attached_version,
        latest_version=latest_version,
        score=score,
        migration=migration,
        created_at=created_at,
    )
    _persist_assessments(
        conn,
        snapshot_id=snapshot_id,
        project_id=project_id,
        evaluations=evaluations,
        created_at=created_at,
    )
    delta_count, task_count = _persist_delta_and_tasks(
        conn,
        snapshot_id=snapshot_id,
        project_id=project_id,
        delta_items=delta_items,
        tasks=tasks,
        created_at=created_at,
    )

    project_label = project_name or project_id
    summary = (
        f"{project_label} health {score['overall_score']:.2f} "
        f"with {score['critical_delta_count']} critical deltas and {score['unknown_count']} unknown standards."
    )

    return {
        "snapshot_id": snapshot_id,
        "summary": summary,
        "health_score": score["overall_score"],
        "critical_delta_count": score["critical_delta_count"],
        "unmet_standards_count": score["unmet_standards_count"],
        "regression_count": score["regression_count"],
        "unknown_count": score["unknown_count"],
        "unknown_coverage": score["unknown_coverage"],
        "evaluation_confidence": score["evaluation_confidence"],
        "delta_item_count": delta_count,
        "backfill_task_count": task_count,
        "profile_id": profile_id,
        "attached_version": attached_version,
        "latest_version": latest_version,
        "trigger_kind": trigger_kind,
        "run_id": run_id,
        "session_id": session_id,
    }


def latest_snapshot(
    conn: sqlite3.Connection, project_id: str | None = None
) -> dict[str, Any] | None:
    ensure_standards_health_schema(conn)
    if project_id:
        row = conn.execute(
            """
            SELECT
                id,
                project_id,
                profile_id,
                attached_version,
                latest_version,
                overall_score,
                critical_delta_count,
                regression_count,
                unknown_count,
                evaluation_confidence,
                created_at
            FROM standards_health_snapshots
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT
                id,
                project_id,
                profile_id,
                attached_version,
                latest_version,
                overall_score,
                critical_delta_count,
                regression_count,
                unknown_count,
                evaluation_confidence,
                created_at
            FROM standards_health_snapshots
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "project_id": row[1],
        "profile_id": row[2],
        "attached_version": row[3],
        "latest_version": row[4],
        "overall_score": row[5],
        "critical_delta_count": row[6],
        "regression_count": row[7],
        "unknown_count": row[8],
        "evaluation_confidence": row[9],
        "created_at": row[10],
    }


def registry_summary(path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {
            "profile_id": None,
            "profile_version": None,
            "standard_count": 0,
            "domains": [],
            "registry_path": str(path),
        }

    profile, standards = load_registry(path)
    domains = sorted({standard.domain for standard in standards})
    return {
        "profile_id": profile.get("id"),
        "profile_version": profile.get("version"),
        "default_attached_version": profile.get("default_attached_version"),
        "standard_count": len(standards),
        "domains": domains,
        "registry_path": str(path),
    }
