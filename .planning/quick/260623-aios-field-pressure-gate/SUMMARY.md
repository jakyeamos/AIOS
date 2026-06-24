# AIOS Field Pressure Gate Summary

Date: 2026-06-23

## Result

PASS, 100/100.

`scripts/aios-field-pressure-gate.py` now tests the five remaining adoption concerns:

- Daily usage pressure: 12 simulated daily objectives routed correctly, with 6 managed-runtime pilots completed.
- Operator UX: required UI/server surface files exist, UI lint/typecheck exits cleanly, and operator-search/daily-flow/next-action return drill-downable evidence.
- Artifact hygiene: managed-runtime log directories are ignored by Git, and dirty-tree state is classified into source changes versus ignored runtime artifacts.
- Learning value: synthetic context-loop replay produced a learning candidate, and repeated session-save summaries produced governed memory plus skillification proposals.
- Failure recovery: ambiguous objectives block, invalid projects fail cleanly, missing-run daily-flow replay degrades with explicit missing provenance, stale-schema replay reports missing evidence without crashing, and missing managed-runtime runs fail with structured preflight JSON instead of a traceback.

The gate exposed and fixed an operator-search gap: run-id queries now find run-linked writebacks and canonical success-criteria findings.
It also tightened managed-runtime preflight errors so missing runs no longer produce a Python traceback.

## Evidence

- `.planning/quick/260623-aios-field-pressure-gate/field-pressure-report.json`
- `.planning/quick/260623-aios-field-pressure-gate/field-pressure-report.md`

## Verification

```bash
uv run pytest -q tests/test_operator_search.py tests/test_aios_cli.py::test_operator_search_cli_json tests/test_aios_cli.py::test_operator_search_cli_kinds_filter
uv run ruff check bin/aios-managed-run.py services/operator_search.py tests/test_operator_search.py scripts/aios-field-pressure-gate.py
pnpm --dir aios-ui lint
python3 scripts/aios-field-pressure-gate.py --db-copy /tmp/aios-field-pressure.db --managed-limit 6
```
