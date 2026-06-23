# Execution-Symmetric Planning Eval

## Purpose

Evaluate whether execution-symmetric plans reduce executor ambiguity and rework without over-planning simple tasks.

The eval uses `services/planning_log.py` records plus downstream execution and validation outcomes. Routing is measured only as an input signal; plan quality is the target.

## Required Cases

| Case | Input | Expected Evidence |
| --- | --- | --- |
| Natural-language plan request | "Create an implementation plan for a bounded API change" | `workflow=aios`, `output_format=execution_symmetric_plan`, interface-contract and validation sections present |
| `/gsdplanphase` request | `/gsdplanphase 20` | `workflow=gsd`, `phase=plan`, `handoff_target=gsd`, `output_format=gsd_ready_plan` |
| Explicit planning-lens request | Request includes "use observability lens" | automatic lenses remain and requested lens is added |
| Audit-to-implementation prompt | "Turn the security audit findings into implementation fixes" | `source_invocation=audit_to_implementation_prompt`, rollback and validation strategy included |
| GSD handoff generation | GSD-ready phase planning | definition of done and handoff target are compatible with GSD execution |
| Simple non-overplanning | "Fix a typo in README" | only objective, safest next step, and validation are emitted |
| Complex rollback task | High-risk secret handling or migration change | rollback/recovery, escalation, failure modes, and validation strategy are present |

## Scoring Criteria

Each case is scored 0-2 for:

- executor readiness
- risk awareness
- validation coverage
- constraint preservation
- specificity
- token efficiency
- reduced rework
- lower clarification burden
- consistency
- handoff ease

Score `2` when the plan gives the executor concrete next actions and verification evidence without excess structure. Score `1` when the plan is directionally useful but misses a key field or adds unnecessary ambiguity. Score `0` when the plan is generic, over-planned for simple work, lacks validation, or omits a required safety/handoff constraint.

## Log Inputs

Planning log records should include:

- source invocation and raw invocation
- workflow and phase
- task type, complexity, and risk
- selected lenses
- validation depth and output format
- handoff target
- sub-agent and model strategy
- TMCP packet and receipt IDs, or an explicit bypass reason
- execution result, validation result, rework flag, and notes when available

## Pass Threshold

The eval passes when:

- every required case has a planning log or test fixture
- no simple case receives non-trivial plan sections
- every moderate, complex, or high-risk case has validation strategy and rollback/recovery
- every GSD case has GSD-ready output and handoff target
- every non-trivial managed-run case records TMCP packet and receipt IDs or an explicit bypass reason
- aggregate score is at least 16 out of 20 for the scoring criteria on representative cases

## Current Automated Coverage

- `tests/test_planning_workflow_detection.py` covers natural-language, `/gsdplanphase`, slash override, audit-to-implementation, generated implementation prompt, and CLI-shaped planning detection.
- `tests/test_planning_lenses.py` covers automatic lens selection, GSD phase lenses, manual lens supplementation, and high-risk required lenses.
- `tests/test_planning_skill_lenses.py` covers skill-as-planning-lens behavior and disallowed completed-work outputs.
- `tests/test_execution_symmetric_planner.py` covers simple non-overplanning, moderate executor-ready plans, explicit lens supplementation, audit-to-implementation planning, GSD-ready plan output, and high-risk rollback/escalation.
- `tests/test_planning_context.py` and `tests/test_planning_log.py` cover structured context, log serialization, comparison axes, TMCP default evidence, and explicit bypass metadata.
