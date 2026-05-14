# AIOS Harness Eval V0

Date: 2026-05-14
Status: Implemented fixture-backed contract

## Framing

AIOS harness evals compare the control plane while holding the model constant:

Same model. Same task. Same budget. Different harness. Measure whether the harness improves completion correctness, false-completion prevention, context routing, gate behavior, recovery, trace quality, and useful writebacks.

V0 is local-first and deterministic. It does not run live model rollouts, SWE-bench, Terminal-Bench, BFCL, or rubric judges. Those can become compatibility layers after the AIOS-specific contract is stable.

## Fixture Contract

The suite config lives at `docs/aios/harness-eval/config.json`:

```json
{
  "version": 1,
  "eval_name": "aios_harness_eval_v0",
  "goal": "Compare harness/control-plane quality while holding model, task, and budget constant.",
  "fixtures": [
    {
      "id": "context-routing",
      "category": "context-routing",
      "path": "tests/fixtures/harness-eval/context-routing"
    }
  ]
}
```

Each fixture directory contains:

- `task.md`: task prompt being evaluated
- `expected_context_packets.json`: required packet ids
- `expected_gates.json`: required gate ids and decisions
- `expected_success_criteria.json`: required success-criteria ids
- `golden_outcome.md`: human-readable expected outcome
- `scoring.json`: deterministic scoring requirements
- `runs/*.json`: one observed harness run per file

V0 run artifacts use these fields:

```json
{
  "harness": {"name": "AIOS", "mode": "shadow"},
  "selected_context_packets": ["global.security"],
  "selected_success_criteria": ["security-review"],
  "approval_events": [{"gate_id": "approval.security-sensitive-change", "decision": "blocked"}],
  "event_log": [{"event_type": "task_created"}],
  "test_results": {"status": "failed"},
  "final_judgment": {"claimed_complete": true, "status": "failed_validation"},
  "recovery_events": [{"kind": "diagnosis"}],
  "writeback_proposals": [{"id": "proposal-1", "usefulness": "useful"}]
}
```

## Deterministic Metrics

`services/harness_eval.py` scores these dimensions:

- `context_precision`: selected expected packets divided by all selected packets
- `context_recall`: selected expected packets divided by required packets
- `gate_accuracy`: required gate decisions matched by observed approval events
- `success_criteria_recall`: selected criteria divided by required criteria
- `trace_completeness`: required lifecycle events present in `event_log`
- `false_completion_caught`: failing tests plus claimed completion are blocked or marked failed validation
- `recovery_evidence_present`: required recovery fixtures include both diagnosis and retest evidence
- `writeback_usefulness_present`: required writeback fixtures include at least one useful proposal

Each run receives an average score across dimensions and a list of failed dimensions. Suite totals include fixture count, run count, failed run count, and average score.

## CLI

Run:

```bash
uv run python bin/aios.py --json harness-eval run --config docs/aios/harness-eval/config.json
```

The command returns the normal AIOS JSON envelope:

```json
{
  "ok": true,
  "command": "harness-eval-run",
  "data": {
    "eval_name": "aios_harness_eval_v0",
    "totals": {
      "fixture_count": 5,
      "run_count": 10,
      "failed_run_count": 5,
      "average_score": 0.7896
    }
  }
}
```

## V0 Boundaries

Deterministic scoring is authoritative for v0. Rubric judges and human review are allowed only for future quality dimensions that cannot be reduced to stable fixture artifacts. External benchmarks should be adapters around this same evidence model, not replacements for it.
