# 07-01 Summary: DELT-01 Domain Coverage

## Result

AIOS standards health now covers every DELT-01 domain and evaluates the five newly introduced domains honestly as `unknown` until local evidence or operator overrides exist.

## Shipped

- Bumped `config/standards/registry.json` profile version to `2026.06.0` while preserving `default_attached_version: 2026.04.0`.
- Added standards:
  - `maintainability.dead_code_signal` - domain `maintainability`, weight 5, severity 3
  - `ux.operator_clarity` - domain `ux`, weight 5, severity 3
  - `launch_readiness.deployable` - domain `launch_readiness`, weight 7, severity 4
  - `agent_readiness.handoff_packet` - domain `agent_readiness`, weight 6, severity 4
  - `standards_compliance.profile_attached` - domain `standards_compliance`, weight 4, severity 3
- Added evaluator branches for the five new standards.
- Added a direct `Provenance` import path from `services.capability_truth` into `services.standards_health`.
- Added tests for registry coverage, version pinning, required fields, evaluator defaults, briefing-packet evidence, profile/coverage scoring, ten-domain score output, and provenance importability.

## Files Modified

- `config/standards/registry.json` - 546 lines
- `services/standards_health.py` - 2001 lines
- `tests/test_standards_health.py` - 625 lines

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_standards_health.py -x -q -k "delt_01 or profile_version or new_standards or profile_domains or evaluator_returns_unknown or agent_readiness or standards_compliance or compute_score_emits_all_ten or provenance_import"` -> 10 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_standards_health.py -q` -> 13 passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/standards_health.py tests/test_standards_health.py` -> passed
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check services/standards_health.py tests/test_standards_health.py` -> 2 files already formatted
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/standards_health.py` -> 0 errors
- `UV_CACHE_DIR=/tmp/uv-cache uv run vulture services/standards_health.py --min-confidence 70` -> no findings
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -m json.tool config/standards/registry.json` -> valid JSON
- `UV_CACHE_DIR=/tmp/uv-cache uv run python -c "from services.standards_health import Provenance; from typing import get_args; assert set(get_args(Provenance)) == {'confirmed','inferred','missing','contradictory'}"` -> passed

## Notes

- Existing project scores remain protected by `default_attached_version: 2026.04.0`; the existing migration test confirms newer standards are `not_applicable` for older attached versions.
- The `agent_readiness.handoff_packet` evaluator tolerates older DBs without briefing packet criteria/standards columns by returning `unknown` instead of raising.
