# AIOS Native Command Pack Audit

Date: 2026-06-23

## Purpose

This audit grounds Phase 19 native workflow commands in existing AIOS architecture. The goal is not to clone an external essentials plugin. The goal is to add small AIOS-native commands that reuse current workflow, skill, prompt, routing, evidence, and eval surfaces.

## Current Architecture

### CLI Commands

The primary command surface is `services/aios_cli.py`, reached through `bin/aios.py`. It already hosts many JSON-first subcommands for status, metadata, workflow audit, gates, evals, shadows, peer traces, ablations, corpus runs, standards, DX pack inspection, and meta-learning session analysis.

Native workflow commands should eventually live here, but current local work has unrelated dirty `context-loops` CLI edits. New command implementation should therefore land in small service modules first and wire into `services/aios_cli.py` only in clean, reviewable hunks.

### Skills

Workflow skill metadata lives in `config/workflows/skills.json` and is loaded by `services.workflow_orchestration`. Prior Phase 15 work also created global agent-facing skills such as `handoff`, `prototype`, `diagnose`, `simplifier`, and `to-issues`.

Native commands should not duplicate those skills. Commands should call reusable services and may point agents to existing skills when a task needs richer interactive behavior.

### Prompts

Prompt templates are registered in `prompts/registry.json` and grouped into prompt families such as recovery, reasoning, research, implementation, and mature repo rehabilitation. Prompt selection already connects to workflow family routing in `services.workflow_orchestration`.

Native commands should use existing prompt families only when they need LLM synthesis. Read-only deterministic orientation commands should prefer structured repo inspection first.

### Workflows

Workflow contracts live in `config/workflows/registry.json` and are validated by `services.workflow_orchestration`. The registry supports stage specs, required skills, prompt bindings, criteria, required evidence, verifier expectations, approval gates, and lifecycle state.

Native commands should remain command-sized unless they need multi-stage governance. Heavy flows should become workflow registry entries rather than ad hoc CLI branches.

### Agents, Sub-Agents, And Model Routing

Model and sub-agent routing live in `config/execution-strategies/model-routing-policy.json` and `services.execution_strategy`. The policy already models model tiers, agent roles, sub-agent preference, and model-selection records.

Commands such as `squad-review` should represent reviewer lanes as structured output first. Later, those lanes can map to sub-agent roles through the execution strategy layer.

### Second-Brain And Context Retrieval

AIOS context selection is file-backed under `aios/context/`, with receipts in `aios/context/receipts/`. Session and second-brain ingestion surfaces exist, but Phase 19 commands should work repo-locally without private second-brain context. Second-brain retrieval should be optional and explicitly labeled when used.

### Eval Harnesses

Evaluation and shadow infrastructure already exists in Phase 11 services and CLI surfaces, including eval runs, gold-set recall, shadow branch comparison, and peer trace metadata. Phase 18 adds proposal-specific shadow eval plan generation. Native commands should log command metadata in a later plan so eval/shadow comparisons can measure command usefulness.

## Candidate Fit Analysis

| Command | Repo fit | Target surface | Dependencies | AIOS reuse | Complexity | Risk | Expected ROI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `zoom-out` | High | `aios zoom-out` read-only CLI plus service | file tree, imports, context receipts | context compiler, CTS later | Low/medium | Low | High context-efficiency gain |
| `handoff` | High | `aios handoff` service + optional artifact write | git status, changed files, tests, existing handoff store | Phase 15 handoff concepts, session effectiveness | Medium | Low/medium if writing artifacts | High continuity gain |
| `squad-review` | High | `aios review squad` read-only CLI | diff/file scope, reviewer lane schema | standards, success criteria, execution strategy roles | Medium | Low if read-only | High review-quality gain |
| `security-audit` | High | `aios audit security` read-only CLI | diff/file scope, security criteria | success criteria security-review, DX security reviewer | Medium | Low if read-only | High for risky diffs |
| `de-slopify` | Medium | `aios cleanup de-slopify` guarded modifying CLI | plan generation, patching, checks | quality gates, simplification docs | High | Medium/high | Useful but must be guarded |
| `prototype` | Medium | `aios prototype` sandboxed writer | explicit sandbox path, cleanup policy | Phase 15 prototype skill | Medium | Medium | Useful for exploration |
| `codebase-rehab` | Medium/low | workflow, not small command | maturity detection, multi-phase plan, tests | behavioral spec loop, DX pack | High | High | High only for mature repos |
| `codebase-sweep` | Low as default | defer; maybe explicit audit workflow | broad repo traversal, many gates | quality eval, architecture audits | Very high | High | Too broad for default behavior |

