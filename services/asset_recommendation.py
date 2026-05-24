from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from services.asset_lifecycle import AssetLifecycleState

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_REGISTRY = ROOT / "prompts" / "registry.json"
EXPLORATION_SAMPLE_SIZE_THRESHOLD = 10
SUCCESS_OUTCOME_SCORE_THRESHOLD = 0.7
LIFECYCLE_STATE_RANK = {
    "active": 3,
    "approved": 2,
    "candidate": 1,
    "draft": 0,
    "deprecated": -1,
}


@dataclass(frozen=True)
class AssetUsageEvidence:
    asset_kind: str
    asset_key: str
    sample_size: int
    success_count: int
    blocker_count: int
    last_used_at: str | None
    per_workflow: dict[str, dict[str, int]]
    per_task_family: dict[str, dict[str, int]]

    @property
    def success_rate(self) -> float:
        if self.sample_size <= 0:
            return 0.0
        return self.success_count / self.sample_size


@dataclass(frozen=True)
class AssetRecommendation:
    asset_kind: str
    asset_key: str
    lifecycle_state: AssetLifecycleState
    rationale: str
    evidence: AssetUsageEvidence
    rank: int


@dataclass(frozen=True)
class _CandidateAsset:
    asset_kind: str
    asset_key: str
    lifecycle_state: AssetLifecycleState
    applicability: tuple[str, ...]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


def _json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return loaded if isinstance(loaded, list) else []


def _json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _bump(bucket: dict[str, dict[str, int]], key: str, *, succeeded: bool) -> None:
    row = bucket.setdefault(key or "unknown", {"used": 0, "succeeded": 0, "failed": 0})
    row["used"] += 1
    if succeeded:
        row["succeeded"] += 1
    else:
        row["failed"] += 1


def _max_iso(left: str | None, right: str | None) -> str | None:
    if not left:
        return right
    if not right:
        return left
    try:
        return max(left, right, key=datetime.fromisoformat)
    except ValueError:
        return max(left, right)


def _prompt_evidence(
    conn: sqlite3.Connection, *, asset_kind: str, asset_key: str, since: str | None
) -> AssetUsageEvidence:
    if not _table_exists(conn, "prompts_used"):
        return AssetUsageEvidence(asset_kind, asset_key, 0, 0, 0, None, {}, {})
    where = "WHERE (classification = ? OR prompt_text LIKE ?)"
    params: list[Any] = [asset_key, f"%{asset_key}%"]
    if since and _table_exists(conn, "prompts_used"):
        where += " AND COALESCE(rowid, 0) >= 0"
    rows = conn.execute(
        f"""
        SELECT session_id, classification, outcome_score
        FROM prompts_used
        {where}
        """,
        params,
    ).fetchall()
    success_count = 0
    per_task_family: dict[str, dict[str, int]] = {}
    for row in rows:
        score = row[2]
        succeeded = score is not None and float(score) >= SUCCESS_OUTCOME_SCORE_THRESHOLD
        success_count += 1 if succeeded else 0
        _bump(per_task_family, str(row[1] or asset_key), succeeded=succeeded)

    per_workflow: dict[str, dict[str, int]] = {}
    if _table_exists(conn, "workflow_execution_reports"):
        report_rows = conn.execute(
            "SELECT workflow_key, status FROM workflow_execution_reports"
        ).fetchall()
        for workflow_key, status in report_rows:
            _bump(per_workflow, str(workflow_key), succeeded=str(status) == "completed")

    blocker_count = _blocker_count(conn)
    return AssetUsageEvidence(
        asset_kind,
        asset_key,
        len(rows),
        success_count,
        blocker_count,
        None,
        per_workflow,
        per_task_family,
    )


