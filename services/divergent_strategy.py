from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, get_args

from services.asset_lifecycle import AssetKind, AssetLifecycleState

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_REGISTRY = ROOT / "config" / "divergent-strategy" / "candidates.json"
DEFAULT_JUDGE_REGISTRY = ROOT / "config" / "divergent-strategy" / "judges.json"

DivergentMode = Literal["lightweight", "standard", "gallery", "audit"]
PromotionStatus = AssetLifecycleState

MODE_PROFILES: dict[DivergentMode, dict[str, Any]] = {
    "lightweight": {
        "candidate_count": 3,
        "judges": ["operator", "skeptic"],
        "writeback_requires_approval": True,
    },
    "standard": {
        "candidate_count": 6,
        "judges": ["operator", "skeptic", "architect", "standards"],
        "writeback_requires_approval": True,
    },
    "gallery": {
        "candidate_count": 8,
        "judges": ["operator", "skeptic", "architect", "humanizer", "entropy"],
        "writeback_requires_approval": True,
    },
    "audit": {
        "candidate_count": 5,
        "judges": ["skeptic", "architect", "codesmell", "standards"],
        "writeback_requires_approval": True,
    },
}


def _normalize_lifecycle_status(status: str) -> AssetLifecycleState:
    if status not in get_args(AssetLifecycleState):
        raise ValueError(f"Unsupported lifecycle status: {status}")
    return status  # type: ignore[return-value]


PORTFOLIO_KEYS = (
    "best_overall",
    "most_immediately_useful",
    "highest_upside",
    "safest_implementation",
    "best_long_term_architecture",
    "most_interesting_failure",
    "should_not_implement",
    "rebranch_later",
)


@dataclass(frozen=True)
class CandidateProfile:
    key: str
    name: str
    role: str
    angle: str
    output_contract: tuple[str, ...]
    default_risks: tuple[str, ...]


@dataclass(frozen=True)
class JudgeProfile:
    key: str
    name: str
    role: str
    rubric: tuple[str, ...]


@dataclass(frozen=True)
class DivergentRun:
    id: str
    source_task: str
    mode: DivergentMode
    status: str
    task_classification: dict[str, Any]
    selected_workflow_profile: dict[str, Any]
    summary: str
    final_recommendation: str
    entropy_score: float
    quality_score: float


@dataclass(frozen=True)
class CandidateOutput:
    id: str
    name: str
    role: str
    formulation: str
    output: dict[str, Any]
    novelty_score: float
    usefulness_score: float
    feasibility_score: float
    risk_score: float


@dataclass(frozen=True)
class JudgmentOutput:
    id: str
    judge_name: str
    judge_role: str
    candidate_id: str
    score: float
    verdict: str
    critique: str
    recommended_action: str


@dataclass(frozen=True)
class EntropyObservation:
    repeated_pattern_detected: bool
    repeated_judges: bool
    repeated_candidate_shapes: bool
    novelty_score: float
    diversity_score: float
    recommendation: str


@dataclass(frozen=True)
class DivergentRunResult:
    run: DivergentRun
    candidates: list[CandidateOutput]
    judgments: list[JudgmentOutput]
    portfolio: dict[str, str | None]
    entropy_observation: EntropyObservation
    writeback_ids: list[str]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return loaded


