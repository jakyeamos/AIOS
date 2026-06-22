# Workflow Promotion Runtime Evidence

## Task

Finish the in-progress workflow-promotion evidence path against the real AIOS runtime.

## Scope

- Patch the managed governed runtime path so workflow execution writes durable stage findings to `success_criteria_stage_findings`.
- Preserve `workflow_execution_reports` evidence for both completed and failed workflow executions so `workflow-compare` and workflow promotion candidates have real run data.
- Verify with one end-to-end governed run against `/Users/jakyeamos/AIOS/data/aios.db`.

## Validation

- Focused runtime tests for managed workflow report and stage findings persistence.
- Real `start-work` plus `bin/aios-managed-run.py` execution against the AIOS DB.
- `workflow-compare` and `promote-asset --kind workflow` read the generated evidence.
