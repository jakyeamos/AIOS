# Durable Agent Workflows Eval

## Task Summary

- Date: 2026-06-24
- Repository: `/Users/jakyeamos/AIOS`
- Context profile: `jakye_repo_only`
- AIOS condition: local AIOS implementation run, not portable benchmark evidence

## Acceptance Criteria Check

- Explicit durable-agent-workflow model: passed via `aios/context/packets/workflow.durable-agent-workflows.md` and `docs/workflows/durable-agent-workflows.md`.
- Goals require verifiers and stopping conditions: passed via packet, docs, registry workflow, and `durable_goal_verifier`.
- Steering and queueing are distinct: passed via `/steer` and `/queue` docs plus `durable_workspace_state_keeper` invariants.
- Durable memory rules are explicit: passed in packet and docs.
- Artifact/source-of-truth guidance is explicit: passed in packet, docs, README, and summary artifact.
- Automation distinguishes fresh scheduled jobs from context-preserving workspace wakeups: passed in packet and docs.
- Skill extraction criteria are evidence-backed: passed in packet and docs.
- Existing gates preserved: passed by candidate-only workflow registration and registry validation.
- No no-op instruction bloat added: searched added durable surfaces for generic phrases; only existing rejected-term and vocabulary references matched.

## Checks Run

- `pnpm test:context -- --test-name-pattern "durable agent workflow"`: passed, 15 tests.
- `UV_CACHE_DIR=/private/tmp/uv-cache-aios-durable uv run pytest -q tests/test_planned_workflows.py`: passed, 10 tests.
- `UV_CACHE_DIR=/private/tmp/uv-cache-aios-durable uv run pytest -q tests/test_workflow_orchestration.py::test_registry_bindings_are_valid tests/test_workflow_orchestration.py::test_load_registry_normalizes_lifecycle_fields tests/test_workflow_orchestration.py::test_workflow_stage_gate_report_exposes_gate_metadata`: passed, 3 tests.
- `UV_CACHE_DIR=/private/tmp/uv-cache-aios-durable uv run pytest -q tests/test_workflow_orchestration.py tests/test_planned_workflows.py`: passed, 58 tests.
- `pnpm context:validate`: passed.
- `pnpm context:compile --task "Add durable agent workspaces with goal verifiers, steering, queueing, artifacts, automation, and memory rules"`: passed and selected `packets.workflow.durable-agent-workflows`.
- `python3 -m json.tool config/workflows/registry.json >/dev/null`: passed.
- `python3 -m json.tool config/workflows/skills.json >/dev/null`: passed.
- `git diff --check`: passed.
- `pnpm quality:eval`: passed with existing repo-wide findings.

## Complexity + Simplification Gate

- Gate A: no new algorithmic, query, render, or runtime hot path. The change is docs, config, and tests.
- Gate B: instruction-sprawl risk addressed by placing detailed guidance in a packet and workflow doc, keeping the domain standard thin, and keeping registry entries candidate-level.
- Gate C: verification commands above exercised context selection and workflow registry contracts.

Existing quality-eval findings were not introduced by this change: large existing Python files, assertionless package marker tests, large UI components, and shellcheck warnings in existing shell scripts.

## Residual Risks

- `durable-agent-workspace` is a candidate workflow only. Runtime automation and UI affordances for durable workspace wakeups are future work.
- Skill candidacy is documented and registered but not yet backed by repeated real-run evidence.