def ensure_divergent_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS divergent_runs (
          id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          user_id TEXT,
          project_id TEXT,
          source_task TEXT NOT NULL,
          mode TEXT NOT NULL,
          status TEXT NOT NULL,
          task_classification TEXT NOT NULL DEFAULT '{}',
          selected_workflow_profile TEXT NOT NULL DEFAULT '{}',
          summary TEXT,
          final_recommendation TEXT,
          entropy_score REAL,
          quality_score REAL,
          cost_estimate REAL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS divergent_candidates (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES divergent_runs(id),
          candidate_name TEXT NOT NULL,
          candidate_role TEXT NOT NULL,
          formulation TEXT NOT NULL,
          output TEXT NOT NULL,
          strengths_json TEXT NOT NULL DEFAULT '[]',
          weaknesses_json TEXT NOT NULL DEFAULT '[]',
          novelty_score REAL NOT NULL,
          usefulness_score REAL NOT NULL,
          feasibility_score REAL NOT NULL,
          risk_score REAL NOT NULL,
          selected_status TEXT NOT NULL DEFAULT 'unselected',
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS divergent_judgments (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES divergent_runs(id),
          candidate_id TEXT REFERENCES divergent_candidates(id),
          judge_name TEXT NOT NULL,
          judge_role TEXT NOT NULL,
          rubric_used TEXT NOT NULL DEFAULT '[]',
          score REAL NOT NULL,
          verdict TEXT NOT NULL,
          critique TEXT NOT NULL,
          recommended_action TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS memory_writeback_proposals (
          id TEXT PRIMARY KEY,
          source_run_id TEXT NOT NULL REFERENCES divergent_runs(id),
          target_scope TEXT NOT NULL,
          proposal_type TEXT NOT NULL,
          proposed_content TEXT NOT NULL,
          rationale TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status TEXT NOT NULL DEFAULT 'proposed',
          created_at TEXT NOT NULL,
          reviewed_at TEXT,
          reviewed_by TEXT
        );

        CREATE TABLE IF NOT EXISTS entropy_observations (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL REFERENCES divergent_runs(id),
          repeated_pattern_detected INTEGER NOT NULL,
          repeated_judges INTEGER NOT NULL,
          repeated_candidate_shapes INTEGER NOT NULL,
          novelty_score REAL NOT NULL,
          diversity_score REAL NOT NULL,
          recommendation TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS promotion_lifecycle_items (
          id TEXT PRIMARY KEY,
          item_kind TEXT NOT NULL,
          item_key TEXT NOT NULL,
          source_run_id TEXT,
          status TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '[]',
          status_reason TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_divergent_runs_created
          ON divergent_runs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_divergent_candidates_run
          ON divergent_candidates(run_id);
        CREATE INDEX IF NOT EXISTS idx_divergent_judgments_run
          ON divergent_judgments(run_id);
        CREATE INDEX IF NOT EXISTS idx_memory_writeback_proposals_run
          ON memory_writeback_proposals(source_run_id);
        CREATE INDEX IF NOT EXISTS idx_entropy_observations_run
          ON entropy_observations(run_id);
        """
    )


def load_candidate_registry(path: Path | None = None) -> dict[str, CandidateProfile]:
    loaded = _load_json(path or DEFAULT_CANDIDATE_REGISTRY)
    rows = loaded.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("Candidate registry must contain a candidates list.")

    profiles: dict[str, CandidateProfile] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key", "")).strip()
        if not key:
            raise ValueError("Candidate key is required.")
        profiles[key] = CandidateProfile(
            key=key,
            name=str(row.get("name", key)),
            role=str(row.get("role", key)),
            angle=str(row.get("angle", "")),
            output_contract=tuple(
                str(item) for item in row.get("output_contract", []) if isinstance(item, str)
            ),
            default_risks=tuple(
                str(item) for item in row.get("default_risks", []) if isinstance(item, str)
            ),
        )
    return profiles


def load_judge_registry(path: Path | None = None) -> dict[str, JudgeProfile]:
    loaded = _load_json(path or DEFAULT_JUDGE_REGISTRY)
    rows = loaded.get("judges")
    if not isinstance(rows, list):
        raise ValueError("Judge registry must contain a judges list.")

    profiles: dict[str, JudgeProfile] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key", "")).strip()
        if not key:
            raise ValueError("Judge key is required.")
        profiles[key] = JudgeProfile(
            key=key,
            name=str(row.get("name", key)),
            role=str(row.get("role", key)),
            rubric=tuple(str(item) for item in row.get("rubric", []) if isinstance(item, str)),
        )
    return profiles


def classify_task(source_task: str) -> dict[str, Any]:
    normalized = source_task.lower()
    signals: list[str] = []
    if any(token in normalized for token in ("architecture", "design", "workflow", "strategy")):
        signals.append("architecture")
    if any(token in normalized for token in ("audit", "evaluate", "repo", "adoption")):
        signals.append("audit")
    if any(token in normalized for token in ("prompt", "skill", "standards", "memory")):
        signals.append("workflow_learning")
    if any(token in normalized for token in ("creative", "gallery", "explore", "novel")):
        signals.append("exploration")

    worthwhile = len(signals) > 0 or len(source_task.split()) >= 12
    if "exploration" in signals:
        mode: DivergentMode = "gallery"
    elif "audit" in signals and "architecture" not in signals:
        mode = "audit"
    elif worthwhile:
        mode = "standard"
    else:
        mode = "lightweight"

    return {
        "worthwhile": worthwhile,
        "recommended_mode": mode,
        "signals": signals,
        "reason": "Task has multiple plausible approaches."
        if worthwhile
        else "Task appears deterministic.",
    }


def _select_profiles(
    mode: DivergentMode, profiles: dict[str, CandidateProfile]
) -> list[CandidateProfile]:
    order = [
        "conservative_integrator",
        "skeptical_minimalist",
        "product_operator",
        "systems_architect",
        "workflow_designer",
        "researcher",
        "chaos_novelty",
        "standards_enforcer",
    ]
    if mode == "audit":
        order = [
            "researcher",
            "skeptical_minimalist",
            "systems_architect",
            "product_operator",
            "standards_enforcer",
        ]
    count = int(MODE_PROFILES[mode]["candidate_count"])
    return [profiles[key] for key in order if key in profiles][:count]


def _score_candidate(index: int, profile: CandidateProfile) -> tuple[float, float, float, float]:
    novelty = max(0.2, min(1.0, 0.35 + (index * 0.08)))
    usefulness = max(0.2, min(1.0, 0.82 - (index * 0.03)))
    feasibility = max(0.2, min(1.0, 0.88 - (index * 0.05)))
    risk = max(0.1, min(1.0, 0.22 + (index * 0.06)))
    if "Novelty" in profile.name:
        novelty = 0.94
        feasibility = 0.44
        risk = 0.72
    if "Standards" in profile.name:
        usefulness = 0.78
        feasibility = 0.76
        risk = 0.28
    return round(novelty, 2), round(usefulness, 2), round(feasibility, 2), round(risk, 2)


def _generate_candidate(source_task: str, profile: CandidateProfile, index: int) -> CandidateOutput:
    novelty, usefulness, feasibility, risk = _score_candidate(index, profile)
    proposal = {
        "name": profile.name,
        "angle": profile.angle,
        "proposal": f"Approach '{source_task}' through the {profile.name} angle.",
        "implementation_shape": (
            "Use existing AIOS workflow tables, explicit registries, approval-gated writebacks, "
            "and inspectable run artifacts before adding broader orchestration."
        ),
        "risks": list(profile.default_risks),
        "best_use_case": f"When {profile.angle.lower()} is the deciding factor.",
        "why_it_might_fail": profile.default_risks[0]
        if profile.default_risks
        else "The angle may not fit the task.",
        "memory_candidates": [
            {
                "category": "HOW",
                "content": f"Use {profile.name} when {profile.angle.lower()} matters.",
            }
        ],
    }
    return CandidateOutput(
        id=f"candidate-{uuid.uuid4()}",
        name=profile.name,
        role=profile.role,
        formulation=profile.angle,
        output=proposal,
        novelty_score=novelty,
        usefulness_score=usefulness,
        feasibility_score=feasibility,
        risk_score=risk,
    )


def _judge_candidate(
    candidate: CandidateOutput, judge: JudgeProfile, run_id: str
) -> JudgmentOutput:
    base = (
        candidate.usefulness_score + candidate.feasibility_score + (1 - candidate.risk_score)
    ) / 3
    if judge.key == "entropy":
        base = candidate.novelty_score
    elif judge.key in {"skeptic", "codesmell"}:
        base = (candidate.feasibility_score + (1 - candidate.risk_score)) / 2
    elif judge.key == "architect":
        base = (candidate.usefulness_score + candidate.feasibility_score) / 2
    score = round(max(0.0, min(1.0, base)), 2)
    verdict = "adopt" if score >= 0.72 else "hold" if score >= 0.55 else "reject"
    return JudgmentOutput(
        id=f"judgment-{uuid.uuid4()}",
        judge_name=judge.name,
        judge_role=judge.role,
        candidate_id=candidate.id,
        score=score,
        verdict=verdict,
        critique=(
            f"{judge.name} scored {candidate.name} at {score:.2f} using "
            f"{', '.join(judge.rubric[:3])}."
        ),
        recommended_action="Include in portfolio."
        if verdict == "adopt"
        else "Preserve as caveat or failure.",
    )


def score_entropy(candidate_shapes: list[str], judge_roles: list[str]) -> EntropyObservation:
    unique_shapes = len({shape.strip().lower() for shape in candidate_shapes if shape.strip()})
    unique_judges = len({role.strip().lower() for role in judge_roles if role.strip()})
    shape_count = max(1, len(candidate_shapes))
    judge_count = max(1, len(judge_roles))
    diversity_score = round(unique_shapes / shape_count, 2)
    novelty_score = round(
        min(1.0, (diversity_score + min(1.0, unique_judges / judge_count)) / 2), 2
    )
    repeated_shapes = unique_shapes < shape_count
    repeated_judges = unique_judges < judge_count
    repeated = repeated_shapes or repeated_judges or diversity_score < 0.5
    recommendation = (
        "Rotate candidate shapes or judge roles before promotion."
        if repeated
        else "Diversity is sufficient for this run; preserve selected failures for future contrast."
    )
    return EntropyObservation(
        repeated_pattern_detected=repeated,
        repeated_judges=repeated_judges,
        repeated_candidate_shapes=repeated_shapes,
        novelty_score=novelty_score,
        diversity_score=diversity_score,
        recommendation=recommendation,
    )


def _select_portfolio(
    candidates: list[CandidateOutput],
    judgments: list[JudgmentOutput],
) -> dict[str, str | None]:
    score_by_candidate: dict[str, float] = {}
    for candidate in candidates:
        candidate_judgments = [
            judgment.score for judgment in judgments if judgment.candidate_id == candidate.id
        ]
        average_judgment = (
            sum(candidate_judgments) / len(candidate_judgments) if candidate_judgments else 0.0
        )
        score_by_candidate[candidate.id] = round(
            (
                candidate.usefulness_score
                + candidate.feasibility_score
                + average_judgment
                - candidate.risk_score
            )
            / 3,
            3,
        )

    def best_by(key: str) -> str | None:
        if not candidates:
            return None
        if key == "overall":
            return max(candidates, key=lambda item: score_by_candidate[item.id]).id
        if key == "useful":
            return max(candidates, key=lambda item: item.usefulness_score).id
        if key == "upside":
            return max(candidates, key=lambda item: item.novelty_score).id
        if key == "safe":
            return min(candidates, key=lambda item: item.risk_score).id
        if key == "architecture":
            return max(
                candidates, key=lambda item: item.feasibility_score + item.usefulness_score
            ).id
        if key == "failure":
            return max(candidates, key=lambda item: item.novelty_score + item.risk_score).id
        if key == "reject":
            return min(candidates, key=lambda item: score_by_candidate[item.id]).id
        return candidates[-1].id

    return {
        "best_overall": best_by("overall"),
        "most_immediately_useful": best_by("useful"),
        "highest_upside": best_by("upside"),
        "safest_implementation": best_by("safe"),
        "best_long_term_architecture": best_by("architecture"),
        "most_interesting_failure": best_by("failure"),
        "should_not_implement": best_by("reject"),
        "rebranch_later": best_by("later"),
    }


def _insert_writebacks(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    source_task: str,
    portfolio: dict[str, str | None],
    entropy: EntropyObservation,
) -> list[str]:
    created_at = _now_iso()
    proposals = [
        {
            "target_scope": "prompt_library",
            "proposal_type": "HOW",
            "proposed_content": (
                "# HOW Memory\n"
                "Use divergent strategy when tasks have multiple plausible approaches, explicit tradeoffs, "
                "or prompt/skill promotion risk."
            ),
            "rationale": "Reusable process preference extracted from a divergent strategy run.",
        },
        {
            "target_scope": "project",
            "proposal_type": "WHAT",
            "proposed_content": (
                "# WHAT Memory\n"
                f"AIOS evaluated this task with a portfolio output instead of a single winner: {source_task}"
            ),
            "rationale": "Project-specific fact about the workflow decision and selected portfolio.",
        },
        {
            "target_scope": "project",
            "proposal_type": "FAILURE",
            "proposed_content": (
                "# FAILURE Memory\n"
                f"Most interesting failure candidate: {portfolio.get('most_interesting_failure')}. "
                "Preserve it as contrast before future promotion."
            ),
            "rationale": "Useful failures should remain inspectable rather than disappear from the final answer.",
        },
        {
            "target_scope": "standards",
            "proposal_type": "ENTROPY",
            "proposed_content": (
                "# ENTROPY Memory\n"
                f"Diversity score: {entropy.diversity_score}. Recommendation: {entropy.recommendation}"
            ),
            "rationale": "Convergence risk affects standards and prompt-library promotion.",
        },
        {
            "target_scope": "skill_registry",
            "proposal_type": "HOW",
            "proposed_content": (
                "# Skill Candidate\n"
                "Promote divergent-strategy only after repeated successful use, tests, and user approval."
            ),
            "rationale": "Lifecycle gate prevents one successful run from becoming active policy.",
        },
    ]
    ids: list[str] = []
    for proposal in proposals:
        proposal_id = f"writeback-{uuid.uuid4()}"
        conn.execute(
            """
            INSERT INTO memory_writeback_proposals (
              id, source_run_id, target_scope, proposal_type, proposed_content,
              rationale, evidence_json, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'proposed', ?)
            """,
            (
                proposal_id,
                run_id,
                proposal["target_scope"],
                proposal["proposal_type"],
                proposal["proposed_content"],
                proposal["rationale"],
                _json_dump([source_task, portfolio]),
                created_at,
            ),
        )
        ids.append(proposal_id)
    return ids


def transition_promotion_lifecycle(
    conn: sqlite3.Connection,
    *,
    item_id: str,
    item_kind: str,
    item_key: str,
    requested_status: PromotionStatus,
    source_run_id: str | None,
    evidence: list[str],
) -> dict[str, Any]:
    ensure_divergent_schema(conn)
    existing = conn.execute(
        "SELECT status FROM promotion_lifecycle_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    previous = str(existing["status"]) if existing else "draft"
    status = requested_status
    status_reason = "Lifecycle transition accepted."
    if requested_status in {"approved", "active"} and not evidence:
        status = previous  # type: ignore[assignment]
        status_reason = f"Promotion to {requested_status} requires evidence."
    normalized_status = _normalize_lifecycle_status(status)

    timestamp = _now_iso()
    conn.execute(
        """
        INSERT INTO promotion_lifecycle_items (
          id, item_kind, item_key, source_run_id, status, evidence_json,
          status_reason, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          status = excluded.status,
          evidence_json = excluded.evidence_json,
          status_reason = excluded.status_reason,
          source_run_id = excluded.source_run_id,
          updated_at = excluded.updated_at
        """,
        (
            item_id,
            item_kind,
            item_key,
            source_run_id,
            normalized_status,
            _json_dump(evidence),
            status_reason,
            timestamp,
            timestamp,
        ),
    )
    row = conn.execute(
        "SELECT id, status, status_reason FROM promotion_lifecycle_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    return dict(row)


def _propose_via_workflow_promotion_if_available(
    conn: sqlite3.Connection,
    *,
    asset_kind: str,
    asset_key: str,
    to_state: AssetLifecycleState,
    evidence: dict[str, Any],
    actor: str,
    rationale: str,
) -> dict[str, Any] | None:
    try:
        from services.workflow_promotion import (
            propose_asset_promotion,
            propose_workflow_promotion,
        )
    except ImportError:
        print(
            "[warn] Phase 8 workflow_promotion absent; falling back to "
            "transition_promotion_lifecycle direct write. Promotion governance "
            "is loose for this run; Phase 10 will tighten once Phase 8 ships.",
            file=sys.stderr,
        )
        return None
    if asset_kind == "workflow":
        from services.workflow_promotion import WorkflowEffectiveness

        workflow_evidence = WorkflowEffectiveness(
            workflow_key=asset_key,
            since=str(evidence.get("since", "")),
            run_count=int(evidence.get("run_count", 1)),
            completed_count=int(evidence.get("completed_count", 1)),
            failed_count=int(evidence.get("failed_count", 0)),
            rework_rate=float(evidence.get("rework_rate", 0.0)),
            validation_pass_rate=float(evidence.get("validation_pass_rate", 1.0)),
            mean_blocker_count=float(evidence.get("mean_blocker_count", 0.0)),
            mean_blockers_per_stage=float(evidence.get("mean_blockers_per_stage", 0.0)),
            writeback_usefulness=float(evidence.get("writeback_usefulness", 0.0)),
            stage_evaluations={},
        )
        return propose_workflow_promotion(
            conn,
            workflow_key=asset_key,
            to_state=to_state,
            evidence=workflow_evidence,
            actor=actor,
            rationale=rationale,
        )
    if asset_kind not in {"prompt", "skill"}:
        raise ValueError(f"Unsupported divergent promotion asset kind: {asset_kind}")
    typed_asset_kind: AssetKind = "prompt" if asset_kind == "prompt" else "skill"
    return propose_asset_promotion(
        conn,
        asset_kind=typed_asset_kind,
        asset_key=asset_key,
        to_state=to_state,
        evidence=evidence,
        actor=actor,
        rationale=rationale,
    )


def create_divergent_run(
    conn: sqlite3.Connection,
    *,
    source_task: str,
    mode: DivergentMode | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
) -> DivergentRunResult:
    ensure_divergent_schema(conn)
    classification = classify_task(source_task)
    selected_mode = mode or classification["recommended_mode"]
    profile = MODE_PROFILES[selected_mode]
    run_id = f"divergent-run-{uuid.uuid4()}"
    timestamp = _now_iso()

    candidate_profiles = _select_profiles(selected_mode, load_candidate_registry())
    judge_profiles = load_judge_registry()
    selected_judges = [judge_profiles[key] for key in profile["judges"] if key in judge_profiles]
    candidates = [
        _generate_candidate(source_task, candidate_profile, index)
        for index, candidate_profile in enumerate(candidate_profiles)
    ]
    judgments = [
        _judge_candidate(candidate, judge, run_id)
        for candidate in candidates
        for judge in selected_judges
    ]
    portfolio = _select_portfolio(candidates, judgments)
    entropy = score_entropy(
        candidate_shapes=[candidate.formulation for candidate in candidates],
        judge_roles=[judge.key for judge in selected_judges],
    )
    quality_score = round(sum(judgment.score for judgment in judgments) / max(1, len(judgments)), 2)
    final_recommendation = (
        "Use the best-overall candidate as the implementation anchor, include the safest candidate "
        "as the delivery path, and preserve the highest-risk novelty candidate as a rebranch option."
    )
    summary = (
        f"Divergent strategy run produced {len(candidates)} candidates, {len(judgments)} judgments, "
        "and an approval-gated memory portfolio."
    )

    conn.execute(
        """
        INSERT INTO divergent_runs (
          id, created_at, updated_at, user_id, project_id, source_task, mode, status,
          task_classification, selected_workflow_profile, summary, final_recommendation,
          entropy_score, quality_score, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            timestamp,
            timestamp,
            user_id,
            project_id,
            source_task,
            selected_mode,
            _json_dump(classification),
            _json_dump(profile),
            summary,
            final_recommendation,
            entropy.diversity_score,
            quality_score,
            _json_dump(
                {
                    "portfolio": portfolio,
                    "status_explanation": "Completed means portfolio output exists.",
                }
            ),
        ),
    )
    for candidate in candidates:
        selected_status = next(
            (key for key, candidate_id in portfolio.items() if candidate_id == candidate.id),
            "unselected",
        )
        conn.execute(
            """
            INSERT INTO divergent_candidates (
              id, run_id, candidate_name, candidate_role, formulation, output,
              strengths_json, weaknesses_json, novelty_score, usefulness_score,
              feasibility_score, risk_score, selected_status, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate.id,
                run_id,
                candidate.name,
                candidate.role,
                candidate.formulation,
                _json_dump(candidate.output),
                _json_dump([candidate.output["best_use_case"]]),
                _json_dump(candidate.output["risks"]),
                candidate.novelty_score,
                candidate.usefulness_score,
                candidate.feasibility_score,
                candidate.risk_score,
                selected_status,
                _json_dump(
                    {
                        "score_formula": "heuristic: novelty/usefulness/feasibility/risk registry defaults"
                    }
                ),
            ),
        )
    for judgment in judgments:
        judge = next(item for item in selected_judges if item.name == judgment.judge_name)
        conn.execute(
            """
            INSERT INTO divergent_judgments (
              id, run_id, candidate_id, judge_name, judge_role, rubric_used,
              score, verdict, critique, recommended_action, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                judgment.id,
                run_id,
                judgment.candidate_id,
                judgment.judge_name,
                judgment.judge_role,
                _json_dump(judge.rubric),
                judgment.score,
                judgment.verdict,
                judgment.critique,
                judgment.recommended_action,
                _json_dump({"score_type": "heuristic"}),
            ),
        )
    conn.execute(
        """
        INSERT INTO entropy_observations (
          id, run_id, repeated_pattern_detected, repeated_judges, repeated_candidate_shapes,
          novelty_score, diversity_score, recommendation, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"entropy-{uuid.uuid4()}",
            run_id,
            1 if entropy.repeated_pattern_detected else 0,
            1 if entropy.repeated_judges else 0,
            1 if entropy.repeated_candidate_shapes else 0,
            entropy.novelty_score,
            entropy.diversity_score,
            entropy.recommendation,
            _json_dump(
                {"formula": "unique candidate shapes / total shapes plus judge-role diversity"}
            ),
        ),
    )
    writeback_ids = _insert_writebacks(
        conn,
        run_id=run_id,
        source_task=source_task,
        portfolio=portfolio,
        entropy=entropy,
    )
    promotion_result = _propose_via_workflow_promotion_if_available(
        conn,
        asset_kind="skill",
        asset_key="divergent-strategy",
        to_state="candidate",
        evidence={
            "source": "divergent_strategy",
            "divergent_run_id": run_id,
            "portfolio": portfolio,
            "quality_score": quality_score,
            "entropy_score": entropy.diversity_score,
        },
        actor="divergent_strategy",
        rationale="Portfolio winner with judge consensus",
    )
    if promotion_result is None:
        transition_promotion_lifecycle(
            conn,
            item_id="skill-divergent-strategy",
            item_kind="skill",
            item_key="divergent-strategy",
            requested_status="candidate",
            source_run_id=run_id,
            evidence=[],
        )
    conn.commit()

    run = DivergentRun(
        id=run_id,
        source_task=source_task,
        mode=selected_mode,
        status="completed",
        task_classification=classification,
        selected_workflow_profile=profile,
        summary=summary,
        final_recommendation=final_recommendation,
        entropy_score=entropy.diversity_score,
        quality_score=quality_score,
    )
    return DivergentRunResult(
        run=run,
        candidates=candidates,
        judgments=judgments,
        portfolio=portfolio,
        entropy_observation=entropy,
        writeback_ids=writeback_ids,
    )


def approve_memory_writeback(
    conn: sqlite3.Connection,
    proposal_id: str,
    *,
    reviewed_by: str,
) -> dict[str, Any]:
    ensure_divergent_schema(conn)
    reviewed_at = _now_iso()
    conn.execute(
        """
        UPDATE memory_writeback_proposals
        SET status = 'approved', reviewed_at = ?, reviewed_by = ?
        WHERE id = ?
        """,
        (reviewed_at, reviewed_by, proposal_id),
    )
    conn.commit()
    row = conn.execute(
        """
        SELECT id, source_run_id, target_scope, proposal_type, status, reviewed_by
        FROM memory_writeback_proposals
        WHERE id = ?
        """,
        (proposal_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown writeback proposal: {proposal_id}")
    return dict(row)
