# Workflow Promotion Runtime Evidence Summary

## Result

Managed governed workflow execution now writes stage findings through the real runtime path.

## Evidence

- Patched `bin/aios-managed-run.py` to pass the active SQLite connection into `execute_workflow`.
- Preserved workflow report persistence before failed workflow status raises, so comparison evidence is retained.
- Added managed-runtime regression coverage for `success_criteria_stage_findings`.
- Verified against `/Users/jakyeamos/AIOS/data/aios.db` with run `run-c4c089f6-80d9-410c-95f9-e32076fbf2f9`.
- Verified `workflow-compare --workflow-key implementation-delivery --since 1d` reads stage metrics.
- Verified `promote-asset --kind workflow --key implementation-delivery --to active` creates governed promotion evidence.
