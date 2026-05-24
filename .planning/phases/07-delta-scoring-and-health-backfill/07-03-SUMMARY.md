# 07-03 Summary: CLI And UI Delta Health Surfaces

## Result

AIOS now exposes delta explanations, health-derived workflow recommendations, and standards manual overrides through operator CLI and UI contracts.

## Shipped

- Added `standards_manual_overrides` to `schema.sql` and the runtime standards-health schema.
- Added durable override persistence and automatic override loading in `evaluate_and_record`.
- Extended `aios governance-audit` with `recommended_workflows`.
- Extended `aios contracts-audit` with the `DeltaExplanation` contract.
- Added CLI commands:
  - `aios delta-explain --project <project> [--format json]`
  - `aios recommend-workflow --project <project> [--limit N]`
  - `aios standards-override --project <project> --standard <standard> --status <pass|partial|fail|unknown|waived|not_applicable> [--rationale TEXT] [--actor TEXT] [--confidence FLOAT] [--evidence VALUE ...] [--waiver-review-at ISO]`
- Added TypeScript types:
  - `DeltaExplanation`
  - `RecommendedWorkflow`
- Extended `StandardsHealthSummary` with `deltaExplanations` and `recommendedWorkflows`.
- Added UI-side `getProjectDeltaExplanations()` and `getRecommendedWorkflowsFromHealth()` in `aios-ui/server/aios/standards-health.ts`.

## Files Modified

- `aios-ui/lib/control-plane.ts` - 775 lines
- `aios-ui/server/aios/standards-health.ts` - 595 lines
- `schema.sql` - 862 lines
- `services/aios_cli.py` - 4160 lines
- `services/standards_health.py` - 2334 lines
- `tests/test_aios_cli.py` - 1972 lines

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_aios_cli.py -x -q -k "delta_explain or recommend_workflow or standards_override or governance_audit_includes_recommended"` -> 8 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_aios_cli.py tests/test_standards_health.py tests/test_workflow_orchestration.py -q` -> 68 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/aios_cli.py services/standards_health.py services/workflow_orchestration.py tests/test_aios_cli.py tests/test_standards_health.py tests/test_workflow_orchestration.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/aios_cli.py services/standards_health.py services/workflow_orchestration.py tests/test_aios_cli.py tests/test_standards_health.py tests/test_workflow_orchestration.py` -> 6 files already formatted
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/aios_cli.py services/standards_health.py services/workflow_orchestration.py` -> 0 errors
- `UV_CACHE_DIR=/tmp/uv-cache uv run vulture services/aios_cli.py services/standards_health.py --min-confidence 70` -> no findings
- `cd aios-ui && pnpm lint` -> exit 0; existing anti-slop warnings remain outside this change
- `git diff aios-ui/lib/control-plane.ts aios-ui/server/aios/standards-health.ts | grep "^+" | grep -E ": any\\b|<any>" | wc -l` -> 0
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -m services.aios_cli --json delta-explain --project nonexistent` -> returned parseable JSON with `delta_explanations: []`
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -m services.aios_cli --json governance-audit` -> returned parseable JSON with `recommended_workflows`

## Phase 7 Closeout

- DELT-01: registry covers ten domains and `_compute_score` emits all ten DELT-01 domain scores when a project is attached to profile `2026.06.0`.
- DELT-02: `DeltaExplanation` projects evidence, confidence, freshness, contradiction, and remediation per standard; CLI and UI both surface it.
- DELT-03: `_classify_provenance` returns confirmed, inferred, missing, or contradictory independently from assessment status; UI `DeltaExplanation.provenance` mirrors that contract.
- DELT-04: `recommend_workflow_from_health` returns prioritized recommendations with approval-policy and registry-membership annotations; CLI, UI, and governance audit surface those recommendations.

## Deferred

- Cross-project ranking remains out of scope.
- Grounded-query integration remains deferred to Phase 10; `getRecommendedWorkflowsFromHealth` is now callable when that surface is wired.
