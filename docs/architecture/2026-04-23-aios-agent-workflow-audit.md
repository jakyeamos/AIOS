# AIOS Agent Workflow Audit (Phase 0b Checkpoint)

Date: 2026-04-23  
Status: Audit complete, implementation paused at checkpoint

## 1. Executive Summary

### Verdict

AIOS already has strong control-plane primitives and enough JSON-capable scripts to support a deterministic workflow baseline, but the agent-facing interface is still fragmented and missing one authoritative metadata snapshot surface.

### Already strong

- Durable control-plane runtime with explicit run/session/invocation handshake and lifecycle events.
- SQLite-first operational state (`sessions`, `tool_events`, `orchestration_*`, `briefing_packets`).
- Several machine-friendly commands already exist (`aios-query.py`, `vault-search.py`, `cts-*`, `architecture-enforcement.py`).
- Clear storage contract in [docs/STORES.md](/Users/jakyeamos/AIOS/docs/STORES.md).

### Weak or missing

- No unified `aios <status|metadata|health|logs|recent-failures>` command family.
- No single-shot structured metadata snapshot covering system + project + workflow + skills + health.
- Exit-code semantics are inconsistent across scripts; hooks frequently swallow errors and return `0`.
- Log inspection is mostly file/DB scraping, not commandized agent surfaces.
- Skill/instruction refresh is manual and static (`sync-claude-md.sh` map), not linked to project bootstrap.

### What to copy from the target pattern set

- JSON-first command contracts for all core control-plane surfaces.
- One cheap metadata snapshot command before agent execution.
- Stable semantic exit-code taxonomy.
- Structured logs/failure query command for deterministic troubleshooting.
- Declarative skill/instruction registry with refresh/install surfaces.

### What explicitly not to copy

- Backend platform migration.
- MCP-first discovery for routine operations.
- High-ceremony orchestration layers that duplicate existing SQLite control-plane truth.

## 2. Current State Audit

### A. CLI / Command Surfaces

Issue A1  
Severity: high  
Why it matters: agents must discover and compose many scripts instead of calling one stable CLI.  
Concrete symptom: `bin/` has 54 Python scripts; only a subset are designed as stable agent APIs.  
Recommended fix: add unified `aios` CLI entrypoint with subcommands and shared JSON envelope.  
Expected payoff: lower startup thrash, easier automation, fewer brittle script-specific integrations.

Issue A2  
Severity: medium  
Why it matters: partial JSON support still leaves inconsistent behavior when switching commands.  
Concrete symptom: 31 scripts use `argparse`; 17 argparse scripts have no explicit JSON mode hint.  
Recommended fix: normalize `--json` contract and default machine envelope for control-plane commands.  
Expected payoff: deterministic parsing and less command-specific branching in agents.

Issue A3  
Severity: medium  
Why it matters: no standardized command naming for status/health/logs/metadata.  
Concrete symptom: `aios-query.py --status` exists, but no matching `metadata`, `logs`, `recent-failures` peers.  
Recommended fix: standard subcommand family under `aios`.  
Expected payoff: predictable API surface across all phases.

### B. Metadata Exposure / Snapshot

Issue B1  
Severity: critical  
Why it matters: missing snapshot forces agents to infer state from docs, hooks, schema, and multiple commands.  
Concrete symptom: no `aios metadata --json` equivalent today.  
Recommended fix: implement metadata snapshot aggregating project link, orchestration context, tools, skills, health, and recent failures.  
Expected payoff: major reduction in discovery tokens and initialization errors.

Issue B2  
Severity: high  
Why it matters: linked-project applicability is unclear without manual cross-checking files.  
Concrete symptom: project mappings exist across `projects` table, `project-name-map.json`, and architecture profiles, but no single surfaced view.  
Recommended fix: snapshot should expose normalized linked-project records and active profile bindings.  
Expected payoff: safer cross-project execution and fewer wrong-repo assumptions.

