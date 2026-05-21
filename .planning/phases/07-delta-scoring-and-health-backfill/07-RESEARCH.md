---
phase: 07-delta-scoring-and-health-backfill
phase_number: "07"
type: research
updated: 2026-05-20
---

# Phase 7 Research

**Researched:** 2026-05-20
**Domain:** Delta scoring, project-health explanation, capability-truth signal classes, remediation prioritization, workflow recommendation from health state
**Confidence:** HIGH

## Summary

Phase 7 turns the evaluation evidence and standards machinery already in place into **explainable** per-domain health scoring with concrete evidence, confidence, freshness, and remediation per signal — and into a **prioritized backfill path** that nominates the right workflow to run next. The structural primitives are mostly already there: `services/standards_health.py` already emits per-domain weighted scores, delta items with `priority_score`/`priority_bucket`, regression flags, blocker dependencies, and per-snapshot backfill tasks; `services/capability_truth.py` already classifies signals as `confirmed | inferred | missing | contradictory` via the `TrustedSignal` dataclass; `aios-ui/server/aios/standards-health.ts` already projects these into the operator surface; `services/quality_pipeline.py` already tracks per-gate runs; Phase 5 already shipped writeback approval policy classes that Phase 7 will reuse for backfill plans; Phase 6 just shipped `success_criteria_stage_findings` so per-domain scoring can now ingest stage-level evidence rather than only run-level evaluations.

The remaining work is largely **wiring and surfacing**, with two notable extensions: (1) DELT-01 names **ten** quality dimensions but `config/standards/registry.json` only covers seven distinct domains today — `maintainability` (lives under `code_quality`), `UX`, `launch_readiness`, `agent_readiness`, and an explicit `standards_compliance` rollup are missing or named differently; (2) the current `EvaluatedStandard.confidence` plus `last_evaluated_at` carry the building blocks for explainability but the **explainability contract** is not yet exposed as a typed payload — the UI consumes per-snapshot domain scores but not per-standard "evidence, confidence, freshness, contradiction, remediation" rows in a canonical form. Workflow recommendation from health state is also new — `recommend_route_primitives` in `services/workflow_orchestration.py` ranks workflows from an objective string, but nothing currently feeds the backfill-task list or critical-delta count back into that recommender so query and operator surfaces can suggest `standards backfill` / `audit-only` / `codebase architecture review` based on health.

**Primary recommendation:** Treat Phase 7 as three additive layers on top of Phase 6 evidence: **(a) Domain coverage** — register the five missing DELT-01 domains in `config/standards/registry.json` with at least one evaluator each, even if some start as `unknown` with explicit `missing_reason`; **(b) Explainable delta contract** — emit a typed `DeltaExplanation { evidence[], confidence, freshness, contradiction?, remediation }` shape per assessment, persisted in `standards_assessments` (already has the columns) and projected through a new `getProjectDeltaExplanations()` server function next to `getProjectStandardsHealth`; **(c) Workflow-from-health recommender** — add `recommend_workflow_from_health(project_id)` that maps `priority_bucket` × `domain` → workflow_key (e.g., `blocked` → `failure-recovery`, foundational standards gaps → `standards backfill`, security domain blocker → `security review`, architecture domain critical → `codebase architecture review`), and surface the recommendation in `aios-ui/server/routers/insights.ts` and `aios-ui/server/routers/projects.ts`. The `standards_backfill_tasks` table already has `priority_score`/`priority_bucket`/`expected_health_impact`; Phase 7's job is to make the recommendation actionable and the explanation drill-downable, not to invent new persistence.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-domain alignment scoring (DELT-01) | Python control plane (`services/standards_health.py`) | Config (`config/standards/registry.json`) | Already computes `domain_scores_json`; adding the missing DELT-01 domains is a registry extension + evaluator wiring, not a new module. |
| Explainable delta contract (DELT-02) | Python control plane (`services/standards_health.py` evaluators, `services/capability_truth.py`) | SQLite (`standards_assessments` columns already present) | Evidence/confidence/freshness columns already exist on `standards_assessments`; Phase 7 adds a canonical projection + typed UI contract. |
| Signal-state classification (DELT-03) | Python control plane (`services/capability_truth.py:TrustedSignal`) | UI (`aios-ui/lib/trusted-signals.ts`) | `TrustedSignal` and `Provenance` literal already enforce the four-state contract; Phase 7 propagates the same contract through health views, not invents a new one. |
| Prioritized backfill path (DELT-04) | Python control plane (`services/standards_health.py:_build_delta_items` + `_build_task_rows`) | SQLite (`standards_delta_items`, `standards_backfill_tasks`) | Priority scoring (severity × leverage × dependency_unlock × regression_penalty / effort) and bucketing already exist; Phase 7 adds (a) cross-project ranking and (b) workflow recommendation derived from buckets. |
| Workflow recommendation from health | Python control plane (new `services/health_workflow_recommender.py` or extension of `services/workflow_orchestration.py`) | UI router (`aios-ui/server/routers/projects.ts`, `insights.ts`, `query.ts`) | Workflow selection currently keys off objective text only; Phase 7 introduces health-state as a second input. |
| Operator-visible delta surface | UI (`aios-ui/server/aios/standards-health.ts`, `aios-ui/server/routers/projects.ts`) | UI (`aios-ui/server/routers/insights.ts`) | `getProjectStandardsHealth` already returns delta items + backfill tasks; Phase 7 extends it with `deltaExplanations[]` and `recommendedWorkflows[]`. |
| Audit-only and architecture-review workflow deltas | Config (`config/workflows/registry.json`) + Python (`services/workflow_orchestration.py`) | Per-stage evaluation hook from Phase 6 | `audit-only` and `codebase architecture review` are still planned-not-registered; Phase 7 must define their **delta-emission shape** even if their full stage contracts wait for Phase 8. |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DELT-01 | Score project alignment across **ten** quality dimensions: architecture, testing, maintainability, security, UX, observability, documentation, launch readiness, agent-readiness, standards compliance | Existing `standards_health.py` already emits per-domain weighted scores from `config/standards/registry.json`. Current registry covers 7 of 10 named domains. Five gaps: `maintainability` (currently bucketed under `code_quality`), `UX`, `launch_readiness`, `agent_readiness`, and a rolled-up `standards_compliance` view. Phase 7 must extend the registry and add evaluators for these (some can start as `unknown` with `missing_reason`). |
| DELT-02 | Every score shows concrete evidence, confidence, freshness, contradiction, and remediation | `standards_assessments` already persists `evidence_json`, `confidence`, `last_evaluated_at`, `regression_flag`, `measured_state_json`, and `reason`. Remediation lives in `standards_delta_items.remediation_playbook_json`. Phase 7 needs to project these as one typed `DeltaExplanation` payload and expose it through the UI router so each domain score drills down to per-standard rows. |
| DELT-03 | Health views distinguish confirmed, inferred, missing, contradictory signals | `services/capability_truth.py:TrustedSignal` + `Provenance = Literal["confirmed", "inferred", "missing", "contradictory"]` already enforces this. `aios-ui/lib/trusted-signals.ts` mirrors it. Phase 7 propagates it through delta views (today they collapse to a single `status` enum: pass/partial/fail/unknown/waived/not_applicable — Phase 7 must add the four-state provenance overlay so "fail with high confidence" ≠ "unknown because missing evidence" ≠ "contradictory between sources"). |
| DELT-04 | Recommend a prioritized backfill path for biggest gaps + workflow recommendation from health state | `standards_delta_items.priority_score`/`priority_bucket` + `standards_backfill_tasks` already encode prioritization. Phase 7 adds (a) cross-domain ranking that respects `blocking_dependencies` so foundational deltas surface first, (b) `recommend_workflow_from_health()` that maps bucket+domain → workflow_key, and (c) the recommendation surfaces in operator-visible routers and grounded query answers. |

## Project Constraints (from CLAUDE.md / AGENTS.md)

