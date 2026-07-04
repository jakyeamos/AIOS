# AIOS Complexity + Simplification Backfill

**Generated:** 2026-06-23  
**Mode:** observation-backed inventory, no remediation

This inventory complements `docs/backfill/agent-eval-backfill.md`. The older backfill focuses on file-size, dead-code, import-violation, and shellcheck metrics. This document records algorithmic complexity and simplification findings using `docs/quality/complexity-simplification-gate.md`.

## Commands Run

```bash
pnpm quality:eval
```

Observed summary:

- Python files over 500 lines: 67
- Test files with no assertions: 2 (`tests/context/__init__.py`, `tests/memory/__init__.py`)
- `services/` imports from `bin/`: 0
- TypeScript component files over 400 lines: 3
- Vulture findings at min confidence 80: 0
- Shellcheck files with findings: 2 (`bin/takeout-ingest.sh`, `bin/weekly-maintenance.sh`)

Additional inspection commands:

- `find services bin tests ... | wc -l`
  - `services`: 92 Python files
  - `bin`: 87 top-level files
  - `tests`: 71 top-level files
- `wc -l` sampling found the largest AIOS files: `services/aios_cli.py` at 5517 lines, `tests/test_aios_cli.py` at 3665 lines, `services/standards_health.py` at 2334 lines, and `services/skills_harvest.py` at 2218 lines.
- UI sampling found largest TypeScript surfaces: `aios-ui/server/aios/knowledge.ts` at 1446 lines, `aios-ui/server/aios/runtime.ts` at 1323 lines, and `aios-ui/components/control/ControlPlaneStudio.tsx` at 686 lines.

## Area 1: Python Services

### Scope Reviewed

- `services/aios_cli.py`
- `services/standards_health.py`
- `services/success_criteria.py`
- `services/workflow_orchestration.py` through quality-eval size evidence

### Hotspot: Monolithic AIOS CLI command surface

- File(s): `services/aios_cli.py:1`
- Category: simplification
- Criteria: `simplicity`, `architecture-boundary`, `agent-claim-verification`
- Severity: high
- Confidence: high
- Current issue: `services/aios_cli.py` is 5517 lines and imports many unrelated service domains at module load, including routing, evals, skills, shadow branches, quality gates, workflow promotion, and standards health.
- Why it matters: the CLI file is a coordination hub for many subsystems, so new commands are likely to accumulate in one module instead of routing through smaller command groups.
- Suggested remediation: split by command family into focused modules while preserving the current CLI entry contract.
- Behavior risk: high
- Tests/benchmarks needed: targeted CLI JSON-path tests plus smoke tests for command groups moved out of the file.
- Agent-safe?: partial

### Hotspot: Standards health combines schema, registry loading, scoring, and backfill logic

- File(s): `services/standards_health.py:238`, `services/standards_health.py:571`, `services/standards_health.py:645`
- Category: simplification
- Criteria: `simplicity`, `data-integrity`, `architecture-boundary`
- Severity: medium
- Confidence: high
- Current issue: one 2334-line module owns schema creation, registry persistence, project binding, status maps, and scoring-related helpers.
- Why it matters: schema and scoring changes have different risk profiles but currently share a large module surface.
- Suggested remediation: extract schema/persistence helpers from scoring and explanation code after adding focused regression tests.
- Behavior risk: medium
- Tests/benchmarks needed: standards schema idempotency tests, registry seed tests, and delta explanation tests.
- Agent-safe?: partial

### Hotspot: Success criteria evaluator has broad trigger heuristics in one file

- File(s): `services/success_criteria.py:21`, `services/success_criteria.py:119`
- Category: simplification
- Criteria: `simplicity`, `agent-claim-verification`, `test-quality`
- Severity: medium
- Confidence: medium
- Current issue: marker sets, registry loading, schema, criterion resolution, and finding persistence are colocated in a 1671-line evaluator module.
- Why it matters: adding a criterion can require touching broad shared logic, increasing risk of unrelated trigger regressions.
- Suggested remediation: separate criterion trigger routing from persistence/evaluation records once current criterion tests cover the split.
- Behavior risk: medium
- Tests/benchmarks needed: trigger routing fixtures for UI, DB, API, dependency, complexity, and security diffs.
- Agent-safe?: partial

## Area 2: CLI / Bin Scripts

### Scope Reviewed

