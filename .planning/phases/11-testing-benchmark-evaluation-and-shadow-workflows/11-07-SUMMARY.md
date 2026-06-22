---
phase: 11-testing-benchmark-evaluation-and-shadow-workflows
plan: "07"
completed_at: "2026-06-21T00:00:00.000Z"
requirements:
  - EVAL-07
  - EVAL-08
key-files:
  created:
    - services/portable_context_packet_generator.py
    - services/external_benchmark_adapter.py
    - config/context-packets/.gitkeep
    - aios-ui/server/aios/eval-data.ts
    - aios-ui/server/routers/eval.ts
    - aios-ui/components/eval/EvalSummaryPanel.tsx
    - aios-ui/components/eval/ShadowCandidateQueue.tsx
    - tests/test_portable_context_packet_generator.py
    - tests/test_external_benchmark_adapter.py
  modified:
    - services/aios_cli.py
    - tests/test_aios_cli.py
    - aios-ui/server/routers/_app.ts
    - aios-ui/lib/control-plane.ts
    - aios-ui/app/page.tsx
    - aios-ui/app/projects/[id]/page.tsx
    - aios-ui/app/runs/[id]/page.tsx
metrics:
  focused_tests_passed: 52
  ui_routes_smoked: 3
---

# Phase 11 Plan 07 Summary

## Result

Completed the portable eval and external benchmark layer. AIOS can now generate privacy-filtered portable context packets, translate eval tasks into SWE-bench and Terminal-Bench shapes, normalize external harness results as `external_clean_room`, and expose packet/benchmark commands through `services.aios_cli`.

The operator UI now has eval data server projections, a tRPC eval router, collapsible eval summary and shadow candidate queue components, and embedded panels on the Command Center, project detail, and run detail surfaces. These paths degrade to null or empty arrays when eval tables are absent.

## Verification

- `uv run pytest -q tests/test_eval_run_service.py tests/test_second_brain_eval.py tests/test_shadow_branch_runner.py tests/test_ablation_runner.py tests/test_peer_trace.py tests/test_shadow_candidate_scorer.py tests/test_shadow_automation.py tests/test_portable_context_packet_generator.py tests/test_external_benchmark_adapter.py tests/test_aios_cli.py::test_packet_and_benchmark_cli_json_paths` passed: 52 tests.
- `uv run ruff check services/portable_context_packet_generator.py services/external_benchmark_adapter.py services/aios_cli.py tests/test_eval_run_service.py tests/test_portable_context_packet_generator.py tests/test_external_benchmark_adapter.py tests/test_aios_cli.py` passed.
- `uv run basedpyright services/portable_context_packet_generator.py services/external_benchmark_adapter.py tests/test_portable_context_packet_generator.py tests/test_external_benchmark_adapter.py` passed with 0 errors and one existing `pytest` import-resolution warning.
- `pnpm lint` in `aios-ui/` passed with 0 errors and the existing anti-slop warning baseline.
- `pnpm lint:architecture` in `aios-ui/` passed with no dependency violations.
- `pnpm context:validate` passed.
- Live Next route smoke returned HTTP 200 for `/`, `/projects/047ce7d77ad6a2f7`, and `/runs/managed-invoke-managed-prompt-capture-260604202353`.
- `git diff --check` passed for the Plan 11-07 changed files.

## Deviations from Plan

The UI server helpers follow the existing `aios-ui/server/aios/*` pattern by accepting the shared SQLite `db` connection from tRPC context instead of opening a connection internally. Browser-level screenshot verification was attempted, but the local Playwright browser was unavailable and system Chrome failed under sandbox control; route-level runtime smoke was completed through the live Next dev server.

## Self-Check: PASSED

All Plan 11-07 must-haves are present: portable packet generation, privacy filters, external benchmark adapters, external clean-room normalization, context packet directory tracking, eval UI projections, collapsible panels, command center/project/run page wiring, CLI subcommands, and focused tests.
