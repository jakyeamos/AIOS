from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "config" / "success-criteria" / "registry.json"
SKILL_MAP_PATH = REPO_ROOT / "config" / "success-criteria" / "skill-map.json"
ARTIFACTS_DIR = REPO_ROOT / "data" / "success-criteria" / "evaluations"
EVALUATOR_VERSION = "v1"

CODE_FILE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".go",
    ".rb",
    ".rs",
    ".java",
    ".kt",
    ".swift",
    ".sh",
    ".sql",
}
EVALUATION_FINDING_LIFECYCLE_STATES = ("open", "accepted", "resolved", "waived", "stale")
TEST_PATH_MARKERS = ("test", "__tests__", "spec", "pytest", "integration")
DOC_PATH_MARKERS = ("/docs/", "/.planning/", "/spec/")
SENSITIVE_PATH_MARKERS = ("auth", "security", "secret", "token", "permission", "crypto")
OBSERVABILITY_MARKERS = ("log", "metric", "trace", "telemetry", "observability", "monitor")
EXECUTION_FIRST_PATH_MARKERS = (
    "/services/",
    "/bin/",
    "/server/",
    "/lib/",
    "schema.sql",
    "schema.ts",
    "types.ts",
    "model",
    "orchestration",
    "workflow",
)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


@dataclass(frozen=True)
class CriterionRecord:
    id: str
    title: str
    scope: str
    blocking: bool
    applies_when: dict[str, list[str]]
    path: str
    related: list[str]
    evaluation_method: str
    stage_applicability: tuple[str, ...] = ()


@dataclass(frozen=True)
class CriterionFinding:
    criterion_id: str
    criterion_title: str
    criterion_scope: str
    level: str
    summary: str
    evidence: list[str]
    metadata: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return loaded


def load_registry(path: Path = REGISTRY_PATH) -> list[CriterionRecord]:
    loaded = _load_json(path)
    criteria = loaded.get("criteria", [])
    if not isinstance(criteria, list):
        raise ValueError("Registry criteria must be a list")

    rows: list[CriterionRecord] = []
    for item in criteria:
        if not isinstance(item, dict):
            continue
        applies_when_raw = item.get("applies_when", {})
        applies_when = (
            {
                key: [str(value) for value in values]
                for key, values in applies_when_raw.items()
                if isinstance(values, list)
            }
            if isinstance(applies_when_raw, dict)
            else {}
        )
        rows.append(
            CriterionRecord(
                id=str(item.get("id", "")),
                title=str(item.get("title", "")),
                scope=str(item.get("scope", "global")),
                blocking=bool(item.get("blocking", False)),
                applies_when=applies_when,
                path=str(item.get("path", "")),
                related=[
                    str(related) for related in item.get("related", []) if isinstance(related, str)
                ],
                evaluation_method=str(item.get("evaluation_method", "heuristic")),
                stage_applicability=tuple(
                    str(stage)
                    for stage in item.get("stage_applicability", [])
                    if isinstance(stage, str) and stage
                ),
            )
        )
    return rows