### C. Skills / Project-Linked Instructions

Issue C1  
Severity: high  
Why it matters: manual sync creates staleness and drift risk.  
Concrete symptom: [sync-claude-md.sh](/Users/jakyeamos/AIOS/bin/sync-claude-md.sh) is interactive/manual with hardcoded source map.  
Recommended fix: declarative instruction/skill registry and non-interactive refresh command with JSON report.  
Expected payoff: reliable, auditable skill/instruction freshness.

Issue C2  
Severity: medium  
Why it matters: bootstrap flow does not expose which instructions are active for a given run.  
Concrete symptom: hooks inject context, but no standardized “applied instructions/skills” output surface.  
Recommended fix: include applied instruction/skill set in metadata snapshot.  
Expected payoff: improves inspectability and reviewability.

### D. Error Handling / Exit Codes / Logs

Issue D1  
Severity: high  
Why it matters: ambiguous exit semantics complicate deterministic agent retries and triage logic.  
Concrete symptom: many scripts return generic `1`; hooks often return `0` even on parse/DB errors.  
Recommended fix: define shared exit-code taxonomy and use it in control-plane command surfaces.  
Expected payoff: reliable machine routing for retry/escalate/fail-fast behavior.

Issue D2  
Severity: high  
Why it matters: failures are stored but not exposed through a dedicated machine API.  
Concrete symptom: errors spread across `~/AIOS/logs/*.log`, `tool_events`, `bug_log` without one query command.  
Recommended fix: add `aios logs --json` and `aios recent-failures --json`.  
Expected payoff: faster debugging, less log scraping.

### E. Static Knowledge vs Live State

Issue E1  
Severity: medium  
Why it matters: architecture intent is documented, but bootstrap still relies on implicit script behavior.  
Concrete symptom: strong contracts in `docs/STORES.md`, but no single runtime surface proving current live state assumptions.  
Recommended fix: snapshot command should explicitly separate static config, execution surfaces, and live state.  
Expected payoff: safer agent planning and lower policy drift.

### F. MCP Dependence

Issue F1  
Severity: low  
Why it matters: routine tasks should not depend on deep tool discovery.  
Concrete symptom: current operational core is mostly local CLI/SQLite already; risk is future regression into discovery-first behavior.  
Recommended fix: codify CLI-first preference for routine status/metadata/log/failure checks.  
Expected payoff: predictable latency and lower complexity.

## 3. Delta From Ideal

### Current -> Target

1. Fragmented script surfaces -> unified `aios` command family with stable JSON envelopes.  
2. No metadata snapshot -> one-shot `aios metadata --json` preflight view.  
3. Inconsistent exits -> shared semantic exit code contract across core CLI commands.  
4. Ad hoc failure inspection -> structured `logs` and `recent-failures` queries.  
5. Manual instruction sync -> declarative skill/instruction registry + refresh commands.  
6. Multiple link-state sources -> canonical linked-project state view in metadata output.  
7. Implicit bootstrap context -> explicit, inspectable bootstrap payload schema.

### Shortest path

- First, create normalized command surfaces and metadata snapshot.
- Second, standardize exit/log contracts.
- Third, add instruction/skill registry automation.
- Fourth, retrofit existing scripts to call shared helpers incrementally.

## 4. Implementation Plan

### Phase 0: Quick Wins

Risk: low  
Expected impact: high

Files to change:
- `/Users/jakyeamos/AIOS/bin/aios.py` (new unified CLI entrypoint)
- `/Users/jakyeamos/AIOS/services/aios_cli_shared.py` (JSON envelope + error helpers)
- `/Users/jakyeamos/AIOS/tests/test_aios_cli_surfaces.py` (new)
- `/Users/jakyeamos/AIOS/docs/handoffs/2026-04-23-aios-agent-workflow-cli-handoff.md` (new)

Commands/scripts to add:
- `aios status --json`
- `aios health --json`
- `aios logs --json --last N`
- `aios recent-failures --json --last N`

