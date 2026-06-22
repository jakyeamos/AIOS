# Debug: divergent strategy validation accounting

## Symptoms
- Expected: `divergent_judge_panel` runs in the divergent-strategy validate stage and satisfies `required_validations`.
- Actual: `logs/control-plane/workflow-reports/invoke-managed-failed-workflow.json` marks the workflow failed with `Required validation did not run: divergent_judge_panel`.
- Evidence: the report's `judge_candidates` stage is `completed`, includes the `divergent_judge_panel` skill, and records success-criteria finding ids, while top-level `validations` is empty.

## Root Cause
`services/workflow_orchestration.py` builds required-validation accounting only from explicit validation rows emitted by `_execute_skill`. The divergent judge stage is a validate-stage skill with stage-level success-criteria evaluation, so a completed judge execution produces stage findings but no validation row.

## Fix Strategy
Keep explicit validation rows authoritative, then credit required validation keys from completed skills on validate stages when the stage evaluation outcome is not failed or blocked.