def load_skill_map(path: Path = SKILL_MAP_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    loaded = _load_json(path)
    mappings = loaded.get("skill_to_criteria", {})
    if not isinstance(mappings, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for skill, criteria in mappings.items():
        if not isinstance(criteria, list):
            continue
        normalized[str(skill)] = [str(criterion) for criterion in criteria]
    return normalized


def ensure_success_criteria_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS success_criteria_evaluations (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id),
            run_id TEXT REFERENCES orchestration_runs(id),
            session_id TEXT REFERENCES sessions(id),
            packet_id TEXT REFERENCES briefing_packets(id),
            task_id TEXT,
            objective TEXT,
            trigger_kind TEXT NOT NULL,
            evaluator_version TEXT NOT NULL,
            criteria_ids_json TEXT NOT NULL DEFAULT '[]',
            files_changed_json TEXT NOT NULL DEFAULT '[]',
            pass_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            blocker_count INTEGER NOT NULL DEFAULT 0,
            accepted_tradeoffs_json TEXT NOT NULL DEFAULT '[]',
            summary TEXT NOT NULL,
            artifact_path TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_success_criteria_eval_project
          ON success_criteria_evaluations(project_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_success_criteria_eval_run
          ON success_criteria_evaluations(run_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS success_criteria_findings (
            id TEXT PRIMARY KEY,
            evaluation_id TEXT NOT NULL REFERENCES success_criteria_evaluations(id),
            criterion_id TEXT NOT NULL,
            criterion_title TEXT NOT NULL,
            criterion_scope TEXT NOT NULL,
            level TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    for column, definition in {
        "resolution_status": "TEXT NOT NULL DEFAULT 'open'",
        "resolution_actor": "TEXT",
        "resolution_rationale": "TEXT",
        "resolution_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
        "resolved_at": "TEXT",
    }.items():
        _ensure_column(conn, "success_criteria_findings", column, definition)
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_success_criteria_findings_eval
          ON success_criteria_findings(evaluation_id, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS success_criteria_stage_findings (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES orchestration_runs(id),
            stage_key TEXT NOT NULL,
            stage_kind TEXT NOT NULL,
            criterion_id TEXT NOT NULL,
            criterion_title TEXT NOT NULL,
            criterion_scope TEXT NOT NULL,
            level TEXT NOT NULL,
            summary TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            resolution_status TEXT NOT NULL DEFAULT 'open',
            resolution_actor TEXT,
            resolution_rationale TEXT,
            resolution_evidence_json TEXT NOT NULL DEFAULT '[]',
            resolved_at TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_success_criteria_stage_findings_run
          ON success_criteria_stage_findings(run_id, stage_key)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_success_criteria_stage_findings_criterion
          ON success_criteria_stage_findings(criterion_id, level)
        """
    )


def _contains_any(text: str, needles: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _unique_paths(paths: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        normalized = str(Path(path)).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def infer_context(
    *,
    objective: str | None,
    prompt_classifications: Sequence[str] | None,
    changed_files: Sequence[str] | None,
    skills: Sequence[str] | None,
) -> dict[str, Any]:
    objective_text = objective or ""
    changed = _unique_paths(changed_files or [])
    classifications = sorted({str(item).lower() for item in (prompt_classifications or []) if item})
    requested_skills = sorted({str(item) for item in (skills or []) if item})

    task_types: set[str] = set()
    domains: set[str] = set()

    if changed:
        task_types.add("implementation")

    for classification in classifications:
        if classification == "debug":
            task_types.add("bugfix")
            domains.add("reliability")
        if classification == "review":
            task_types.add("review")
        if classification == "refactor":
            task_types.add("refactor")
        if classification == "plan":
            task_types.add("planning")
        if classification == "implement":
            task_types.add("implementation")

    objective_lower = objective_text.lower()
    explicit_security_focus = _contains_any(
        objective_lower, ("security", "auth", "token", "permission", "secret")
    ) or any("security" in skill.lower() for skill in requested_skills)
    if _contains_any(objective_lower, ("test", "pytest", "unit", "integration", "coverage")):
        task_types.add("testing")
        domains.add("testing")
    if explicit_security_focus:
        domains.add("security")
    if _contains_any(objective_lower, OBSERVABILITY_MARKERS):
        domains.add("observability")
    if _contains_any(objective_lower, ("workflow", "orchestration", "run", "invocation")):
        domains.add("workflow")

    if any(_contains_any(path.lower(), TEST_PATH_MARKERS) for path in changed):
        task_types.add("testing")
        domains.add("testing")
    if any(_contains_any(path.lower(), OBSERVABILITY_MARKERS) for path in changed):
        domains.add("observability")
    if any(_contains_any(path.lower(), SENSITIVE_PATH_MARKERS) for path in changed):
        domains.add("security")

    execution_first_triggers: set[str] = set()
    code_changes = [path for path in changed if _is_code_path(path)]
    test_changes = [path for path in changed if _is_test_path(path)]
    if code_changes and (
        _contains_any(objective_lower, ("side effect", "state", "database", "db", "sqlite"))
        or any(Path(path).suffix.lower() == ".sql" for path in changed)
    ):
        execution_first_triggers.add("non-trivial side effects or state")
    if code_changes and (
        _contains_any(objective_lower, ("api", "http", "workflow", "orchestration", "cross-system"))
        or bool({"workflow", "observability", "security"} & domains)
    ):
        execution_first_triggers.add("cross-system interactions")
    if code_changes and any(
        _contains_any(f"/{path.lower()}", EXECUTION_FIRST_PATH_MARKERS) and _is_code_path(path)
        for path in changed
    ):
        execution_first_triggers.add("core/shared logic modification")
    if "bugfix" in task_types or _contains_any(
        objective_lower,
        ("debug", "inconsistent behavior", "inconsistent"),
    ):
        execution_first_triggers.add("debugging inconsistent behavior")
    if code_changes and not test_changes:
        execution_first_triggers.add("low trust in tests")
    if code_changes and (
        _contains_any(objective_lower, ("complex domain", "domain model"))
        or any(
            _contains_any(path.lower(), ("schema", "types", "model", "orchestration"))
            for path in changed
        )
    ):
        execution_first_triggers.add("complex domain models")

    return {
        "task_types": sorted(task_types),
        "domains": sorted(domains),
        "skills": requested_skills,
        "changed_files": changed,
        "prompt_classifications": classifications,
        "objective": objective_text,
        "explicit_security_focus": explicit_security_focus,
        "execution_first_triggers": sorted(execution_first_triggers),
    }


def _matches(values: Sequence[str], allowed: Sequence[str]) -> bool:
    if not allowed:
        return True
    if "*" in allowed:
        return True
    return bool(set(values) & set(allowed))


def resolve_applicable_criteria(
    *,
    registry: Sequence[CriterionRecord],
    context: dict[str, Any],
    project_id: str | None = None,
    project_name: str | None = None,
    skill_map: dict[str, list[str]] | None = None,
) -> list[CriterionRecord]:
    skill_map = skill_map or {}
    criteria_by_id = {criterion.id: criterion for criterion in registry}
    skill_linked: set[str] = set()
    for skill in context.get("skills", []):
        for criterion_id in skill_map.get(skill, []):
            if criterion_id in criteria_by_id:
                skill_linked.add(criterion_id)

    applicable: list[CriterionRecord] = []
    for criterion in registry:
        rules = criterion.applies_when
        if criterion.scope == "global":
            applicable.append(criterion)
            continue

        project_ids = rules.get("project_ids", [])
        project_names = rules.get("project_names", [])
        if project_ids and (project_id not in project_ids):
            continue
        if project_names and (project_name not in project_names):
            continue

        task_match = _matches(context.get("task_types", []), rules.get("task_types", []))
        domain_match = _matches(context.get("domains", []), rules.get("domains", []))
        skill_match = _matches(context.get("skills", []), rules.get("skills", []))

        if criterion.id in skill_linked:
            applicable.append(criterion)
            continue

        if task_match and domain_match and skill_match:
            applicable.append(criterion)

    seen: set[str] = set()
    deduped: list[CriterionRecord] = []
    for criterion in applicable:
        if criterion.id in seen:
            continue
        seen.add(criterion.id)
        deduped.append(criterion)
    return deduped


def _is_test_path(path: str) -> bool:
    return _contains_any(path.lower(), TEST_PATH_MARKERS)


def _is_code_path(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in CODE_FILE_EXTENSIONS and not _is_test_path(path)


def _evaluate_testing_trust(
    context: dict[str, Any], criterion: CriterionRecord
) -> CriterionFinding:
    changed = context.get("changed_files", [])
    code_changes = [path for path in changed if _is_code_path(path)]
    test_changes = [path for path in changed if _is_test_path(path)]

    if code_changes and not test_changes:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "warning",
            "Code changed without accompanying tests; trust evidence is incomplete.",
            code_changes[:6],
            {"code_changes": len(code_changes), "test_changes": 0},
        )
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        "pass",
        "Testing trust baseline is satisfied for the observed change set.",
        test_changes[:6],
        {"code_changes": len(code_changes), "test_changes": len(test_changes)},
    )


def _evaluate_code_simplicity(
    context: dict[str, Any], criterion: CriterionRecord
) -> CriterionFinding:
    changed = context.get("changed_files", [])
    code_changes = [path for path in changed if _is_code_path(path)]
    if len(code_changes) > 40:
        level = "blocker"
        summary = "Large code surface changed; complexity risk exceeds simplicity threshold."
    elif len(code_changes) > 20:
        level = "warning"
        summary = "Broad code change set may hide unnecessary complexity."
    else:
        level = "pass"
        summary = "Code change surface remains within simplicity guardrail."
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        level,
        summary,
        code_changes[:8],
        {"code_changes": len(code_changes)},
    )


def _evaluate_security_review(
    context: dict[str, Any], criterion: CriterionRecord
) -> CriterionFinding:
    changed = context.get("changed_files", [])
    sensitive_changes = [
        path for path in changed if _contains_any(path.lower(), SENSITIVE_PATH_MARKERS)
    ]
    explicit_security_focus = bool(context.get("explicit_security_focus"))
    if any(path.lower().endswith(".env") for path in changed):
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "blocker",
            "Environment file changes require explicit security review evidence.",
            [path for path in changed if path.lower().endswith(".env")],
            {},
        )
    if sensitive_changes and not explicit_security_focus:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "warning",
            "Sensitive paths changed without explicit security-focused context.",
            sensitive_changes[:8],
            {"explicit_security_focus": False},
        )
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        "pass",
        "No sensitive-path security warning detected.",
        sensitive_changes[:8],
        {"explicit_security_focus": explicit_security_focus},
    )


def _evaluate_observability(
    context: dict[str, Any], criterion: CriterionRecord
) -> CriterionFinding:
    changed = context.get("changed_files", [])
    code_changes = [path for path in changed if _is_code_path(path)]
    observability_changes = [
        path for path in changed if _contains_any(path.lower(), OBSERVABILITY_MARKERS)
    ]
    if code_changes and not observability_changes and "observability" in context.get("domains", []):
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "warning",
            "Observability-related objective lacks explicit telemetry/logging evidence in changed files.",
            code_changes[:8],
            {},
        )
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        "pass",
        "Observability baseline check did not detect a blocking gap.",
        observability_changes[:8],
        {"observability_changes": len(observability_changes)},
    )


def _evaluate_truth_file_consistency(
    context: dict[str, Any],
    criterion: CriterionRecord,
) -> CriterionFinding:
    changed = context.get("changed_files", [])
    objective = context.get("objective", "")
    has_truth_file_change = any(Path(path).name == "PROJECT.md" for path in changed)
    substantial_code_change = any(_is_code_path(path) for path in changed)
    project_name = (context.get("project_name") or "").lower()

    if substantial_code_change and not has_truth_file_change:
        level = "blocker" if project_name == "aios" else "warning"
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            level,
            "Substantial code changes were detected without a project truth-file update.",
            changed[:8],
            {"objective": objective},
        )
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        "pass",
        "Truth-file consistency check passed for this change set.",
        [path for path in changed if Path(path).name == "PROJECT.md"][:4],
        {},
    )


def _evaluate_repo_boundary_discipline(
    context: dict[str, Any],
    criterion: CriterionRecord,
) -> CriterionFinding:
    changed = context.get("changed_files", [])
    cwd = context.get("cwd")
    if not cwd:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "pass",
            "No working-directory boundary was provided; boundary check skipped.",
            [],
            {},
        )
    cwd_path = Path(cwd).resolve()
    out_of_bounds: list[str] = []
    for path in changed:
        resolved = Path(path).expanduser()
        if not resolved.is_absolute():
            resolved = (cwd_path / resolved).resolve()
        try:
            resolved.relative_to(cwd_path)
        except ValueError:
            out_of_bounds.append(str(resolved))

    if out_of_bounds:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "blocker",
            "Changed files outside project boundary were detected.",
            out_of_bounds[:8],
            {"cwd": str(cwd_path)},
        )
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        "pass",
        "All changed files stayed within project boundary.",
        changed[:8],
        {"cwd": str(cwd_path)},
    )


def _evaluate_workflow_state_integrity(
    context: dict[str, Any],
    criterion: CriterionRecord,
) -> CriterionFinding:
    run_id = context.get("run_id")
    used_legacy_link = bool(context.get("used_legacy_link", False))
    trigger_kind = context.get("trigger_kind")
    if trigger_kind == "session_close" and not run_id:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "warning",
            "Session closed without linked orchestration run; lifecycle trace is incomplete.",
            [],
            {},
        )
    if used_legacy_link:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "warning",
            "Legacy run linkage fallback was used; explicit handshake is preferred.",
            [],
            {},
        )
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        "pass",
        "Workflow linkage and state integrity checks passed.",
        [],
        {},
    )


def _evaluate_execution_first_verification(
    context: dict[str, Any],
    criterion: CriterionRecord,
) -> CriterionFinding:
    triggers = [str(item) for item in context.get("execution_first_triggers", []) if item]
    evidence = [str(item) for item in context.get("execution_evidence", []) if item]
    if not triggers:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "pass",
            "Execution-first verification was not triggered for the observed change set.",
            [],
            {"triggers": []},
        )
    if evidence:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "pass",
            "Execution-first verification evidence was recorded for the triggered change set.",
            evidence[:8],
            {"triggers": triggers, "evidence_count": len(evidence)},
        )
    return CriterionFinding(
        criterion.id,
        criterion.title,
        criterion.scope,
        "blocker",
        "Execution-first verification was triggered but no direct execution evidence was recorded.",
        triggers[:8],
        {"triggers": triggers},
    )


def evaluate_criterion(
    criterion: CriterionRecord,
    context: dict[str, Any],
) -> CriterionFinding:
    evaluators = {
        "testing-trust": _evaluate_testing_trust,
        "code-simplicity": _evaluate_code_simplicity,
        "security-review": _evaluate_security_review,
        "observability": _evaluate_observability,
        "truth-file-consistency": _evaluate_truth_file_consistency,
        "repo-boundary-discipline": _evaluate_repo_boundary_discipline,
        "workflow-state-integrity": _evaluate_workflow_state_integrity,
        "execution-first-verification": _evaluate_execution_first_verification,
    }
    evaluator = evaluators.get(criterion.id)
    if evaluator is None:
        return CriterionFinding(
            criterion.id,
            criterion.title,
            criterion.scope,
            "pass",
            "No automated evaluator registered; treated as advisory pass.",
            [],
            {"evaluation_method": criterion.evaluation_method},
        )
    finding = evaluator(context, criterion)
    if criterion.blocking and finding.level == "warning":
        return CriterionFinding(
            finding.criterion_id,
            finding.criterion_title,
            finding.criterion_scope,
            "blocker",
            finding.summary,
            finding.evidence,
            finding.metadata,
        )
    return finding


def evaluate_context(
    *,
    registry: Sequence[CriterionRecord],
    skill_map: dict[str, list[str]],
    context: dict[str, Any],
    project_id: str | None,
    project_name: str | None,
) -> dict[str, Any]:
    applicable = resolve_applicable_criteria(
        registry=registry,
        context=context,
        project_id=project_id,
        project_name=project_name,
        skill_map=skill_map,
    )
    findings = [evaluate_criterion(criterion, context) for criterion in applicable]
    pass_count = sum(1 for finding in findings if finding.level == "pass")
    warning_count = sum(1 for finding in findings if finding.level == "warning")
    blocker_count = sum(1 for finding in findings if finding.level == "blocker")

    summary = (
        f"{len(findings)} criteria evaluated: {pass_count} pass, "
        f"{warning_count} warning, {blocker_count} blocker."
    )

    return {
        "criteria": applicable,
        "findings": findings,
        "summary": summary,
        "counts": {
            "pass": pass_count,
            "warning": warning_count,
            "blocker": blocker_count,
        },
    }


def _stage_kinds_for_criterion(criterion: CriterionRecord) -> tuple[str, ...]:
    return criterion.stage_applicability or ("validate",)


def evaluate_stage_findings(
    *,
    criteria: Sequence[CriterionRecord],
    context: dict[str, Any],
    stage_key: str,
    stage_kind: str,
    run_state: dict[str, Any],
) -> list[dict[str, Any]]:
    stage_context = dict(context)
    stage_context.update(
        {
            "stage_key": stage_key,
            "stage_kind": stage_kind,
            "run_state": run_state,
        }
    )
    findings: list[dict[str, Any]] = []
    for criterion in criteria:
        if stage_kind not in _stage_kinds_for_criterion(criterion):
            continue
        finding = evaluate_criterion(criterion, stage_context)
        findings.append(
            {
                "criterion_id": finding.criterion_id,
                "criterion_title": finding.criterion_title,
                "criterion_scope": finding.criterion_scope,
                "level": finding.level,
                "summary": finding.summary,
                "evidence": finding.evidence,
                "metadata": finding.metadata,
            }
        )
    return findings


def persist_stage_findings(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    stage_key: str,
    stage_kind: str,
    findings: Sequence[dict[str, Any]],
    artifact_root: Path = ARTIFACTS_DIR,
) -> dict[str, Any]:
    if not findings:
        return {
            "finding_ids": [],
            "artifact_path": None,
            "blocker_count": 0,
            "warning_count": 0,
            "pass_count": 0,
        }
    ensure_success_criteria_schema(conn)
    finding_ids: list[str] = []
    for finding in findings:
        finding_id = f"criteria-stage-finding-{uuid.uuid4()}"
        finding_ids.append(finding_id)
        conn.execute(
            """
            INSERT INTO success_criteria_stage_findings (
                id,
                run_id,
                stage_key,
                stage_kind,
                criterion_id,
                criterion_title,
                criterion_scope,
                level,
                summary,
                evidence_json,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding_id,
                run_id,
                stage_key,
                stage_kind,
                str(finding["criterion_id"]),
                str(finding["criterion_title"]),
                str(finding["criterion_scope"]),
                str(finding["level"]),
                str(finding["summary"]),
                _json(finding.get("evidence", [])),
                _json(finding.get("metadata", {})),
            ),
        )

    pass_count = sum(1 for finding in findings if finding.get("level") == "pass")
    warning_count = sum(1 for finding in findings if finding.get("level") == "warning")
    blocker_count = sum(1 for finding in findings if finding.get("level") == "blocker")
    artifact_root.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_root / f"stage-{run_id}-{stage_key}.json"
    artifact_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "stage_key": stage_key,
                "stage_kind": stage_kind,
                "finding_ids": finding_ids,
                "counts": {
                    "pass": pass_count,
                    "warning": warning_count,
                    "blocker": blocker_count,
                },
                "findings": list(findings),
                "created_at": _now_iso(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {
        "finding_ids": finding_ids,
        "artifact_path": str(artifact_path),
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "pass_count": pass_count,
    }


def resolve_finding(
    conn: sqlite3.Connection,
    *,
    finding_id: str,
    status: str,
    actor: str,
    rationale: str | None = None,
    evidence: Sequence[str] | None = None,
) -> dict[str, Any]:
    if status not in EVALUATION_FINDING_LIFECYCLE_STATES:
        raise ValueError(f"Invalid finding resolution status: {status}")
    if finding_id.startswith("criteria-stage-finding-"):
        table = "success_criteria_stage_findings"
        scope = "stage"
    elif finding_id.startswith("criteria-finding-"):
        table = "success_criteria_findings"
        scope = "run"
    else:
        raise ValueError(f"Unknown finding id scope: {finding_id}")
    if not _table_exists(conn, table):
        raise ValueError(f"Finding table is unavailable: {table}")

    row = conn.execute(
        f"SELECT resolution_status FROM {table} WHERE id = ? LIMIT 1",
        (finding_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Finding not found: {finding_id}")
    now = _now_iso()
    conn.execute(
        f"""
        UPDATE {table}
        SET resolution_status = ?,
            resolution_actor = ?,
            resolution_rationale = ?,
            resolution_evidence_json = ?,
            resolved_at = ?
        WHERE id = ?
        """,
        (status, actor, rationale, _json(list(evidence or [])), now, finding_id),
    )
    return {
        "finding_id": finding_id,
        "scope": scope,
        "previous_status": str(row[0] or "open"),
        "new_status": status,
        "resolved_at": now,
    }


def record_evaluation(
    conn: sqlite3.Connection,
    *,
    project_id: str | None,
    run_id: str | None,
    session_id: str | None,
    packet_id: str | None,
    objective: str | None,
    task_id: str | None,
    trigger_kind: str,
    context: dict[str, Any],
    findings: Sequence[CriterionFinding],
    accepted_tradeoffs: Sequence[str] | None = None,
) -> str:
    ensure_success_criteria_schema(conn)
    evaluation_id = f"criteria-eval-{uuid.uuid4()}"
    criteria_ids = [finding.criterion_id for finding in findings]
    files_changed = context.get("changed_files", [])
    accepted_tradeoffs = [str(item) for item in (accepted_tradeoffs or [])]

    pass_count = sum(1 for finding in findings if finding.level == "pass")
    warning_count = sum(1 for finding in findings if finding.level == "warning")
    blocker_count = sum(1 for finding in findings if finding.level == "blocker")
    summary = (
        f"Evaluated {len(findings)} criteria for objective '{objective or 'unspecified'}' "
        f"({pass_count} pass / {warning_count} warning / {blocker_count} blocker)."
    )

    artifact_payload = {
        "id": evaluation_id,
        "project_id": project_id,
        "run_id": run_id,
        "session_id": session_id,
        "packet_id": packet_id,
        "task_id": task_id,
        "objective": objective,
        "trigger_kind": trigger_kind,
        "evaluator_version": EVALUATOR_VERSION,
        "criteria_ids": criteria_ids,
        "files_changed": files_changed,
        "counts": {
            "pass": pass_count,
            "warning": warning_count,
            "blocker": blocker_count,
        },
        "accepted_tradeoffs": accepted_tradeoffs,
        "context": context,
        "findings": [
            {
                "criterion_id": finding.criterion_id,
                "criterion_title": finding.criterion_title,
                "criterion_scope": finding.criterion_scope,
                "level": finding.level,
                "summary": finding.summary,
                "evidence": finding.evidence,
                "metadata": finding.metadata,
            }
            for finding in findings
        ],
        "created_at": _now_iso(),
    }
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = ARTIFACTS_DIR / f"{evaluation_id}.json"
    artifact_path.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")

    conn.execute(
        """
        INSERT INTO success_criteria_evaluations (
            id,
            project_id,
            run_id,
            session_id,
            packet_id,
            task_id,
            objective,
            trigger_kind,
            evaluator_version,
            criteria_ids_json,
            files_changed_json,
            pass_count,
            warning_count,
            blocker_count,
            accepted_tradeoffs_json,
            summary,
            artifact_path,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evaluation_id,
            project_id,
            run_id,
            session_id,
            packet_id,
            task_id,
            objective,
            trigger_kind,
            EVALUATOR_VERSION,
            _json(criteria_ids),
            _json(files_changed),
            pass_count,
            warning_count,
            blocker_count,
            _json(accepted_tradeoffs),
            summary,
            str(artifact_path),
            _now_iso(),
        ),
    )

    for finding in findings:
        conn.execute(
            """
            INSERT INTO success_criteria_findings (
                id,
                evaluation_id,
                criterion_id,
                criterion_title,
                criterion_scope,
                level,
                summary,
                evidence_json,
                metadata_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"criteria-finding-{uuid.uuid4()}",
                evaluation_id,
                finding.criterion_id,
                finding.criterion_title,
                finding.criterion_scope,
                finding.level,
                finding.summary,
                _json(finding.evidence),
                _json(finding.metadata),
                _now_iso(),
            ),
        )
    return evaluation_id


def evaluate_and_record(
    conn: sqlite3.Connection,
    *,
    project_id: str | None,
    project_name: str | None,
    run_id: str | None,
    session_id: str | None,
    packet_id: str | None,
    objective: str | None,
    task_id: str | None,
    trigger_kind: str,
    cwd: str | None,
    prompt_classifications: Sequence[str],
    changed_files: Sequence[str],
    skills: Sequence[str] | None = None,
    execution_evidence: Sequence[str] | None = None,
    used_legacy_link: bool = False,
    accepted_tradeoffs: Sequence[str] | None = None,
) -> dict[str, Any]:
    registry = load_registry()
    skill_map = load_skill_map()
    context = infer_context(
        objective=objective,
        prompt_classifications=prompt_classifications,
        changed_files=changed_files,
        skills=skills,
    )
    context["cwd"] = cwd
    context["project_name"] = project_name
    context["run_id"] = run_id
    context["used_legacy_link"] = used_legacy_link
    context["trigger_kind"] = trigger_kind
    context["execution_evidence"] = [str(item) for item in (execution_evidence or []) if item]

    evaluated = evaluate_context(
        registry=registry,
        skill_map=skill_map,
        context=context,
        project_id=project_id,
        project_name=project_name,
    )
    evaluation_id = record_evaluation(
        conn,
        project_id=project_id,
        run_id=run_id,
        session_id=session_id,
        packet_id=packet_id,
        objective=objective,
        task_id=task_id,
        trigger_kind=trigger_kind,
        context=context,
        findings=evaluated["findings"],
        accepted_tradeoffs=accepted_tradeoffs,
    )
    return {
        "evaluation_id": evaluation_id,
        "summary": evaluated["summary"],
        "counts": evaluated["counts"],
        "criteria_ids": [criterion.id for criterion in evaluated["criteria"]],
    }


def preview_applicable_criteria(
    *,
    project_id: str | None,
    project_name: str | None,
    objective: str | None,
    prompt_classifications: Sequence[str] | None = None,
    changed_files: Sequence[str] | None = None,
    skills: Sequence[str] | None = None,
) -> dict[str, Any]:
    registry = load_registry()
    skill_map = load_skill_map()
    context = infer_context(
        objective=objective,
        prompt_classifications=prompt_classifications,
        changed_files=changed_files,
        skills=skills,
    )
    applicable = resolve_applicable_criteria(
        registry=registry,
        context=context,
        project_id=project_id,
        project_name=project_name,
        skill_map=skill_map,
    )
    return {
        "context": {
            "task_types": context["task_types"],
            "domains": context["domains"],
        },
        "criteria": [
            {
                "id": criterion.id,
                "title": criterion.title,
                "scope": criterion.scope,
                "blocking": criterion.blocking,
                "path": criterion.path,
            }
            for criterion in applicable
        ],
    }


def _standard_applies(
    standard: Any,
    *,
    project_name: str | None,
    domains: Sequence[str],
) -> bool:
    applicability = standard.applicability
    if not applicability:
        return True

    project_pattern = str(applicability.get("project_pattern") or "").strip().lower()
    if project_pattern and project_pattern not in (project_name or "").lower():
        return False

    projects = applicability.get("projects")
    if isinstance(projects, list) and projects and "*" not in projects:
        normalized_projects = {str(project).lower() for project in projects}
        if (project_name or "").lower() not in normalized_projects:
            return False

    applicable_domains = applicability.get("domains")
    if isinstance(applicable_domains, list) and applicable_domains:
        return bool(set(domains) & {str(domain) for domain in applicable_domains})

    return True


def _standard_summary(standard: Any) -> dict[str, Any]:
    return {
        "standard_id": standard.id,
        "title": standard.title,
        "domain": standard.domain,
        "weight": standard.weight,
        "severity_if_missing": standard.severity_if_missing,
        "related_criteria": list(standard.related_criteria),
    }


def resolve_task_standards(
    *,
    project_id: str | None,
    project_name: str | None,
    objective: str | None,
    prompt_classifications: Sequence[str] | None = None,
    changed_files: Sequence[str] | None = None,
    skills: Sequence[str] | None = None,
    workflow_key: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    criteria_preview = preview_applicable_criteria(
        project_id=project_id,
        project_name=project_name,
        objective=objective,
        prompt_classifications=prompt_classifications,
        changed_files=changed_files,
        skills=skills,
    )
    context = infer_context(
        objective=objective,
        prompt_classifications=prompt_classifications,
        changed_files=changed_files,
        skills=skills,
    )

    from services import standards_health  # noqa: PLC0415

    profile, standards = standards_health.load_registry()
    registry_profile_id = str(profile.get("id") or "")
    registry_profile_version = str(profile.get("version") or "")
    profile_id = registry_profile_id
    profile_version = registry_profile_version
    resolution_status = "ok"

    if conn is not None and project_id is not None:
        if not _table_exists(conn, "project_standards_profiles"):
            resolution_status = "no_profile_attached"
            standards = []
        else:
            row = conn.execute(
                """
                SELECT profile_id, attached_version, latest_version
                FROM project_standards_profiles
                WHERE project_id = ?
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            if row is None:
                resolution_status = "no_profile_attached"
                standards = []
            else:
                profile_id = str(row[0] or registry_profile_id)
                profile_version = str(row[1] or row[2] or registry_profile_version)
                standards = [
                    standard for standard in standards if standard.profile_id == profile_id
                ]

    domains = [str(domain) for domain in context.get("domains", [])]
    applicable_standards = [
        _standard_summary(standard)
        for standard in standards
        if _standard_applies(standard, project_name=project_name, domains=domains)
    ]

    return {
        "criteria": criteria_preview["criteria"],
        "standards": applicable_standards,
        "execution_first_triggers": context["execution_first_triggers"],
        "workflow_key": workflow_key,
        "resolution_status": resolution_status,
        "profile_id": profile_id,
        "profile_version": profile_version,
    }
