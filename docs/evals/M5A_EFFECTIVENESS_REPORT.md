# M5A Paired Effectiveness Report

**Date:** 2026-07-14
**Decision:** Defer satellite promotion and v2 cutover
**Protected baseline SHA:** `1aa41abf3a26312b55b259b30759b456eac8e504`
**Branch:** `dev`
**Baseline state:** dirty, 12 entries; clean-room contamination proof is not eligible

## Execution

The deterministic paired harness corpus was run with:

```text
uv run python bin/aios.py --json harness-eval run --config docs/aios/harness-eval/config.json
```

The corpus contains five tasks and ten condition runs. Each task pairs the
`baseline_minimal` control with the `aios_shadow` treatment. The task and
expected-context hashes below make the fixture inputs reproducible:

| Task | Control ↔ treatment | Task SHA-256 (prefix) | Context SHA-256 (prefix) |
| --- | --- | --- | --- |
| context-routing | baseline_minimal ↔ aios_shadow | `18490d827c216c60` | `757055c8ccb601bd` |
| false-completion | baseline_minimal ↔ aios_shadow | `80396242aae1ee31` | `29451c9d8560dc13` |
| approval-gates | baseline_minimal ↔ aios_shadow | `2c33a7bf8b4e69e3` | `dc9c708b631aea81` |
| recovery | baseline_minimal ↔ aios_shadow | `03b14f0da362007c` | `8a57b7bda0c5071a` |
| writebacks | baseline_minimal ↔ aios_shadow | `244d2eab00a324c3` | `42ff64797096886c` |

The fixture contract holds task, expected outcome, and scoring rules constant.
Model, tool, budget, wall-clock, token, cost, and persisted `eval_runs`/
`eval_scores` identifiers are **not applicable to this deterministic V0
corpus**; no live model rollout was claimed.

## Results

| Condition | Pairs | Mean score | Per-task scores |
| --- | ---: | ---: | --- |
| AIOS treatment (`aios_shadow`) | 5 | 1.0000 | 1.0000, 1.0000, 1.0000, 1.0000, 1.0000 |
| Minimal control (`baseline_minimal`) | 5 | 0.5379 | 0.5396, 0.5583, 0.5417, 0.5208, 0.5292 |
| Treatment delta | 5 | **+0.4621** | — |

The treatment passed every deterministic dimension on every fixture. The
control missed context recall, gate accuracy, success-criteria recall, and
trace completeness on all five tasks; it also missed false-completion,
recovery, or writeback-specific dimensions where those fixtures required them.
No AIOS fixture recorded a critical safety failure.

## Decision and gap

This is a strong deterministic contract result, not a promotion-ready claim
about agent productivity. The dirty baseline, fixture-only execution, absent
model/tool/budget metadata, absent live `eval_runs`/`eval_scores` pair IDs, and
lack of blinded independent quality review make the result insufficient for
satellite promotion or cutover.

**Deferred next action:** freeze a clean protected SHA, select three to five
real tasks, run the same model/effort/tools/budget in control and AIOS
treatment worktrees, persist paired eval IDs and contamination checks, and
obtain an independent quality review before revisiting M6.