- `bin/import_ai_history.py`
- `bin/hook-stop.py`
- quality-eval size and shellcheck output across `bin/`

### Hotspot: History importer repeats parser-normalizer structure per provider

- File(s): `bin/import_ai_history.py:241`, `bin/import_ai_history.py:509`, `bin/import_ai_history.py:617`
- Category: simplification
- Criteria: `simplicity`, `data-integrity`, `test-quality`
- Severity: medium
- Confidence: high
- Current issue: ChatGPT, Claude export, and Claude Code parsing follow similar normalize/sort/extract/score flows with provider-specific details embedded inline.
- Why it matters: provider additions can duplicate flow control and make behavior drift likely.
- Suggested remediation: keep current behavior but extract a narrow provider-normalization seam after provider regression tests are locked.
- Behavior risk: medium
- Tests/benchmarks needed: existing import history tests plus fixture tests for provider-specific edge cases.
- Agent-safe?: partial

### Hotspot: Stop hook mixes closeout, learning, standards, git status, and writeback concerns

- File(s): `bin/hook-stop.py:45`, `bin/hook-stop.py:90`, `bin/hook-stop.py:124`, `bin/hook-stop.py:145`
- Category: architecture
- Criteria: `architecture-boundary`, `simplicity`, `agent-claim-verification`
- Severity: high
- Confidence: high
- Current issue: the hook imports runtime functions, success criteria, standards health, RTK, session effectiveness, git status, closeout classification, and learning signal emission in one 1211-line script.
- Why it matters: hook-stop is a critical lifecycle boundary; broad responsibilities make failures harder to isolate and test.
- Suggested remediation: extract closeout learning, git status, and standards/evaluation adapters into services while keeping the hook as a thin orchestrator.
- Behavior risk: high
- Tests/benchmarks needed: hook payload fixture tests and end-to-end closeout smoke tests.
- Agent-safe?: no

## Area 3: aios-ui

### Scope Reviewed

- `aios-ui/components/control/ControlPlaneStudio.tsx`
- `aios-ui/components/projects/TaskiProjectSurface.tsx`
- quality-eval output for `aios-ui/components`
- line-count sampling for `aios-ui/server/aios/*`

### Hotspot: ControlPlaneStudio mixes routing, mutation wiring, review queues, run detail, and findings

- File(s): `aios-ui/components/control/ControlPlaneStudio.tsx:47`, `aios-ui/components/control/ControlPlaneStudio.tsx:71`, `aios-ui/components/control/ControlPlaneStudio.tsx:220`, `aios-ui/components/control/ControlPlaneStudio.tsx:527`
- Category: render performance
- Criteria: `thin-display`, `performance-budget`, `simplicity`
- Severity: medium
- Confidence: high
- Current issue: a 686-line client component owns many local state fields, tRPC mutations, task routing forms, workflow/backend registry display, writeback review, run detail, lifecycle events, and evaluator finding controls.
- Why it matters: client-side changes to one sub-surface can affect render behavior and state interactions across unrelated panels.
- Suggested remediation: split into focused child components for planning, writebacks, packet ledger, and run detail; keep data ownership explicit.
- Behavior risk: medium
- Tests/benchmarks needed: UI smoke tests or component-level interaction tests for planning and writeback review.
- Agent-safe?: partial

### Hotspot: TaskiProjectSurface combines project scope controls with multiple dashboard panels

- File(s): `aios-ui/components/projects/TaskiProjectSurface.tsx:44`, `aios-ui/components/projects/TaskiProjectSurface.tsx:74`, `aios-ui/components/projects/TaskiProjectSurface.tsx:120`
- Category: simplification
- Criteria: `thin-display`, `simplicity`, `test-quality`
- Severity: medium
- Confidence: medium
- Current issue: the 540-line component owns tab state, component enablement state, mutations, scope controls, summary panels, standards health, pipeline status, learning writebacks, and active runs.
- Why it matters: the component is a dense operational surface where display, mutation, and data-derived status logic are intertwined.
- Suggested remediation: split stable panels after adding basic route/component smoke coverage.
- Behavior risk: medium
- Tests/benchmarks needed: route smoke for the project surface and mutation-state interaction tests.
- Agent-safe?: partial

### Needs Deeper Audit

- `aios-ui/server/aios/knowledge.ts`
- `aios-ui/server/aios/runtime.ts`
- `aios-ui/server/aios/topic-graph.ts`
- `aios-ui/server/routers/insights.ts`

