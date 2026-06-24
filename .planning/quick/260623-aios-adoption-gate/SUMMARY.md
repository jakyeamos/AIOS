# AIOS Adoption Gate Summary

Date: 2026-06-23

## Result

PASS.

`scripts/aios-adoption-gate.py` copies the live AIOS database and runs three managed-runtime pilots:

- AIOS internal bugfix.
- Non-AIOS `amos-saas` bugfix.
- AIOS operator UI verification.

Each pilot selected `implementation-delivery`, completed the managed runtime, closed run/invocation/session lifecycle state with explicit linkage, emitted workflow/evaluation/writeback/TMCP artifacts, returned a route-decision operator-search hit, and replayed through the daily-flow trace.

## Evidence

- `.planning/quick/260623-aios-adoption-gate/adoption-gate-report.json`
- `.planning/quick/260623-aios-adoption-gate/adoption-gate-report.md`

## Verification

```bash
uv run ruff check scripts/aios-adoption-gate.py services/daily_flow.py tests/test_daily_flow.py
uv run pytest -q tests/test_daily_flow.py::test_replay_finds_evaluation_through_canonical_schema tests/test_aios_cli.py::test_daily_flow_replay_cli
python3 scripts/aios-adoption-gate.py --db-copy /tmp/aios-adoption-gate.db
```