def _skill_evidence(
    conn: sqlite3.Connection, *, asset_kind: str, asset_key: str, since: str | None
) -> AssetUsageEvidence:
    sample_size = 0
    success_count = 0
    last_used_at: str | None = None
    per_workflow: dict[str, dict[str, int]] = {}
    if _table_exists(conn, "workflow_execution_reports"):
        query = (
            "SELECT workflow_key, status, report_json, created_at FROM workflow_execution_reports"
        )
        params: tuple[Any, ...] = ()
        if since:
            query += " WHERE created_at >= ?"
            params = (since,)
        for workflow_key, status, report_json, created_at in conn.execute(query, params).fetchall():
            report = _json_dict(report_json)
            stages = report.get("stages", [])
            found = False
            if isinstance(stages, list):
                for stage in stages:
                    if not isinstance(stage, dict):
                        continue
                    skills = stage.get("skills") or stage.get("required_skills") or []
                    if isinstance(skills, list) and any(
                        (item == asset_key)
                        or (isinstance(item, dict) and item.get("skill_key") == asset_key)
                        for item in skills
                    ):
                        found = True
            if found:
                succeeded = str(status) == "completed"
                sample_size += 1
                success_count += 1 if succeeded else 0
                _bump(per_workflow, str(workflow_key), succeeded=succeeded)
                last_used_at = _max_iso(last_used_at, str(created_at) if created_at else None)

    if _table_exists(conn, "workflow_skill_experiments"):
        rows = conn.execute(
            """
            SELECT workflow_key, candidate_score, outcome, created_at
            FROM workflow_skill_experiments
            WHERE skill_key = ?
            """,
            (asset_key,),
        ).fetchall()
        for workflow_key, candidate_score, outcome, created_at in rows:
            succeeded = str(outcome).lower() in {"success", "improved", "completed"} or (
                candidate_score is not None
                and float(candidate_score) >= SUCCESS_OUTCOME_SCORE_THRESHOLD
            )
            sample_size += 1
            success_count += 1 if succeeded else 0
            _bump(per_workflow, str(workflow_key), succeeded=succeeded)
            last_used_at = _max_iso(last_used_at, str(created_at) if created_at else None)

    return AssetUsageEvidence(
        asset_kind,
        asset_key,
        sample_size,
        success_count,
        _blocker_count(conn),
        last_used_at,
        per_workflow,
        {},
    )


def _workflow_evidence(
    conn: sqlite3.Connection, *, asset_kind: str, asset_key: str, since: str | None
) -> AssetUsageEvidence:
    if not _table_exists(conn, "workflow_execution_reports"):
        return AssetUsageEvidence(asset_kind, asset_key, 0, 0, 0, None, {}, {})
    query = """
        SELECT run_id, workflow_key, status, created_at
        FROM workflow_execution_reports
        WHERE workflow_key = ?
    """
    params: list[Any] = [asset_key]
    if since:
        query += " AND created_at >= ?"
        params.append(since)
    rows = conn.execute(query, params).fetchall()
    success_count = 0
    last_used_at: str | None = None
    per_workflow: dict[str, dict[str, int]] = {}
    for _, workflow_key, status, created_at in rows:
        succeeded = str(status) == "completed"
        success_count += 1 if succeeded else 0
        _bump(per_workflow, str(workflow_key), succeeded=succeeded)
        last_used_at = _max_iso(last_used_at, str(created_at) if created_at else None)
    return AssetUsageEvidence(
        asset_kind,
        asset_key,
        len(rows),
        success_count,
        _blocker_count(conn),
        last_used_at,
        per_workflow,
        {},
    )


def _blocker_count(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "success_criteria_findings"):
        return 0
    row = conn.execute(
        "SELECT COUNT(*) FROM success_criteria_findings WHERE level = 'blocker'"
    ).fetchone()
    return int(row[0]) if row else 0


def build_asset_usage_evidence(
    conn: sqlite3.Connection,
    *,
    asset_kind: str,
    asset_key: str,
    since: str | None = None,
) -> AssetUsageEvidence:
    if asset_kind == "prompt":
        return _prompt_evidence(conn, asset_kind=asset_kind, asset_key=asset_key, since=since)
    if asset_kind == "skill":
        return _skill_evidence(conn, asset_kind=asset_kind, asset_key=asset_key, since=since)
    if asset_kind == "workflow":
        return _workflow_evidence(conn, asset_kind=asset_kind, asset_key=asset_key, since=since)
    return AssetUsageEvidence(asset_kind, asset_key, 0, 0, 0, None, {}, {})


def _load_prompt_candidates() -> list[_CandidateAsset]:
    with DEFAULT_PROMPT_REGISTRY.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    templates = loaded.get("templates", []) if isinstance(loaded, dict) else []
    candidates: list[_CandidateAsset] = []
    if not isinstance(templates, list):
        return candidates
    for row in templates:
        if not isinstance(row, dict):
            continue
        state = str(row.get("lifecycle_state", row.get("route_status", "candidate")))
        if state == "approved" and "lifecycle_state" not in row:
            state = "active"
        if state not in LIFECYCLE_STATE_RANK:
            continue
        candidates.append(
            _CandidateAsset(
                asset_kind="prompt",
                asset_key=str(row.get("id", "")).strip(),
                lifecycle_state=state,  # type: ignore[arg-type]
                applicability=tuple(
                    str(item)
                    for item in (
                        row.get("applicability") or row.get("applicable_workflow_families") or []
                    )
                    if isinstance(item, str)
                ),
            )
        )
    return [candidate for candidate in candidates if candidate.asset_key]