These are large server-side TypeScript files and need a focused data-access/query audit before remediation.

## Area 4: Config / Standards

### Scope Reviewed

- `config/success-criteria/registry.json`
- `config/quality-gates.json`
- `config/agent-rules.md`
- related docs under `spec/success-criteria/`

### Finding

No major complexity hotspots found in this area on this pass. The main risk is governance drift rather than algorithmic complexity: new rules must preserve Rule 11's always-loaded-vs-intent-specific decision.

### Test Gaps

- A future check could assert that agent-rule additions include a placement rationale or pointer target, but this is not yet automated.

## Area 5: Tests

### Scope Reviewed

- `tests/test_aios_cli.py`
- `tests/test_orchestration_runtime.py`
- `tests/test_workflow_orchestration.py`
- quality-eval assertion scan

### Hotspot: CLI regression tests mirror monolithic CLI breadth

- File(s): `tests/test_aios_cli.py:1`
- Category: test gap
- Criteria: `test-quality`, `simplicity`, `agent-claim-verification`
- Severity: medium
- Confidence: high
- Current issue: `tests/test_aios_cli.py` is 3665 lines, mirroring the breadth of `services/aios_cli.py`.
- Why it matters: the test file is a useful safety net, but its size makes it harder to identify which command families are covered before extracting CLI modules.
- Suggested remediation: split tests by command family as CLI modules are extracted, preserving existing assertions.
- Behavior risk: medium
- Tests/benchmarks needed: no new broad test type; reorganize only alongside CLI extraction.
- Agent-safe?: partial

### Test Files With No Assertions

- `tests/context/__init__.py`
- `tests/memory/__init__.py`

These are package marker files, so the quality-eval finding is informational rather than a remediation target.

## Remediation Order

1. P0: `bin/hook-stop.py` closeout responsibility split, after adding lifecycle fixture tests.
2. P0: `services/aios_cli.py` command-family extraction, one family at a time.
3. P1: `services/standards_health.py` schema/persistence split.
4. P1: `ControlPlaneStudio.tsx` panel extraction with smoke coverage.
5. P1: `bin/import_ai_history.py` provider-normalization seam.
6. P2: `TaskiProjectSurface.tsx` panel extraction.
7. P2: `tests/test_aios_cli.py` test-family split after CLI extraction begins.

## Cross-Project Summary

| Project | Backfill Doc | Audit Date | P0 | P1 | P2 |
|---------|--------------|------------|----|----|----|
| soundscape-app | `/Users/jakyeamos/projects/soundscape-app/docs/complexity-simplification-backfill.md` | 2026-06-23 | 0 | 3 | 2 |
| portfolio | `/Users/jakyeamos/projects/portfolio/docs/complexity-simplification-backfill.md` | 2026-06-23 | 0 | 2 | 1 |
| BidCamp (formerly amos-saas) | `/Users/jakyeamos/projects/BidCamp/docs/complexity-simplification-backfill.md` | 2026-06-23 | 0 | 3 | 2 |
| tm | `/Users/jakyeamos/projects/tm/docs/complexity-simplification-backfill.md` | 2026-06-23 | 0 | 2 | 3 |
| Terrace | `/Users/jakyeamos/projects/Terrace/docs/complexity-simplification-backfill.md` | 2026-06-23 | 3 | 2 | 1 |

Notes:

- `amos-saas` has been renamed to `BidCamp`; the live BidCamp repository is the authoritative source for that backfill.
- P0/P1/P2 counts are based on explicit hotspot headings in each project backfill doc.
- Terrace P0 items are elevated because Terrace is the framework layer for agent workflow execution.

## Needs Deeper Audit

- `services/skills_harvest.py`
- `services/workflow_orchestration.py`
- `services/tmcp_benchmark.py`
- `services/tmcp_runtime.py`
- `aios-ui/server/aios/knowledge.ts`
- `aios-ui/server/aios/runtime.ts`
- `aios-ui/server/aios/topic-graph.ts`

These files are large enough to require focused follow-up audits before safe remediation.

## Definition Of Done For Quality Standard

- Complexity+Simplification Gate runs after all large-work triggers.
- All hotspots in this doc are resolved or explicitly deferred with rationale.
- No new O(n^2) patterns are added to hot paths without recorded justification.
- All services over 500 lines are reviewed for extraction opportunities.