| Constraint | Source | Phase 7 Implication |
|------------|--------|---------------------|
| Run quality ladder: `ruff check . && ruff format --check . && basedpyright && vulture` | `~/.claude/CLAUDE.md` Python canonical commands | Every implementation task in this phase ends with these checks; treat as hard gate. |
| UI quality ladder: `pnpm lint && pnpm tsc --noEmit` (no `pnpm test` is wired in `aios-ui/package.json`) | `~/.claude/CLAUDE.md` + AGENTS.md | Any TypeScript edit in `aios-ui/server/aios/` or `aios-ui/server/routers/` ends with these. |
| Atomic commits scoped to one project + one concern, followed by immediate `PROJECT.md` truth update commit | `~/.claude/CLAUDE.md` Git + AGENTS.md | Each task in this phase commits independently and updates `PROJECT.md` before the next task begins. |
| `main` stays deployable | `~/.claude/CLAUDE.md` Git | Phase 7 work goes through feature branches per `.planning/config.json` `branching_strategy: none` setting → confirm with user whether the autonomous mode bypasses branching here. |
| No `--no-verify` or `--no-gpg-sign` bypasses | `~/.claude/CLAUDE.md` Git | Honor pre-commit hooks. |
| Never use `cat << EOF` or heredoc for file creation | Agent harness rule | Use Write tool for any new file. |
| Don't add comments/docstrings/type annotations to code I didn't change | `~/.claude/CLAUDE.md` Working style | Edits stay scoped; do not blanket-annotate touched modules. |
| Three similar lines is better than premature abstraction | `~/.claude/CLAUDE.md` Working style | Resist the temptation to invent a generic `Scorer` framework; extend the per-standard evaluator dispatch pattern that Phase 6 already follows. |
| Local-first + files-authoritative | AGENTS.md (Constraints) | All new scoring data must live in SQLite + registry JSON, not in external services. |
| Governance must remain reviewable | AGENTS.md (Constraints) | Workflow recommendations are advisory; promotion of backfill tasks into actual runs must reuse Phase 5 approval policy classes when impact_scope is `standards-default` or `workflow-default`. |
| Explainability is required | AGENTS.md (Constraints) | Every Phase 7 score MUST carry an explanation contract; UI surfaces MUST drill down to sources. This is also enforced by `TIER_ONE_ACCEPTANCE_CHECKLIST.md` Phase 7 failure conditions ("No score may appear without a drill-down path"). |

## Standard Stack

### Core (existing — extend, don't replace)

| Library / Surface | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| `services/standards_health.py` | in-tree (1599 lines) | Registry load, per-domain scoring, delta items, backfill tasks, regression flags, dependency unlock | Already the canonical scoring entry point; consumed by hook-stop, aios-ui, and CLI `governance-audit`. Phase 7 extends evaluators and adds explanation projection. |
| `services/capability_truth.py` | in-tree (617 lines) | `TrustedSignal` four-state contract, per-surface signals (projects, RTK, automations, prompt library, knowledge) | Already the canonical provenance contract; Phase 7 propagates it through delta views. |
| `services/workflow_orchestration.py` | in-tree | `rank_workflow_candidates`, `recommend_route_primitives`, `WORKFLOW_TASK_FAMILIES` | Already the workflow recommender — extend to accept health state as input. |
| `services/quality_pipeline.py` | in-tree (388 lines) | Per-gate (`lint`, `typecheck`, `test`, `build`, `architecture`, `ci`) run tracking, applicability inference, latest-run state | Phase 7 reads quality_pipeline runs as evidence for `code_quality.lint_ratchet`-style standards but should NOT modify gate inference. |
| `config/standards/registry.json` | 2026.05.0 | Declarative standards profile (`aios-core`) with weights, applicability, blocking_dependencies, waiver policy, related_criteria | Phase 7 adds new standards for the missing DELT-01 domains and bumps `profile.version` to `2026.05.1` or `2026.06.0`. |
| `services/aios_cli.py` | in-tree | `capability-audit`, `governance-audit`, `contracts-audit`, `prove-project-health` CLI commands | Phase 7 adds a `delta-explain` CLI subcommand and extends `governance-audit` with workflow recommendations. |
| `aios-ui/server/aios/standards-health.ts` | in-tree (323 lines) | `getProjectStandardsHealth(db, projectId)`, `updateStandardsBackfillTask(db, input)` | Phase 7 adds `getProjectDeltaExplanations()` and `getRecommendedWorkflowsFromHealth()` sibling functions. |
| `aios-ui/lib/trusted-signals.ts` | in-tree | TypeScript mirror of `TrustedSignal` + `Provenance` | Phase 7 reuses; do not redefine. |

### Supporting (no new external deps required)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlite3` (stdlib) | 3.x | All persistence follows the `ensure_*_schema` + `INSERT ... ON CONFLICT` pattern | New standards definitions are loaded via existing `seed_registry`; no new schema needed unless a `health_workflow_recommendations` cache is added. |
| `json` (stdlib) | — | Registry parsing and JSON-column persistence | Reuse existing `_load_json` + `_json` helpers. |
| `dataclasses` (stdlib) | — | Frozen dataclasses for new explanation payloads | Follow `StandardDefinition` / `TrustedSignal` shape. |
| `pytest` 8.x | — | Test framework | Follow `tests/test_standards_health.py` in-memory sqlite pattern. |
| `better-sqlite3` (UI) | per `aios-ui/package.json` | Direct DB access in `aios-ui/server/db.ts` | Reuse — Phase 7 adds prepared statements next to `getProjectStandardsHealth`. |
| `zod` | per `aios-ui/package.json` | Runtime validation in tRPC routers | New `recommend-workflow-from-health` input/output schemas use `z.object(...)`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending `services/standards_health.py` evaluators in place | New `services/health_explainer.py` module | Splitting risks duplicating registry-load + evaluation-status mapping. Keep the per-standard evaluator dispatch in `_evaluate_known_standard` and add `_build_explanation()` next to `_build_delta_items()`. |
| Adding new SQLite tables for explanations | Project explanations on-the-fly from existing `standards_assessments` columns | The columns are already there (`evidence_json`, `confidence`, `last_evaluated_at`, `regression_flag`, `reason`, `measured_state_json`). A new table would just denormalize the same data. **Choose on-the-fly projection.** |
| New `health_workflow_recommendations` cache table | Compute recommendations at read time in `aios-ui/server/aios/standards-health.ts` | Health snapshots are recomputed on session close so recommendations don't change often; recompute at read time is cheaper than maintaining a denormalized cache. **Choose read-time projection.** |
| Adding `maintainability`/`UX`/`launch_readiness`/`agent_readiness`/`standards_compliance` as fresh evaluators with full automation | Add the standards with `evaluator_type: "manual"` and `unknown` default status, with explicit `missing_reason` and required `manual_assessment_override` to flip status | Honest reporting per CLAUDE.md philosophy: surface "unknown because no auto evaluator exists yet" rather than fake-passing scores. Manual overrides hit the existing `ManualAssessmentOverride` TypedDict. **Choose unknown-with-rationale + override path.** |
| Inventing a new four-state `provenance` enum on `EvaluatedStandard` | Reuse `Provenance = Literal["confirmed", "inferred", "missing", "contradictory"]` from `capability_truth.py` | Two parallel enums diverge over time. **Reuse the existing one** — import `Provenance` from `services.capability_truth` (or move to a shared `services/signal_provenance.py` if circular import becomes a concern). |
| Hardcoded bucket→workflow mapping in code | Declarative mapping in `config/workflows/health-recommendations.json` | Hardcoding three similar lines is better than premature abstraction (CLAUDE.md). Start hardcoded in `services/workflow_orchestration.py`; promote to config only if the mapping grows beyond ~8 rules. |

**Installation:** No new dependencies. Phase 7 is entirely additive to existing in-tree modules.

**Version verification:** `config/standards/registry.json` is at `profile.version = 2026.05.0` and Phase 7 will bump to `2026.06.0` when registering the five missing domains. No external package version checks required.

## Architecture Patterns

### System Architecture Diagram