## Safety Analysis

### Read-Only By Default

- `zoom-out`
- `squad-review`
- `security-audit`
- `codebase-rehab` as an audit/plan only
- `codebase-sweep` only as a read-only inventory if ever implemented

### Modifying Or Artifact-Writing

- `handoff` may write a continuation artifact or DB record.
- `de-slopify` modifies code only after a cleanup plan, explicit scope, and checks.
- `prototype` writes only to explicit prototype/sandbox locations.

### Confirmation Required

- Any command that writes files, updates DB rows, stages commits, applies patches, installs packages, changes permissions, or runs network/deploy operations.
- `de-slopify` before applying changes.
- `prototype` before writing outside a declared sandbox root.

### Shadow Branch Required

- `de-slopify` for cross-file or behavior-risk cleanup.
- `codebase-rehab` before any implementation path.
- Any future `codebase-sweep` implementation that proposes broad edits.

### Test Gates

- Read-only commands need schema and snapshot-style output tests.
- Modifying commands need before/after tests, command discovery, lint/type/test gates when available, and rollback instructions.
- Security-related commands need non-issue coverage so output is not only a list of guesses.

## MVP Implementation Order

1. `zoom-out`: read-only, high ROI, low blast radius, clear structured output.
2. `handoff`: continuity value is high; start read-only preview, then optional artifact write.
3. `squad-review`: high review value; implement lane schema before sub-agent orchestration.
4. `security-audit`: read-only and criteria-backed, but better after squad lane schema exists.
5. `de-slopify`: guarded modifying command after command contracts and logging exist.
6. `prototype`: sandboxed writer after explicit prototype root policy exists.
7. `codebase-rehab`: workflow candidate, not MVP command.
8. `codebase-sweep`: explicitly deferred as default behavior.

This matches current repo evidence: the first core should be `zoom-out`, `handoff`, and `squad-review`.

## Deferred Commands And Rationale

`codebase-sweep` is deferred as default behavior because it invites broad repo traversal, broad findings, and broad edits. AIOS already has targeted audits, quality eval, standards health, and workflow routing. A sweep command would be too easy to use as a substitute for scoped context selection and governed workflows.

`codebase-rehab` should be a mature-repo workflow, not a small command. AIOS already has maturity detection and behavioral-spec verification concepts that better match this shape.

## Test And Logging Plan

- Add command contract fixtures with name, safety class, input schema, output schema, write behavior, confirmation requirements, and validation gates.
- Test registration without requiring second-brain context.
- Test read-only commands do not write files.
- Test modifying commands refuse without explicit confirmation and target scope.
- Log command metadata later with command name, safety class, input scope, files inspected, files written, checks run, model/sub-agent use, second-brain use, duration proxy, and outcome.
- Connect command metadata to eval/shadow comparison after MVP command behavior is stable.

## Target Placement Decisions

- `zoom-out`: service module plus `aios zoom-out`.
- `handoff`: service module reusing handoff concepts, then `aios handoff`.
- `squad-review`: service module with reviewer lane schema, then `aios review squad`.
- `security-audit`: service module, then `aios audit security`.
- `de-slopify`: guarded cleanup service, then `aios cleanup de-slopify`.
- `prototype`: sandbox service, then `aios prototype`.
- `codebase-rehab`: workflow registry candidate, not command MVP.
- `codebase-sweep`: deferred; no default command.
