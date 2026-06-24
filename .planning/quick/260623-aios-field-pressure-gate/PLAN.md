# AIOS Field Pressure Gate Plan

## Goal

Stress AIOS beyond the initial adoption gate by simulating daily usage pressure, operator inspection, artifact hygiene, learning/writeback compounding, and failure recovery on a copied live database.

## Scope

- Route a mixed set of representative AIOS and non-AIOS objectives.
- Execute a managed-runtime subset through the real runtime path.
- Verify closeout artifacts for every managed pilot.
- Probe operator-facing search, daily-flow, and next-action surfaces for drill-downable evidence.
- Run operator UI lint/typecheck as a cheap friction and type-safety proxy.
- Simulate second-brain/session-save learning through context-loop replay and governed writeback proposals.
- Exercise failure recovery for ambiguous objectives, invalid projects, missing runs, stale schema, and missing managed-runtime preflight.
- Ensure managed-runtime logs are treated as runtime artifacts instead of source changes, and classify the remaining dirty tree into source changes versus ignored runtime artifacts.

## Acceptance

- `scripts/aios-field-pressure-gate.py --db-copy /tmp/aios-field-pressure.db --managed-limit 6` exits `0`.
- The generated report scores `100/100`.
- Runtime log artifact directories are ignored by Git.
- Operator search can find run-linked writebacks and canonical evaluation findings by run id.
- Missing managed-runtime runs fail with structured preflight JSON instead of a traceback.