```
                  ┌──────────────────────────────────────────────────────┐
                  │ config/standards/registry.json                       │
                  │  (extend: + maintainability, UX, launch_readiness,   │
                  │           agent_readiness, standards_compliance)     │
                  └─────────────────┬────────────────────────────────────┘
                                    │ seed_registry()
                                    ▼
   ┌──────────────────────────┐     ┌──────────────────────────────────┐
   │ standards_definitions    │     │ standards_assessments (existing) │
   │ (existing)               │     │  evidence_json, confidence,      │
   └──────────────────────────┘     │  last_evaluated_at, reason,      │
                                    │  measured_state_json,            │
                                    │  regression_flag                 │
                                    └─────────────┬────────────────────┘
                                                  │ read at snapshot time
                                                  ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ services/standards_health.py: evaluate_and_record()                │
   │   evaluations[]                                                    │
   │     ↓                                                              │
   │   _compute_score()  ────→  domain_scores_json (existing)           │
   │     ↓                                                              │
   │   _build_delta_items()  ──→  standards_delta_items + priority_*    │
   │     ↓                                                              │
   │   _build_task_rows()  ────→  standards_backfill_tasks              │
   │     ↓                                                              │
   │   NEW: _build_explanations(evaluations, capability_truth_signals)  │
   │     │   per standard:                                              │
   │     │     - evidence[]   ←─ standards_assessments.evidence_json    │
   │     │     - confidence   ←─ standards_assessments.confidence       │
   │     │     - freshness    ←─ standards_assessments.last_evaluated_at│
   │     │     - provenance   ←─ TrustedSignal classification           │
   │     │     - contradiction←─ cross-source check (see Pattern 3)     │
   │     │     - remediation  ←─ standards_delta_items.remediation_*    │
   │     │                                                              │
   │   NEW: recommend_workflow_from_health(project_id)                  │
   │     │   inputs: priority_bucket × domain × blocked? × foundational?│
   │     │   outputs: [{workflow_key, rationale, confidence}]           │
   │     ▼                                                              │
   └────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ projected into UI via
                                    ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ aios-ui/server/aios/standards-health.ts                            │
   │   getProjectStandardsHealth(db, projectId)  (extended)             │
   │     - existing: snapshot, deltaItems, backfillTasks, migration     │
   │     - NEW: deltaExplanations[]                                     │
   │     - NEW: recommendedWorkflows[]                                  │
   │                                                                    │
   │   NEW: getProjectDeltaExplanations(db, projectId)                  │
   │   NEW: getRecommendedWorkflowsFromHealth(db, projectId)            │
   └─────────────┬──────────────────────────────────────────────────────┘
                 │
                 ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │ tRPC routers (existing, extended):                                 │
   │   projects.getOverview / projects.getProject / projects.byId       │
   │   insights.* (health drill-down)                                   │
   │   query.* (workflow recommendations in grounded query)             │
   └────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ also reachable via CLI
                                    │
   ┌────────────────────────────────┴───────────────────────────────────┐
   │ aios CLI (services/aios_cli.py):                                    │
   │   aios capability-audit                                             │
   │   aios prove-project-health  (existing)                             │
   │   NEW: aios delta-explain --project X                               │
   │   NEW: aios recommend-workflow --project X                          │
   │   aios governance-audit  (extended: includes workflow recs)         │
   └────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (additions)

```
services/
├── standards_health.py          # extend: _build_explanations(),
│                                #          recommend_workflow_from_health(),
│                                #          register new domain evaluators
├── capability_truth.py          # extend: expose Provenance enum publicly
│                                #          add contradiction detection helper
├── workflow_orchestration.py    # extend: accept health_state in recommender
└── aios_cli.py                  # extend: delta-explain + recommend-workflow

config/
└── standards/
    └── registry.json            # extend: + 5 new standards covering
                                 #           maintainability, UX,
                                 #           launch_readiness,
                                 #           agent_readiness,
                                 #           standards_compliance
                                 # bump profile.version to 2026.06.0

aios-ui/
├── server/
│   ├── aios/
│   │   └── standards-health.ts  # extend: getProjectDeltaExplanations(),
│   │                            #          getRecommendedWorkflowsFromHealth()
│   └── routers/
│       ├── projects.ts          # extend: include explanations + recs
│       ├── insights.ts          # extend: surface workflow recommendations
│       └── query.ts             # extend: workflow recs in grounded query
└── lib/
    ├── control-plane.ts         # extend: DeltaExplanation type,
    │                            #          RecommendedWorkflow type
    └── trusted-signals.ts       # already correct — reuse

tests/
├── test_standards_health.py     # extend: explanation projection,
│                                #          recommend_workflow_from_health,
│                                #          new domain evaluators
└── test_aios_cli.py             # extend: delta-explain + recommend-workflow CLI
```

### Pattern 1: Explainable Delta Contract (DELT-02)

**What:** Every standard assessment produces a typed `DeltaExplanation` projection that combines what's already in `standards_assessments` (evidence, confidence, freshness, reason) with what's in `standards_delta_items` (remediation, priority_score, priority_bucket) and overlays a four-state `provenance` derived from the assessment status + confidence + evidence-source plurality.

**When to use:** Anytime a domain score or per-standard score is surfaced to an operator or to grounded query.

**Example:**
```python
# Source: extends services/standards_health.py
from dataclasses import dataclass
from typing import Any
from services.capability_truth import Provenance  # reuse — do not redefine


@dataclass(frozen=True)
class DeltaExplanation:
    standard_id: str
    domain: str
    status: str  # existing: pass/partial/fail/unknown/waived/not_applicable
    provenance: Provenance  # NEW: confirmed/inferred/missing/contradictory
    confidence: float
    freshness: str  # ISO timestamp from last_evaluated_at
    evidence: tuple[str, ...]
    contradiction: str | None  # populated when two evidence sources disagree
    remediation_summary: str
    remediation_effort: float
    remediation_leverage: float
    priority_score: float
    priority_bucket: str
    measured_state: dict[str, Any]
    expected_state: dict[str, Any]
    reason: str


def build_explanation(
    *,
    evaluation: "EvaluatedStandard",
    delta_item: dict[str, Any] | None,
    capability_signals: dict[str, Any] | None = None,
) -> DeltaExplanation:
    provenance = _classify_provenance(
        status=evaluation.status,
        confidence=evaluation.confidence,
        evidence=evaluation.evidence,
        evaluator_type=evaluation.evaluator_type,
        cross_signals=capability_signals,
    )
    contradiction = _detect_contradiction(evaluation, capability_signals)
    remediation = (delta_item or {}).get("remediation_playbook") or evaluation.standard.remediation_playbook
    return DeltaExplanation(
        standard_id=evaluation.standard.id,
        domain=evaluation.standard.domain,
        status=evaluation.status,
        provenance=provenance,
        confidence=evaluation.confidence,
        freshness=evaluation.last_evaluated_at,
        evidence=evaluation.evidence,
        contradiction=contradiction,
        remediation_summary=str(remediation.get("summary", "")),
        remediation_effort=float(remediation.get("effort", 1.0)),
        remediation_leverage=float(remediation.get("leverage", 1.0)),
        priority_score=float((delta_item or {}).get("priority_score", 0.0)),
        priority_bucket=str((delta_item or {}).get("priority_bucket", "high_leverage")),
        measured_state=evaluation.measured_state,
        expected_state=evaluation.standard.expected_state,
        reason=evaluation.reason,
    )
```

### Pattern 2: Provenance Classification Bridge

**What:** Today `EvaluatedStandard.status` uses pass/partial/fail/unknown/waived/not_applicable (a *quality* axis). `TrustedSignal.provenance` uses confirmed/inferred/missing/contradictory (a *source-quality* axis). DELT-03 requires both views. Phase 7 maps assessment fields → provenance without collapsing them.

**When to use:** Inside `build_explanation()` and inside any UI projection.

**Example:**
```python
# Source: new helper in services/standards_health.py
def _classify_provenance(
    *,
    status: str,
    confidence: float,
    evidence: tuple[str, ...],
    evaluator_type: str,
    cross_signals: dict[str, Any] | None,
) -> Provenance:
    # confirmed: auto evaluator AND non-empty evidence AND high confidence
    if evaluator_type == "auto" and evidence and confidence >= 0.75:
        return "confirmed"
    # contradictory: detect from cross-signal comparison (Pattern 3)
    if cross_signals and _has_contradiction(status, cross_signals):
        return "contradictory"
    # missing: no evidence at all OR explicit unknown status
    if not evidence or status == "unknown":
        return "missing"
    # inferred: manual / semi_auto evaluator OR moderate confidence
    return "inferred"
