# 07-02 Summary: Delta Explanations And Health Workflow Recommendations

## Result

AIOS now projects standards-health snapshots into per-standard delta explanations and recommends workflows from health-state deltas without adding new persistence.

## Shipped

- Added `DeltaExplanation` in `services.standards_health`.
- Added `_classify_provenance`, `_findings_by_criterion`, `_detect_contradiction`, `build_explanation`, and `project_delta_explanations`.
- Added `HEALTH_TO_WORKFLOW_RULES` and `recommend_workflow_from_health` in `services.workflow_orchestration`.
- Included Phase 6 stage findings in contradiction aggregation when `orchestration_runs` is available.
- Added tests for four-state provenance, 14-day finding freshness, contradiction detection, explanation projection, workflow recommendation rules, registry availability, approval metadata, uniqueness, and trigger metadata.

## Files Modified

- `services/standards_health.py` - 2252 lines
- `services/workflow_orchestration.py` - 1188 lines
- `tests/test_standards_health.py` - 874 lines
- `tests/test_workflow_orchestration.py` - 443 lines

## Public API Surface

- `services.standards_health.DeltaExplanation`
- `services.standards_health.build_explanation()`
- `services.standards_health.project_delta_explanations()`
- `services.workflow_orchestration.HEALTH_TO_WORKFLOW_RULES`
- `services.workflow_orchestration.recommend_workflow_from_health()`

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_standards_health.py -x -q -k "provenance or contradiction or delta_explanations or build_explanation or findings_by_criterion"` -> 10 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_workflow_orchestration.py -x -q -k "recommend_workflow"` -> 9 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_standards_health.py tests/test_workflow_orchestration.py -q` -> 39 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/standards_health.py services/workflow_orchestration.py tests/test_standards_health.py tests/test_workflow_orchestration.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/standards_health.py services/workflow_orchestration.py tests/test_standards_health.py tests/test_workflow_orchestration.py` -> 4 files already formatted
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/standards_health.py services/workflow_orchestration.py` -> 0 errors
- `UV_CACHE_DIR=/tmp/uv-cache uv run vulture services/standards_health.py services/workflow_orchestration.py --min-confidence 70` -> no findings

## Notes

- No new SQLite tables were created; explanations and recommendations are read-time projections from existing health, assessment, delta, criteria-finding, and workflow registry rows.
- `_findings_by_criterion` filters to the most recent 14 days, preventing stale findings from creating false contradictions.
- Planned workflows such as `standards backfill`, `security review`, and `codebase architecture review` are returned with `available_in_registry: false` when absent from the workflow registry.
- The direct `Provenance` import from `services.capability_truth` remained clean; no shared fallback module was needed.
