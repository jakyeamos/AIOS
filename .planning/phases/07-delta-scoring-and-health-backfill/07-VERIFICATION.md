# 07 Verification: Delta Scoring And Health Backfill

## Status

Passed.

## Phase Outcome

Phase 7 turns standards and criteria evidence into explainable health signals, per-standard delta drill-downs, provenance-aware contradiction checks, prioritized workflow recommendations, and operator-resolvable manual overrides.

## Observable Success Criteria

- AIOS produces domain-level alignment scores across architecture, testing, maintainability, security, UX, observability, documentation, launch readiness, agent-readiness, and standards compliance: satisfied by registry version `2026.06.0`, five new standards, evaluator branches, and ten-domain score tests.
- Each score shows evidence, confidence, freshness, and remediation guidance: satisfied by `DeltaExplanation`, `build_explanation()`, `project_delta_explanations()`, `aios delta-explain`, and the UI `deltaExplanations` contract.
- Health views distinguish confirmed, inferred, missing, and contradictory signals: satisfied by `_classify_provenance`, contradiction detection against recent criteria findings, and the UI `TrustedSignalProvenance` type.
- The system can prioritize a backfill path for the highest-value standards or capability gaps: satisfied by `recommend_workflow_from_health`, CLI `recommend-workflow`, UI `recommendedWorkflows`, and governance-audit `recommended_workflows`.

## Verification Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_standards_health.py -q` -> 13 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_standards_health.py tests/test_workflow_orchestration.py -q` -> 39 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_aios_cli.py tests/test_standards_health.py tests/test_workflow_orchestration.py -q` -> 68 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check ...` -> passed for touched Phase 7 Python files
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check ...` -> passed for touched Phase 7 Python files
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/aios_cli.py services/standards_health.py services/workflow_orchestration.py` -> 0 errors
- `UV_CACHE_DIR=/tmp/uv-cache uv run vulture services/aios_cli.py services/standards_health.py --min-confidence 70` -> no findings
- `cd aios-ui && pnpm lint` -> exit 0 with existing warnings outside this change
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -m services.aios_cli --json delta-explain --project nonexistent` -> parseable empty explanation payload
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -m services.aios_cli --json governance-audit` -> parseable payload with `recommended_workflows`

## Commits

- `d0e5abc6 feat(standards): cover phase 7 health domains`
- `774fd165 docs(planning): record phase 7 domain coverage`
- `c574641e feat(health): explain standards deltas`
- `92bf2978 docs(planning): record phase 7 delta explanations`
- `c0d6f9e6 feat(health): surface delta recommendations`
- `4851c50b docs(planning): record phase 7 recommendation surfaces`

## Follow-Up

- Cross-project ranking remains out of scope.
- Grounded-query integration remains deferred to Phase 10 operator surfaces.