```

### Pattern 3: Contradiction Detection (DELT-03)

**What:** A contradiction exists when two evidence sources disagree about the same dimension — e.g., `standards_assessments.status = "pass"` for `testing.trust_signal` but `success_criteria_findings` has open blockers for the `testing-trust` criterion. Phase 7 wires the `related_criteria` field on each standard to cross-check assessment status against the criteria findings table.

**When to use:** Inside `_build_explanations()` for every standard that declares `related_criteria`.

**Example:**
```python
# Source: new helper in services/standards_health.py
def _detect_contradiction(
    evaluation: "EvaluatedStandard",
    capability_signals: dict[str, Any] | None,
) -> str | None:
    if not evaluation.standard.related_criteria:
        return None
    if capability_signals is None:
        return None
    open_blockers_for_related = capability_signals.get("findings_by_criterion", {})
    for criterion_id in evaluation.standard.related_criteria:
        blockers = open_blockers_for_related.get(criterion_id, 0)
        if evaluation.status == "pass" and blockers > 0:
            return (
                f"Standard reports pass but {blockers} open blocker(s) exist "
                f"on related criterion '{criterion_id}'."
            )
        if evaluation.status == "fail" and blockers == 0 and evaluation.confidence < 0.5:
            return (
                f"Standard reports fail with low confidence ({evaluation.confidence}) "
                f"but no findings recorded on related criterion '{criterion_id}'."
            )
    return None
```

### Pattern 4: Workflow Recommendation From Health (DELT-04)

**What:** Map `(priority_bucket, domain, status, foundational)` tuples to recommended workflow keys with rationale. Reuse the existing workflow recommender for objective-based ranking when health-state is ambiguous.

**When to use:** When an operator opens a project surface, when grounded query asks "what should I run next", or when the CLI `recommend-workflow` command runs.

**Example:**
```python
# Source: extends services/workflow_orchestration.py
HEALTH_TO_WORKFLOW_RULES = [
    # (predicate, workflow_key, rationale_template)
    (
        lambda d: d["priority_bucket"] == "blocked" and d["domain"] == "workflow_agent_control",
        "failure-recovery",
        "Critical workflow-handshake blocker — recover handshake integrity before other work.",
    ),
    (
        lambda d: d["domain"] == "security" and d["status"] in {"fail", "partial"},
        "security review",  # planned workflow_family; mark as planned in output
        "Security domain has open delta — focused security review before broader work.",
    ),
    (
        lambda d: d["domain"] == "architecture" and d["status"] == "fail",
        "codebase architecture review",  # planned
        "Architecture boundary failure — review before remediation work compounds.",
    ),
    (
        lambda d: d["priority_bucket"] in {"foundational", "high_leverage"},
        "standards backfill",  # planned
        "Highest-leverage standards gap — backfill workflow targets foundational deltas.",
    ),
    (
        lambda d: d["priority_bucket"] == "quick_wins",
        "implementation-delivery",
        "Quick-win standards gap — implementation-delivery covers low-effort fixes.",
    ),
]


