# Phase 18 Plan 18-02 Summary: Session Signal Extractor

Completed: 2026-06-23

## Outcome

AIOS now has a lightweight meta-learning signal extractor for structured/mock session traces.

## Artifacts

- `services/meta_learning_signals.py`
  - Defines normalized `MetaLearningSignal` records with `signal_id`, `type`, `summary`, `evidence`, `source_sessions`, `frequency`, `recency`, `confidence_points`, `recommended_target_layer`, and `risk_level`.
  - Detects explicit corrections such as `don't`, `always`, `never`, `from now on`, and `in this repo`.
  - Aggregates repeated corrections, repeated approvals, repeated manual commands, repeated failed tool loops, context misses, second-brain misses, irrelevant loaded context, model mismatches, scope restatements, and contradictions.
  - Generates stable IDs for the same signal input.
- `services/aios_cli.py`
  - Adds read-only `aios meta analyze-session --input <json>` for extracting normalized signals from a JSON session trace.
- `tests/test_meta_learning_signals.py`
  - Covers correction extraction, repeated pattern aggregation, approval, command repetition, tool friction, context miss, model mismatch, scope restatement, contradiction extraction, stable IDs, and CLI payload consumption.

## Requirement Coverage

- META-02 is complete.

## Verification

- `uv run pytest -q tests/test_meta_learning_signals.py` -> 6 passed
- `uv run ruff check services/meta_learning_signals.py tests/test_meta_learning_signals.py services/aios_cli.py` -> passed
- `uv run python bin/aios.py --json meta analyze-session --input /private/tmp/meta-session.json` -> returned two normalized signals for the smoke trace
- `pnpm context:validate` -> passed
- `pnpm quality:eval` -> passed with existing repository hotspot inventory; new relevant finding recorded below

## Design Notes

- No database schema was added. The extractor accepts local JSON traces first, matching the Plan 18-02 scope.
- The extractor proposes target layers such as `project_rule`, `command_suggestion`, `workflow_rule`, `context_packet_or_retrieval_policy`, `model_routing_policy`, `skill_or_agent_suggestion`, `observe_only`, and `manual_review`; it does not mutate those targets.

## Complexity + Simplification Gate

### Hotspot: Signal extractor module size
- File(s): `services/meta_learning_signals.py`
- Category: simplification
- Severity: low
- Confidence: high
- Current issue: `pnpm quality:eval` reports the new module at 524 lines, slightly above the 500-line size threshold.
- Why it matters: Future phases may add scoring, routing, and proposal generation; keeping extraction helpers bounded will make those additions easier to review.
- Suggested remediation: After META-03 decides which helpers remain stable, split event normalization, signal detectors, and signal construction into smaller internal sections or modules if the file keeps growing.
- Behavior risk: medium if refactored immediately, because detector behavior and stable IDs are newly introduced.
- Tests/benchmarks needed: `uv run pytest -q tests/test_meta_learning_signals.py` and CLI smoke for `aios meta analyze-session`.
- Agent-safe?: partial; defer to a dedicated simplification pass after one more phase of API stabilization.

## Next Plan

Phase 18 Plan 18-03 adds confidence scoring, quality filtering, conflict detection, and target-layer routing.