Docs/skills to update:
- agent-facing usage section for command contracts.

Validation:
- smoke tests for each subcommand + envelope schema assertions.

### Phase 1: Core Structural Improvements

Risk: medium  
Expected impact: very high

Files to change:
- `/Users/jakyeamos/AIOS/bin/aios.py`
- `/Users/jakyeamos/AIOS/services/metadata_snapshot.py` (new)
- `/Users/jakyeamos/AIOS/services/exit_codes.py` (new)
- `/Users/jakyeamos/AIOS/tests/test_metadata_snapshot.py` (new)

Commands/scripts to add/standardize:
- `aios metadata --json`
- `aios project metadata --json` (optional scoped view)
- semantic exits (e.g. usage, missing-config, data-source-unavailable, runtime-failure)

Interfaces:
- snapshot schema including:
  - environment
  - linked project state
  - orchestration state
  - active enforcement profiles
  - instruction/skill pointers
  - health and recent failure summary

### Phase 2: Optional Enhancements

Risk: medium  
Expected impact: medium-high

Files to change:
- `/Users/jakyeamos/AIOS/config/skills-registry.json` (new)
- `/Users/jakyeamos/AIOS/bin/aios-skills.py` (new or subcommand integration)
- `/Users/jakyeamos/AIOS/bin/sync-claude-md.sh` (non-interactive mode integration)
- `/Users/jakyeamos/AIOS/tests/test_aios_skills_registry.py` (new)

Commands/scripts to add:
- `aios skills status --json`
- `aios skills refresh --json`

Focus:
- deterministic skill/instruction freshness checks for linked projects.

### Phase 3: Future / Watchlist

Risk: medium-high  
Expected impact: medium

Files to change:
- `/Users/jakyeamos/AIOS/aios-ui/*` (CLI-surface integration into control center)
- `/Users/jakyeamos/AIOS/docs/architecture/*` (governance docs)

Focus:
- UI consumption of standardized CLI metadata/failure surfaces.
- deprecation plan for direct script calls once `aios` surfaces are stable.

## HARD CHECKPOINT: AUDIT COMPLETE

### 1. Top 5 highest-leverage findings

1. Missing `metadata --json` snapshot is the biggest source of startup discovery thrash.
2. CLI fragmentation across many scripts is the largest reliability gap.
3. Exit-code inconsistency blocks deterministic retry/escalation behavior.
4. Failure/log inspection lacks a dedicated machine-facing command surface.
5. Skill/instruction refresh is manual and stale-prone.

### 2. Top 5 highest-confidence implementations

1. Add unified `aios` command family with JSON envelope.
2. Implement `aios metadata --json` with linked-project + runtime + health sections.
3. Add `aios logs --json` and `aios recent-failures --json`.
4. Introduce shared semantic exit-code constants and error payload format.
5. Add test suite for CLI contract stability.

### 3. Top 5 risky or uncertain changes that should not be rushed

1. Rewriting all existing scripts at once to new command framework.
2. Aggressively changing hook exit behavior without validating host expectations.
3. Auto-mutating external project instruction files without dry-run/report safeguards.
4. Collapsing all existing tool-specific outputs into one schema without migration period.
5. Introducing new persistent services when SQLite + scripts already satisfy current scope.

### 4. Exact implementation order recommended

1. Create shared CLI envelope + exit-code module.
2. Ship `aios status/health/logs/recent-failures` JSON surfaces.
3. Ship `aios metadata --json` snapshot with fixed schema.
4. Add tests and handoff docs for agent usage.
5. Add skills/instruction registry + refresh/status commands.
6. Incrementally migrate high-value existing scripts to shared helpers.

### 5. What I would do next if implementation proceeds

Implement Phase 0 and Phase 1 first in one controlled pass, validate command schemas with tests, then stop for a second gate before skills refresh automation.

Implementation is intentionally paused here per checkpoint requirement.