def _load_candidates(asset_kind: str) -> list[_CandidateAsset]:
    if asset_kind == "prompt":
        return _load_prompt_candidates()
    if asset_kind == "skill":
        from services.workflow_orchestration import load_skill_registry

        return [
            _CandidateAsset("skill", spec.key, spec.lifecycle_state, spec.applicability)
            for spec in load_skill_registry().values()
        ]
    if asset_kind == "workflow":
        from services.workflow_orchestration import load_workflow_registry

        return [
            _CandidateAsset(
                "workflow",
                spec.key,
                spec.lifecycle_state,
                spec.applicability or (spec.workflow_family,),
            )
            for spec in load_workflow_registry().values()
        ]
    return []


def _applicability_matches(
    applicability: tuple[str, ...],
    *,
    task_classifications: tuple[str, ...],
    workflow_family: str | None,
) -> bool:
    if not applicability or (not workflow_family and not task_classifications):
        return True
    needles = {item.lower().replace("-", "_") for item in task_classifications}
    if workflow_family:
        needles.add(workflow_family.lower().replace("-", "_"))
    haystack = {item.lower().replace("-", "_") for item in applicability}
    return bool(needles & haystack)


def _top_workflow(evidence: AssetUsageEvidence) -> str:
    if not evidence.per_workflow:
        return "n/a"
    return max(evidence.per_workflow.items(), key=lambda item: item[1]["used"])[0]


def _recommendation_from_candidate(
    candidate: _CandidateAsset,
    evidence: AssetUsageEvidence,
    *,
    rank: int,
    exploration: bool = False,
) -> AssetRecommendation:
    prefix = "exploration: low sample_size for active assets; " if exploration else ""
    rationale = (
        f"{prefix}{candidate.lifecycle_state} asset; "
        f"success_rate={evidence.success_rate:.2f} over sample_size={evidence.sample_size}; "
        f"recent_use={evidence.last_used_at}; per_workflow_top={_top_workflow(evidence)}"
    )
    return AssetRecommendation(
        asset_kind=candidate.asset_kind,
        asset_key=candidate.asset_key,
        lifecycle_state=candidate.lifecycle_state,
        rationale=rationale,
        evidence=evidence,
        rank=rank,
    )


def recommend_assets_for_packet(
    conn: sqlite3.Connection,
    *,
    task_classifications: tuple[str, ...],
    workflow_family: str | None,
    project_id: str | None,
    asset_kind: str,
    limit: int = 5,
) -> list[AssetRecommendation]:
    del project_id
    eligible = [
        candidate
        for candidate in _load_candidates(asset_kind)
        if LIFECYCLE_STATE_RANK.get(candidate.lifecycle_state, -1) >= 1
        and _applicability_matches(
            candidate.applicability,
            task_classifications=task_classifications,
            workflow_family=workflow_family,
        )
    ]
    scored = [
        (
            candidate,
            build_asset_usage_evidence(
                conn,
                asset_kind=asset_kind,
                asset_key=candidate.asset_key,
            ),
        )
        for candidate in eligible
    ]
    scored.sort(
        key=lambda item: (
            -LIFECYCLE_STATE_RANK[item[0].lifecycle_state],
            -item[1].success_rate,
            -item[1].sample_size,
            item[0].asset_key,
        )
    )
    recommendations = [
        _recommendation_from_candidate(candidate, evidence, rank=index + 1)
        for index, (candidate, evidence) in enumerate(scored[:limit])
    ]
    if (
        recommendations
        and recommendations[0].evidence.sample_size < EXPLORATION_SAMPLE_SIZE_THRESHOLD
    ):
        if not any(item.lifecycle_state == "candidate" for item in recommendations):
            for candidate, evidence in scored[limit:]:
                if candidate.lifecycle_state == "candidate":
                    recommendations = recommendations[:-1] + [
                        _recommendation_from_candidate(
                            candidate,
                            evidence,
                            rank=len(recommendations),
                            exploration=True,
                        )
                    ]
                    break
        else:
            recommendations = [
                _recommendation_from_candidate(
                    item[0],
                    item[1],
                    rank=index + 1,
                    exploration=item[0].lifecycle_state == "candidate",
                )
                for index, item in enumerate(scored[:limit])
            ]
    return recommendations[:limit]


def recommend_skills_for_workflow_stage(
    conn: sqlite3.Connection,
    *,
    workflow_key: str,
    stage_key: str,
    limit: int = 3,
) -> list[AssetRecommendation]:
    from services.workflow_orchestration import load_workflow_registry

    workflow = load_workflow_registry()[workflow_key]
    stage = next(stage for stage in workflow.stages if stage.key == stage_key)
    return recommend_assets_for_packet(
        conn,
        task_classifications=(workflow.workflow_family, stage.kind),
        workflow_family=workflow.workflow_family,
        project_id=None,
        asset_kind="skill",
        limit=limit,
    )