def recommend_workflow_from_health(
    *,
    delta_items: list[dict[str, Any]],
    registry_workflows: set[str],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in sorted(delta_items, key=lambda d: d["priority_score"], reverse=True):
        for predicate, workflow_key, rationale in HEALTH_TO_WORKFLOW_RULES:
            if predicate(item):
                if workflow_key in seen:
                    continue
                seen.add(workflow_key)
                recommendations.append(
                    {
                        "workflow_key": workflow_key,
                        "available_in_registry": workflow_key in registry_workflows,
                        "rationale": rationale,
                        "triggered_by": {
                            "standard_id": item["standard_id"],
                            "domain": item["domain"],
                            "priority_bucket": item["priority_bucket"],
                            "priority_score": item["priority_score"],
                        },
                    }
                )
                break
    return recommendations[:5]  # top 5 unique workflow recommendations
```

### Pattern 5: Domain Coverage Extension (DELT-01)

**What:** Add five standards entries to `config/standards/registry.json` so all ten DELT-01 domains have at least one signal, even if some start as `unknown` with explicit `missing_reason` and rely on `ManualAssessmentOverride`.

**When to use:** Phase 7 task wave 1.

**Example registry entries (representative):**
```json
{
  "id": "maintainability.dead_code_signal",
  "domain": "maintainability",
  "title": "Dead Code Signal",
  "description": "Project surfaces a recent dead-code scan (vulture / knip / ts-prune) with no high-confidence findings unresolved.",
  "weight": 5,
  "severity_if_missing": 3,
  "evaluation_method": "auto",
  "expected_state": {"vulture_or_knip_clean": true},
  "remediation_playbook": {
    "summary": "Run vulture (Python) or knip (TS) and resolve or document each finding.",
    "effort": 1.5,
    "leverage": 1.1
  },
  "blocking_dependencies": ["code_quality.lint_ratchet"],
  "version": "2026.06.0",
  "introduced_version": "2026.06.0",
  "applicability": {"projects": ["*"]},
  "waiver_policy": {"allowed": true, "requires_owner": true, "requires_review_date": true, "max_days": 14},
  "related_criteria": ["code-simplicity"],
  "metadata": {"foundational": false}
}
```

Similar entries for `ux.operator_clarity`, `launch_readiness.deployable`, `agent_readiness.handoff_packet`, and `standards_compliance.profile_attached` (the last is a meta-standard that fails if any other standard is `unknown` for too long).

### Anti-Patterns to Avoid

- **Inventing a new "score" framework:** `_compute_score()` already exists with weighted-penalty math, domain rollup, regression handling, and unknown-coverage tracking. Phase 7 must not replace it. Extend the inputs (more standards) and outputs (DeltaExplanation projection); leave the math alone.
- **Adding a `delta_explanations` SQLite table:** All columns required for explanations already exist on `standards_assessments` + `standards_delta_items`. A new table would just denormalize what's already there and create a sync-drift risk between the existing tables and the cache.
- **Letting workflow recommendations promote themselves into runs without governance:** Phase 5 already shipped approval policy classes for `workflow-default` impact scope. Phase 7 workflow recommendations are **advisory only** — promoting them to actual runs reuses Phase 5 governance gates.
- **Hard-coupling the recommender to currently-registered workflows only:** `standards backfill`, `audit-only`, `codebase architecture review`, and `security review` are still planned per `WORKFLOW_MATRIX.md` lines 56-64. The recommender must return them with `available_in_registry: false` rather than skip them — that surface signals to operators what's missing.
- **Collapsing four-state provenance into the existing status enum:** "fail with high confidence" (`status=fail`, `provenance=confirmed`) and "unknown because we couldn't measure" (`status=unknown`, `provenance=missing`) and "contradictory across sources" (`status=fail`, `provenance=contradictory`) MUST remain distinguishable in the UI. The two enums are orthogonal and both must surface.
- **Cross-project ranking without per-project context:** A `priority_score` of 12 on Project A and a `priority_score` of 12 on Project B don't mean the same thing — they depend on project weight, profile attachment, and quantity of unknowns. Cross-project ranking is out of scope for Phase 7 unless explicitly requested; per-project ranking is sufficient for DELT-04.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-domain weighted scoring | New scorer class | `_compute_score()` in `services/standards_health.py` | Already handles weights, penalty multipliers, regression flag, domain rollup, unknown coverage. |
| Priority scoring (severity × leverage × dependency_unlock × regression_penalty / effort) | New prioritizer | `_build_delta_items()` formula | Already encodes the leverage-vs-effort tradeoff and dependency unlock count. |
| Priority bucketing | New bucketing logic | `_priority_bucket()` (existing: waived_deferred / blocked / foundational / quick_wins / high_leverage) | Five buckets already cover the DELT-04 surface; do not add a sixth. |
| Four-state signal classification | New enum | `Provenance = Literal["confirmed","inferred","missing","contradictory"]` from `services/capability_truth.py` | Single source of truth across services and UI. |
| Per-criterion finding lifecycle | New lifecycle | `EVALUATION_FINDING_LIFECYCLE_STATES = ["open","accepted","resolved","waived","stale"]` from `aios_cli.py` | Phase 5 added the columns; Phase 6 added stage findings; Phase 7 reuses for backfill-task lifecycle alignment. |
| Workflow ranking from text | New ranker | `rank_workflow_candidates()` in `services/workflow_orchestration.py` | Phase 7 layers health-state on top, doesn't replace. |
| Approval policy for standards-affecting writebacks | New approval flow | `writeback_approval_policy(layer_type, impact_scope, ...)` from `bin/aios_orchestration_runtime.py` | Phase 5 already wired `standards`/`standards-default`/`workflow-default` policy classes. |
| Per-gate status tracking | New gate tracker | `services/quality_pipeline.py` + `quality_pipeline_runs` | Already covers lint/typecheck/test/build/architecture/ci with applicability inference. |
| Standards registry parsing | New parser | `standards_health.load_registry()` | Already returns `(profile, list[StandardDefinition])` with all fields. |
| Trust-signal UI contract | New types | `aios-ui/lib/trusted-signals.ts` + `aios-ui/lib/types.ts` | Already mirrors the Python `TrustedSignal` shape; reuse. |

**Key insight:** Phase 7 is overwhelmingly about **projecting and surfacing existing primitives**, not building new ones. The two genuinely new pieces are (a) the five missing DELT-01 domains in the standards registry, and (b) the health-to-workflow recommender. Everything else is wiring.

## Runtime State Inventory

*Phase 7 is a code/config/UI evolution, not a rename or refactor. The Runtime State Inventory section applies only to rename/refactor phases. Confirmed: no string-rename or migration occurs in this phase; existing `standards_health_snapshots`, `standards_assessments`, `standards_delta_items`, and `standards_backfill_tasks` rows remain valid under the extended registry because (1) `attached_version` already pins each project to a registry version and the new standards have `introduced_version: "2026.06.0"`, which means existing projects will see them as `not_applicable` until migration mode advances; (2) no SQL ALTER on existing columns is required.*

## Common Pitfalls

### Pitfall 1: Score Drift When New Standards Are Introduced Without Migration

**What goes wrong:** Adding five new standards bumps `profile.version` to `2026.06.0`. Existing projects still pinned to `2026.05.0` (via `project_standards_profiles.attached_version`) will see the new standards as `not_applicable` because `_version_gt(introduced_version, attached_version)` returns True. If the operator expects "we added a maintainability standard" to immediately affect their score, but `attached_version` still says `2026.05.0`, the new standard contributes zero and the score is unchanged.

**Why it happens:** `standards_health.py` lines 1354-1382 explicitly migrate-skip standards whose `introduced_version > attached_version` (correct behavior — protects projects from surprise score drops).

**How to avoid:** Phase 7 must include a documented migration step (e.g., bump `attached_version` to `2026.06.0` in `project_standards_profiles` for the AIOS project itself) and surface `migration_delta_count` and `migration_weight` in the operator UI as part of the health view so operators can see "5 new standards are pending migration" rather than "no change."

**Warning signs:** Post-deploy: `standards_health_snapshots.unknown_count` stays flat, `migration_json.migration_delta_count = 5`, and the score doesn't move.

### Pitfall 2: Contradiction Detection False Positives From Stale Findings

**What goes wrong:** `_detect_contradiction` cross-checks standard status against `success_criteria_findings.resolution_status = 'open'`. Phase 6 added the lifecycle column but few resolution writes exist yet, so most findings are stuck at `open`. A standard reporting `pass` against `testing.trust_signal` will look "contradictory" because the related `testing-trust` criterion has open findings from runs months ago.

**Why it happens:** Resolution lifecycle is wired but underused; "open" doesn't necessarily mean "currently failing."

**How to avoid:** Contradiction detection must filter findings by recency (e.g., last 14 days) and by run-linkage to the **latest** assessment, not all-time. Add a `findings_within_days` parameter to `_detect_contradiction`.

**Warning signs:** Every `pass`-status standard has a `contradictory` overlay on first deploy.

### Pitfall 3: Workflow Recommendations That Refer To Workflows Not In The Registry

**What goes wrong:** `recommend_workflow_from_health()` returns `standards backfill`, `audit-only`, `codebase architecture review`, and `security review` — none of which are in `config/workflows/registry.json` yet (per `WORKFLOW_MATRIX.md` they are planned for Phase 8). The UI surfaces these recommendations; an operator clicks one; nothing happens because the workflow can't be launched.

**Why it happens:** Phase 7 surfaces recommendations that depend on Phase 8 to deliver the executable contracts.

**How to avoid:** Every recommendation includes `available_in_registry: bool`. UI MUST render unavailable workflows distinctly (e.g., grayed with "planned — Phase 8" tooltip), and the CLI MUST refuse to launch them with a clear "workflow not yet registered" error. Do NOT let the recommendation pretend the workflow exists.

**Warning signs:** Operator clicks a recommendation; the orchestration runtime errors with `KeyError: 'standards backfill'`.

### Pitfall 4: Cross-Project Ranking Conflates Profile Bindings

**What goes wrong:** If Project A is pinned to `2026.04.0` and Project B is pinned to `2026.05.0`, Project B sees more standards and naturally has a higher `unmet_standards_count`. A naive cross-project ranking would say "Project B is worse" when really it's just "Project B is on a newer profile."

**Why it happens:** `priority_score` is computed per-standard, not per-project-normalized.

**How to avoid:** Phase 7 scopes recommendations per-project (do not introduce cross-project rankings). If cross-project visibility is needed, normalize against `max_penalty` (which is already per-project-weight-aware).

**Warning signs:** Operator sees Project B always at the top of a hypothetical leaderboard despite Project B being objectively healthier.

### Pitfall 5: Manual Override Path Stays Empty For New Domains

**What goes wrong:** Phase 7 adds `maintainability`, `UX`, `launch_readiness`, `agent_readiness`, `standards_compliance` evaluators that initially return `unknown` (because no auto evaluator exists). The `ManualAssessmentOverride` TypedDict is supported by `evaluate_and_record(overrides=...)` but nothing currently calls it — there's no CLI or UI command to set an override.

**Why it happens:** Override path is plumbed end-to-end but unsurfaced.

**How to avoid:** Phase 7 must add an `aios standards-override --standard X --status pass --reason "..."` CLI command (or the UI equivalent) so the override path is actually usable. Otherwise the new domains stay permanently `unknown`.

**Warning signs:** All five new domains stay at `unknown` indefinitely; `evaluation_confidence` drops; `unknown_coverage` grows monotonically.

### Pitfall 6: Health Recommendation Becomes A Hidden Approval Gate

**What goes wrong:** UI surfaces "we recommend running `standards backfill`" but launching it requires Phase 5 approval policy. Operator clicks; gets blocked by approval; backs off; recommendation looks broken.

**Why it happens:** Recommendation = advisory; promotion = governed. These get conflated.

**How to avoid:** Recommendation responses MUST include `requires_approval: bool` + `impact_scope` so the UI can show the approval requirement upfront. Reuse `writeback_approval_policy(layer_type="workflow", impact_scope=...)` from Phase 5.

**Warning signs:** Operators report "recommendations don't actually launch."

## Code Examples

Verified patterns from existing code:

### Reading An Existing Health Snapshot

```python
# Source: services/standards_health.py:latest_snapshot (verbatim)
from services.standards_health import latest_snapshot
snap = latest_snapshot(conn, project_id="proj")
# returns: {id, project_id, profile_id, attached_version, latest_version,
#          overall_score, critical_delta_count, regression_count,
#          unknown_count, evaluation_confidence, created_at} | None
```

### Computing Domain Scores (Existing Math)

```python
# Source: services/standards_health.py:_compute_score (lines 828-913 verbatim shape)
# Returns:
{
    "overall_score": 78.4,
    "weighted_delta": 14.5,
    "max_penalty": 67.5,
    "unmet_standards_count": 3,
    "critical_delta_count": 1,
    "regression_count": 0,
    "unknown_count": 2,
    "unknown_coverage": 0.18,
    "evaluation_confidence": 0.72,
    "domain_scores": {
        "architecture": {"score": 90.0, "confidence": 0.85, "weight": 9.0},
        "testing": {"score": 65.0, "confidence": 0.8, "weight": 8.0},
        # ...
    }
}
```

### Reading TrustedSignal Provenance (DELT-03 Contract)

```python
# Source: services/capability_truth.py:TrustedSignal (verbatim)
from services.capability_truth import TrustedSignal, Provenance

signal = TrustedSignal(
    value=78.4,
    provenance="confirmed",  # one of: confirmed | inferred | missing | contradictory
    confidence=0.9,
    source={"label": "Standards health snapshot", "table": "standards_health_snapshots", "field": "overall_score"},
    freshness="2026-05-20T19:06:31Z",
    explanation="Latest standards-health score on a 0-100 scale.",
    missing_reason=None,
    contradiction=None,
)
```

### UI Side — Reusing The Same TrustedSignal Contract

```typescript
// Source: aios-ui/lib/trusted-signals.ts (verbatim)
export type TrustedSignalProvenance = "confirmed" | "inferred" | "missing" | "contradictory";

export type TrustedSignalSource = {
  label: string;
  table?: string;
  field?: string;
};

export type TrustedSignal<T> = {
  value: T;
  provenance: TrustedSignalProvenance;
  confidence: number;
  source: TrustedSignalSource;
  freshness: string;
  explanation: string;
  missingReason?: string | null;
  contradiction?: string | null;
};
```

### Existing Backfill Task Projection (Phase 7 Extends With Recommendations)

```typescript
// Source: aios-ui/server/aios/standards-health.ts:getProjectStandardsHealth (existing)
const summary = getProjectStandardsHealth(db, projectId);
// summary.deltaItems: StandardsDeltaItem[]
//   - id, standardId, domain, severity, status, summary,
//   - estimatedHealthImpact, blockers, foundational, linkedTaskIds,
//   - priorityScore, priorityBucket
// summary.backfillTasks: StandardsBackfillTask[]
//   - id, deltaItemId, standardId, title, problemStatement, expectedState,
//   - acceptanceCriteria, effort, dependencyChain, expectedHealthImpact,
//   - owner, blockedReason, dueAt, reviewAt, priorityScore, priorityBucket,
//   - blocked, status
// Phase 7 adds: summary.deltaExplanations[] + summary.recommendedWorkflows[]
```

### Approval Policy Class (Phase 5 — Reused For Workflow Recommendation Promotion)

```python
# Source: bin/aios_orchestration_runtime.py:writeback_approval_policy (verbatim)
policy = writeback_approval_policy(
    layer_type="workflow",
    impact_scope="workflow-default",  # triggers approval gating
    proposed_change={"workflow_key": "standards backfill"},
    requires_approval=False,  # auto-derived from impact_scope
)
# policy = {"policy_class": "workflow-default_change",
#           "requires_approval": True,
#           "reason": "workflow-default changes require approval before promotion."}
```

### Existing Workflow Recommender (Phase 7 Extends)

```python
# Source: services/workflow_orchestration.py:recommend_route_primitives (verbatim shape)
from services.workflow_orchestration import recommend_route_primitives

result = recommend_route_primitives(
    objective="bring this project to standard",
    surface="codex",
)
# result.selected_workflow.workflow_key: e.g., "implementation-delivery" (will be wrong
#   for "bring to standard" until Phase 7's health-aware path adds "standards backfill")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-axis status (pass/fail/...) | Two-axis: quality status + provenance | Phase 7 (this phase) | Operators can tell "we failed with high confidence" apart from "we don't know" apart from "sources disagree." |
| Health surfaced as one `overall_score` number | Health surfaced with per-domain breakdown + per-standard `DeltaExplanation` drill-down | Phase 7 | Drill-down satisfies `TIER_ONE_ACCEPTANCE_CHECKLIST.md` Phase 7 failure conditions. |
| Workflow recommendation from objective text only | Workflow recommendation from objective text + project health state | Phase 7 | "What should I run next?" answers from delta state, not just keyword matching. |
| `standards backfill`/`audit-only` workflows referenced only in planning docs | `standards backfill`/`audit-only`/`codebase architecture review` surface as available recommendations marked `available_in_registry: false` | Phase 7 | Operator-visible signal of what Phase 8 must deliver next. |
| Standards registry covered 7 distinct DELT-01 domains | Standards registry covers all 10 (5 new entries may start as `unknown` with explicit `missing_reason`) | Phase 7 | DELT-01 acceptance becomes measurable. |
| Closeout report governance state from Phase 5 | Closeout report + governance state + workflow recommendation from health | Phase 7 | One operator surface answers "what's wrong?" and "what should we do about it?" |

**Deprecated/outdated:**
- Treating `code_quality` as a stand-in for `maintainability` — Phase 7 adds an explicit `maintainability` domain so DELT-01 enumeration is complete. `code_quality.lint_ratchet` remains valid but is now joined by `maintainability.dead_code_signal` (or similar).
- Treating `product_readiness.command_center_operability` as a proxy for `launch_readiness` — they overlap but `launch_readiness` should track deployability evidence (CI green, release notes present) distinctly from operator-surface readiness.
- One-shot workflow ranking on objective text alone — Phase 7 adds a health-state path; the objective-text path remains valid as a fallback when no health snapshot exists.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The five missing DELT-01 domains (`maintainability`, `UX`, `launch_readiness`, `agent_readiness`, `standards_compliance`) should be added as new registry standards rather than re-tagging existing ones (e.g., relabeling `code_quality` as `maintainability`). | Pattern 5 | If the user prefers re-tagging, the registry change is smaller but the historic snapshots become harder to interpret because domain labels would change retroactively. Confirm in discuss-phase. |
| A2 | Workflow recommendations are advisory and need NOT auto-launch the recommended workflow. | Pattern 4 | If the user wants auto-launch with approval gating, scope expands to wire the Phase 5 governance API end-to-end through the recommender. |
| A3 | Cross-project ranking is out of scope; per-project ranking suffices. | Anti-Patterns | If the user wants a portfolio-wide "top deltas across all projects," additional normalization work (penalty-relative ranking) is needed. The `prove-project-health` CLI already does some cross-project iteration so the surface exists; ranking math doesn't. |
| A4 | The four planned workflows (`standards backfill`, `audit-only`, `codebase architecture review`, `security review`) are still owned by Phase 8 for full stage contracts; Phase 7 only surfaces them with `available_in_registry: false`. | Common Pitfalls 3 | If the user wants Phase 7 to also REGISTER these workflows (even with minimal stages), scope expands to include Phase 8's contract work — confirm in discuss-phase. |
| A5 | `standards_assessments.evidence_json` consistently contains usable strings for explanation surfaces (no schema migration needed). | Pattern 1 | Verified: `_persist_assessments` writes `_json(list(evaluation.evidence))` so the column is always a JSON array; UI can parse with the existing `parseJsonArray<string[]>` helper. **VERIFIED — no risk.** |
| A6 | Adding a `findings_by_criterion` aggregation to `capability_truth_payload` is the cheapest path for contradiction detection (avoids a separate query per standard). | Pattern 3 | If `capability_truth_payload` is consumed by many places with strict shape expectations, adding the aggregation is a shape change. **MEDIUM risk** — verify by grepping `capability_truth_payload` consumers (Phase 7 task 01 verification step). |
| A7 | Bumping `profile.version` to `2026.06.0` is acceptable and the existing migration logic handles it without per-project intervention. | Pitfall 1 | Verified: `_ensure_project_binding` updates `latest_version` automatically but leaves `attached_version` pinned, which is the documented "migration_mode = current" behavior. Operators advance via UI/CLI later. **VERIFIED — no risk.** |
| A8 | `Provenance` literal type from `services/capability_truth.py` can be imported by `services/standards_health.py` without circular import. | Code Examples | Quick check: `capability_truth.py` imports from `services.rtk_integration` only. `standards_health.py` has no current imports from `capability_truth`. **LOW risk** but verify on first task. If circular, move the literal to a shared `services/signal_provenance.py` module. |

## Open Questions (RESOLVED)

1. **Should new domain standards (maintainability/UX/launch_readiness/agent_readiness/standards_compliance) require explicit operator override for the first cycle, or auto-set to `unknown` with `missing_reason` and stay there until manual override?**
   - What we know: `ManualAssessmentOverride` TypedDict already supports per-standard overrides via `evaluate_and_record(overrides=...)`.
   - What's unclear: Whether Phase 7 should ship a default override per AIOS project so the new domains immediately contribute meaningful signal, or leave them `unknown` and require the operator to act.
   - Recommendation: Leave `unknown` with explicit `missing_reason` to honor "honest reporting" — surfaces the gap rather than hiding it. Add the `aios standards-override` CLI in Phase 7 so the operator can flip them when ready.

2. **How aggressive should contradiction detection be?**
   - What we know: `related_criteria` field on each standard provides the join key.
   - What's unclear: Whether contradiction detection should also cross-check `standards_health_snapshots.overall_score` trend against individual standard regressions, or stay limited to standard-vs-finding comparison.
   - Recommendation: Start narrow (standard-vs-related-criterion). Add trend-based contradiction in a later phase only if signal-vs-noise warrants it.

3. **Should workflow recommendations surface in grounded query (`aios-ui/server/routers/query.ts`) or only in project-health views?**
   - What we know: Phase 4 grounded query exists; Phase 10 will integrate recommendations more broadly.
   - What's unclear: Whether Phase 7 query integration is in scope or deferred to Phase 10.
   - Recommendation: Include in query for parity with project-health surfaces (the recommender output is small and reusable). Document the surface in the Phase 7 plan so Phase 10 can extend rather than rebuild.

4. **What's the right unit-of-explanation granularity — per standard, per domain, or both?**
   - What we know: Per-standard explanations are sufficient for drill-down; per-domain rollup is sufficient for at-a-glance.
   - What's unclear: Whether the UI needs a separate `DomainExplanation` type or whether domain-level explanations are computed at projection time from per-standard explanations.
   - Recommendation: Per-standard `DeltaExplanation` is the canonical unit; domain-level views are aggregations computed on the fly. No separate type needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All phase 7 work | ✓ | 3.12 (per pyproject.toml requires-python) | — |
| sqlite3 stdlib | Persistence (no new tables — read existing) | ✓ | stdlib | — |
| ruff | Lint gate | Assumed present | per pyproject.toml | Quality ladder hard gate fails fast if missing |
| basedpyright | Typecheck gate | Assumed | per pyproject.toml | — |
| pytest 8.x | Test gate | ✓ (used in Phase 5/6) | — | — |
| vulture | Dead-code report | Assumed | per pyproject.toml | Report-only, non-blocking |
| `uv` runner | Phase 5/6 verification commands use it | Likely ✓ | per `uv.lock` | Fall back to bare `python -m pytest` |
| pnpm | UI quality ladder | Assumed (per aios-ui/) | — | — |
| better-sqlite3 | UI server DB access | ✓ (per `aios-ui/package.json`) | — | — |
| tRPC v11 | UI router boundary | ✓ | — | — |
| zod | UI runtime validation | ✓ | — | — |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** None; all dependencies are in-tree or stdlib.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (Python 3.12) + Node test runner for context-compile tests |
| Config file | `pyproject.toml` (ruff + basedpyright + vulture sections); no separate `pytest.ini` block |
| Quick run command | `uv run pytest tests/test_standards_health.py tests/test_aios_cli.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DELT-01 | Registry adds all 5 missing DELT-01 domains, each producing a row in `standards_definitions` | unit | `uv run pytest tests/test_standards_health.py::test_registry_covers_all_delt_01_domains -x` | ❌ Wave 0 |
| DELT-01 | Domain rollup in `_compute_score()` includes all 10 named domains | unit | `uv run pytest tests/test_standards_health.py::test_compute_score_emits_all_ten_domains -x` | ❌ Wave 0 |
| DELT-02 | `build_explanation()` returns evidence + confidence + freshness + remediation per standard | unit | `uv run pytest tests/test_standards_health.py::test_build_explanation_includes_required_fields -x` | ❌ Wave 0 |
| DELT-02 | UI `getProjectStandardsHealth` payload includes `deltaExplanations[]` | unit | `cd aios-ui && pnpm tsc --noEmit && pnpm lint` (type-level guarantee via `StandardsHealthSummary` type) | partial — type extension required |
| DELT-03 | `_classify_provenance()` returns `confirmed` for auto evaluators with evidence + high confidence | unit | `uv run pytest tests/test_standards_health.py::test_classify_provenance_confirmed_for_auto_with_evidence -x` | ❌ Wave 0 |
| DELT-03 | `_classify_provenance()` returns `missing` when evidence is empty | unit | `uv run pytest tests/test_standards_health.py::test_classify_provenance_missing_without_evidence -x` | ❌ Wave 0 |
| DELT-03 | `_classify_provenance()` returns `contradictory` when related-criterion findings disagree | integration | `uv run pytest tests/test_standards_health.py::test_classify_provenance_contradictory_on_stale_findings -x` | ❌ Wave 0 |
| DELT-03 | `_classify_provenance()` returns `inferred` for manual/semi_auto evaluators | unit | `uv run pytest tests/test_standards_health.py::test_classify_provenance_inferred_for_manual -x` | ❌ Wave 0 |
| DELT-04 | `recommend_workflow_from_health()` returns `standards backfill` (with `available_in_registry: false`) for foundational deltas | unit | `uv run pytest tests/test_standards_health.py::test_recommend_workflow_returns_standards_backfill_for_foundational -x` | ❌ Wave 0 |
| DELT-04 | Recommender includes `requires_approval` + `impact_scope` so UI can surface approval gates | unit | `uv run pytest tests/test_standards_health.py::test_recommend_workflow_includes_approval_policy -x` | ❌ Wave 0 |
| DELT-04 | CLI `aios recommend-workflow --project X` returns JSON with recommendations | integration | `uv run pytest tests/test_aios_cli.py::test_recommend_workflow_cli -x` | ❌ Wave 0 |
| DELT-04 | UI `getRecommendedWorkflowsFromHealth(db, projectId)` returns the projected recommendations | integration | `cd aios-ui && pnpm lint && pnpm tsc --noEmit` (type-level), plus a manual `pnpm test` if added | partial |

### Sampling Rate

- **Per task commit:**
  - Python: `uv run pytest tests/test_standards_health.py tests/test_aios_cli.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
  - UI (when TS files change): `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Per wave merge:**
  - `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright`
  - `cd aios-ui && pnpm lint && pnpm tsc --noEmit`
- **Phase gate:**
  - Full suite green + `aios contracts-audit` reports `implemented_count` increases for any new contracts added
  - `aios prove-project-health` for the AIOS project itself shows score ≥ pre-phase baseline + all 10 DELT-01 domains present in `domain_scores_json`
  - Manual operator check: open the project surface in `aios-ui` and confirm `deltaExplanations` render with drill-down + recommendations surface with `available_in_registry: false` callouts where applicable

### Wave 0 Gaps

- [ ] `tests/test_standards_health.py` — add test fixtures and stubs for the test names above (covers all 9 new test functions)
- [ ] `tests/test_aios_cli.py` — add stub for `test_recommend_workflow_cli`
- [ ] `aios-ui/lib/control-plane.ts` — extend `StandardsHealthSummary` type with `deltaExplanations: DeltaExplanation[]` and `recommendedWorkflows: RecommendedWorkflow[]` (type-level Wave 0 work; no test file)
- [ ] No new conftest.py needed — existing tests use direct `sqlite3.connect(":memory:")` patterns
- [ ] No framework install required; pytest + ruff + basedpyright + pnpm already wired

## Security Domain

> Phase 7 introduces no new authentication, session management, network surface, or cryptographic concerns. Security applicability is limited to: (a) workflow recommendations that promote standards-affecting writebacks must reuse Phase-5 approval policy, (b) explanation payloads must not leak filesystem paths or evidence that contains sensitive content beyond what `standards_assessments.evidence_json` already exposes, and (c) the `security.review_traceability` standard's evaluator must continue to function as Phase 7 extends the explanation contract.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — internal CLI / hook / UI-server surface |
| V3 Session Management | no | n/a |
| V4 Access Control | partial | Phase-5 approval policy classes gate standards-affecting and workflow-default writebacks; Phase 7 reuses for any recommendation-driven promotion |
| V5 Input Validation | yes | Registry JSON parsed via `_load_json` with type guards; new domain entries must validate `weight`, `severity_if_missing`, `version`, `introduced_version`, `applicability` fields. UI tRPC routes validate input with `zod`. |
| V6 Cryptography | no | n/a |
| V7 Error Handling | yes | Explanation builder must not silently drop standards when `standards_assessments` rows are missing — surface `provenance: "missing"` with a clear `missing_reason` |
| V10 Malicious Code | no | n/a |
| V13 API & Web Service | partial | tRPC routes already validate inputs; new `recommendWorkflowFromHealth` route uses the same pattern. No new external API surface introduced. |
| V14 Configuration | yes | New standards entries in `config/standards/registry.json` are reviewable in git; do not introduce secrets or env-derived config into the registry |

### Known Threat Patterns for Delta Scoring And Recommendation

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stale findings drive false "contradictory" classifications | Information Disclosure | Filter contradiction detection to recent findings (e.g., last 14 days) + same-run scope; document the freshness window |
| Recommendations refer to unregistered workflows and silently fail | Denial of Service (operator UX) | `available_in_registry: bool` on every recommendation; UI MUST render unavailable workflows distinctly; CLI MUST refuse to launch with a clear error |
| Manual override path allows arbitrary status flips without rationale | Repudiation | `ManualAssessmentOverride` already requires `reason`; the new `aios standards-override` CLI MUST persist `evaluator_type: "manual"`, the actor identity, and the reason — no anonymous overrides |
| Explanation payloads leak sensitive filesystem paths via `evidence_json` | Information Disclosure | Evidence already passes through `_json(list(evaluation.evidence))`; Phase 7 does not change this surface — but new evaluators should not write absolute home-directory paths into evidence (use repo-relative or canonical labels) |
| Workflow recommendation reuses cached priority_score after registry rev | Tampering / staleness | `priority_score` is recomputed every snapshot; do not cache outside the snapshot lifecycle. Recommendation read-time projection is the right boundary |
| Bumping `profile.version` causes silent score drops on projects with `migration_mode: current` | Repudiation / Tampering | Existing migration logic in `evaluate_and_record` lines 1354-1382 already marks new standards as `not_applicable` until `attached_version` advances. Surface `migration_delta_count` in the operator UI so the operator sees pending migration explicitly |

## Sources

### Primary (HIGH confidence)

- `services/standards_health.py` (in-tree, lines 1-1599) — full scoring math, registry loader, evaluator dispatch, delta items, backfill tasks, migration handling. [VERIFIED: read complete file]
- `services/capability_truth.py` (in-tree, lines 1-617) — `TrustedSignal` dataclass, `Provenance` literal, project/RTK/automation/prompt-library/knowledge signal builders. [VERIFIED: read complete file]
- `services/quality_pipeline.py` (in-tree, lines 1-388) — per-gate run tracking, applicability inference. [VERIFIED: read complete file]
- `services/workflow_orchestration.py` (in-tree, `rank_workflow_candidates` + `recommend_route_primitives`) — text-based workflow recommender shape. [VERIFIED: read]
- `services/aios_cli.py` lines 2680-2772, 2754, 3520-3526 — `EvaluationFinding` contract status, `EVALUATION_FINDING_LIFECYCLE_STATES`, `capability_truth_payload` invocation. [VERIFIED: read]
- `config/standards/registry.json` — 10 standards covering 7 distinct DELT-01 domains; profile version `2026.05.0`. [VERIFIED: read complete file]
- `config/workflows/registry.json` — 6 registered workflows: `academic_paper_v1`, `implementation-delivery`, `failure-recovery`, `divergent-strategy`, `personalized-humanizer`, `agentize`; `standards backfill`/`audit-only`/`codebase architecture review`/`security review` are NOT registered. [VERIFIED: jq grep]
- `config/quality-pipeline.json` — gate definitions (install/lint/typecheck/test/build/architecture/ci/secret_scan/pre_pr_readiness). [VERIFIED: read]
- `schema.sql` lines 510-720 — `standards_*` table layout including `standards_assessments.evidence_json`/`confidence`/`last_evaluated_at`/`regression_flag`, `standards_delta_items.priority_score`/`priority_bucket`/`blockers_json`, `standards_health_snapshots.domain_scores_json`. [VERIFIED: read]
- `aios-ui/server/aios/standards-health.ts` (in-tree, lines 1-323) — `getProjectStandardsHealth` + `updateStandardsBackfillTask` UI projection. [VERIFIED: read complete file]
- `aios-ui/lib/trusted-signals.ts` — UI mirror of `TrustedSignal` contract. [VERIFIED: read]
- `aios-ui/server/routers/projects.ts` (in-tree, lines 1-160) — health/critical-delta/unknown-coverage signal projection into project rows. [VERIFIED: read]
- `bin/aios_orchestration_runtime.py` lines 816-852 — `writeback_approval_policy` policy class derivation. [VERIFIED: read]
- `.planning/REQUIREMENTS_CODE_SURFACE_MATRIX.md` lines 71-74 — DELT-01..DELT-04 surface authority mapping. [VERIFIED: read]
- `.planning/TIER_ONE_ACCEPTANCE_CHECKLIST.md` lines 146-166 — Phase 7 capability gates, evidence gates, failure conditions. [VERIFIED: read]
- `.planning/WORKFLOW_MATRIX.md` lines 50-68 — planned workflows including `standards backfill` (rows 56-64). [VERIFIED: read]
- `.planning/phases/06-*/06-RESEARCH.md` — Phase 6 stage findings, EvaluationFinding lifecycle, governance audit shape, approval policy classes from Phase 5. [VERIFIED: read complete file]
- `.planning/phases/05-*/05-02-SUMMARY.md` + `05-03-SUMMARY.md` — Phase 5 shipped governance overview, approval policy classes, control-plane router. [VERIFIED: read]
- `tests/test_standards_health.py` (in-tree, lines 1-333) — test pattern for in-memory sqlite + registry path injection. [VERIFIED: read first portion]

### Secondary (MEDIUM confidence)

- `services/automation_history.py` — imports `ensure_automation_run_history_schema` from `capability_truth.py`, confirming the capability_truth module is the canonical home for automation signal schema. [VERIFIED: grep]
- `aios-ui/server/aios/runtime.ts` line 1181 — `standards_delta_items` consumer in the UI runtime layer. [VERIFIED: grep]
- `aios-ui/server/aios/query.ts` line 302 — `standards_health_snapshots` row count surfaced through query. [VERIFIED: grep]
- `aios-ui/server/aios/project-components.ts` line 18 — `standards_health` keyed as a project component. [VERIFIED: grep]

### Tertiary (LOW confidence)

- None — this is an internal phase researched entirely against in-tree code and config; no external web sources required.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primary surface is in-tree and read directly during research; no external dependency assumptions.
- Architecture: HIGH — pattern follows the Phase 5/6 conventions; the explanation projection and workflow recommender are additive and use existing data shapes.
- Pitfalls: HIGH — pitfalls 1, 4, and 6 are grounded in existing code behavior (migration logic at lines 1354-1382, per-project priority math, Phase 5 approval policy). Pitfalls 2 and 5 are forward-looking but grounded in observed schema state (resolution lifecycle columns exist but unused in Phase 5).
- DELT-01 domain coverage: MEDIUM — five missing domain names are confirmed (`maintainability`, `UX`, `launch_readiness`, `agent_readiness`, `standards_compliance` are not present in `config/standards/registry.json`), but the user's intended definition of each (e.g., what counts as `agent_readiness`) needs confirmation in discuss-phase.
- Workflow-from-health recommender: MEDIUM — the mapping table is opinionated; the user may want different bucket→workflow mappings (e.g., is `architecture-domain critical` always architecture-review, or sometimes failure-recovery?).
- Cross-project ranking: not in scope per A3 — confirm in discuss-phase before assuming.

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (30 days — stable surfaces; `config/standards/registry.json` could rev with this phase itself)
