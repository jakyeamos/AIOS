# Spec Execution Roadmap

**Date:** 2026-04-22
**Author:** jakyeamos

Already executed: AIOS UI (original), Code Topology Service

## Scope Clarification

AIOS is the orchestration layer for agents across all development projects. The phases below are not primarily about hardening this repository or `aios-ui` as isolated applications. They are about building global standards, workflow, evaluation, prompt, and governance infrastructure that AIOS can apply to every linked development project.

This repo is the implementation home and first self-check target. Use it to build and validate the control plane, but do not narrow phase scope to `aios-ui/` or repo-local checks unless the phase explicitly says it is a bootstrap slice. Every phase must answer two questions:

1. What global AIOS capability is being added for all agent-run development?
2. How is that capability proven against this repo and at least one representative linked project/profile when practical?

Partially executed before this roadmap:
- Anti-Slop ESLint is already wired into `aios-ui/` through `eslint-plugin-anti-slop`; Phase 1b is now an audit/ratchet pass, not a greenfield build.
- AIOS already has first-pass orchestration/control-plane primitives (`orchestration_runs`, invocation handshake, event trace, `/control`, managed local runtime). Phase 2a must audit and extend those primitives instead of duplicating them.

Everything below is remaining work, ordered by dependency.

---

## Dependency Graph

```
0a Architecture Enforcement
        │
        ▼
0b Agent Workflow CLI Audit + JSON Surfaces
        │
        ▼
0c Success Criteria System
        │
        ▼
1a Prompt Library Phase 1 ─────┐
1b Anti-Slop ESLint Ratchet ───┤
        │                      │
        └──────────┬───────────┘
                   ▼
       1c Improvement Engine Audit (audit only)
                   │
                   ▼
       2a Workflow Orchestration
                   │
                   ▼
       2b Prompt Library Phase 2
                   │
                   ▼
       3a UI Command Center MVP
                   │
                   ▼
       3b Standards Delta / Health
```

---

## Phase 0 — Structural Foundation
*Run serially unless a human explicitly assigns non-overlapping file ownership. These phases all touch shared AIOS scripts, docs, hooks, package checks, project registry metadata, and runtime contracts, so parallel execution is too conflict-prone without coordination.*

---

### 0a — Architecture Enforcement
**Spec:** [`2026-04-22-aios-architecture-enforcement.md`](2026-04-22-aios-architecture-enforcement.md)

**Requirements:**
- Build an AIOS-managed architecture enforcement system for linked development projects. The implementation should support project profiles/adapters instead of assuming this repository's layout is the universal target.
- Audit this repo as the control-plane implementation home and use `aios-ui/` as one bootstrap TypeScript/Next.js target, but also define how the same enforcement model applies to other linked repos such as `amos-saas`, `soundscape-app`, `Terrace`, and `portfolio`.
- Infer architectural layers and module boundaries per project profile, then implement machine-enforced rules using the strongest available tools for each stack: Dependency Cruiser/ESLint for TS/React, ruff/import checks for Python, and other adapters where warranted.
- Enforce global standards through per-project adapters: layering rules (UI cannot import infra internals), module boundary rules (no arbitrary cross-feature imports), directionality rules (dependencies flow inward), restricted import patterns, and cycle prevention.
- Wire checks into project-local package scripts/CI where available and expose them through AIOS metadata/status surfaces so agents know which checks apply before editing. Deliver an audit summary, rule configs/adapters, CI or command wiring, and a developer-facing doc explaining each rule and why it exists.

**Why first:** Sets the structural rules every subsequent agent-run build must follow across projects. Implementation work started before this risks encoding violations that become expensive to unwind.

**Execution guardrail:** Do not start 0a by installing or wiring tooling only inside `aios-ui/`. First define the AIOS project-profile/enforcement model, then use `aios-ui/` as one proof target for the TypeScript/Next.js adapter.

**Write ownership:** AIOS enforcement registry/profile docs, reusable rule adapters, project-local lint/dependency configs where used as proofs, package/CI check scripts, architecture enforcement docs. Do not modify agent CLI surfaces or success-criteria runtime hooks in this phase unless required to make checks discoverable.

---

### 0b — Agent Workflow CLI Audit
**Spec:** [`2026-04-22-aios-agent-workflow-audit.md`](2026-04-22-aios-agent-workflow-audit.md)

**Requirements:**
- Audit AIOS CLI surfaces, project-linking metadata, skill installation, error handling, and MCP dependency against agent-native patterns: JSON-first commands (`aios status --json`, `aios metadata --json`, project/profile metadata snapshots), single-shot structured metadata snapshots before agent execution, semantic exit codes, and structured logs agents can parse deterministically.
- Produce the required hard-checkpoint audit and pause. Implementation is a separate post-checkpoint step and must only proceed after the audit explicitly recommends the exact changes.
- After checkpoint clearance, implement the highest-leverage improvements: JSON-first command surfaces, a metadata snapshot command, improved skill install/refresh flow, standardized exit codes, and better log inspection.
- Deliver a handoff doc explaining what changed and how agents should use the new surfaces.

**Why first:** The JSON CLI surfaces and metadata snapshot command are consumed by Workflow Orchestration, the UI Command Center, the Improvement Engine, and agents working in linked projects. Nothing downstream should be built before these plumbing primitives exist.

**Write ownership:** CLI entrypoints, metadata snapshot schema, structured log/exit-code helpers, agent-facing handoff docs. Avoid changing architecture enforcement rules or success-criteria schemas except through explicit integration points.

---

### 0c — Success Criteria System
**Spec:** [`2026-04-22-aios-success-criteria-system.md`](2026-04-22-aios-success-criteria-system.md)
**Seed file:** [`../../../spec/success-criteria/testing-trust.md`](../../../spec/success-criteria/testing-trust.md)

**Requirements:**
- Turn AIOS-managed `spec/success-criteria/` files from passive documentation into a first-class control plane for agent quality across all projects. Audit all existing criteria files, fix naming/path inconsistencies, and produce a canonical `spec/success-criteria/index.md` that lists every criterion, its intent, when it applies, blocking vs advisory severity, and whether it is global, task-type, domain-specific, project-domain-specific, or skill-specific.
- Standardize all criteria files to a consistent schema (Intent / Applies When / Required Checks / Blockers / Warnings / Evidence to Provide / Related Criteria). Implement a real evaluation mechanism (script, hook, or workflow step) and a storage location for per-run evaluation artifacts (task id, files changed, criteria applied, passes, warnings, blockers, tradeoffs).
- Wire criteria resolution into the agent workflow: agents must determine applicable criteria before implementation and evaluate the diff against them before marking work complete. Create an explicit skill-to-criteria mapping so simplifier/refactor skills are judged against code-simplicity criteria, security skills against security-review criteria, etc.
- Define the shared contract consumed later by Standards Delta / Health: criterion id, title, domain, severity, evaluation_method, applicability rules, blocking/advisory status, evidence fields, related criteria, and optional standards-mapping metadata. 0c owns the judging rubric; 3b owns project health scoring and remediation.

**Why first:** Every other system uses this framework to validate its own output. Workflow Orchestration validation gates, Prompt Library promotion rules, and Standards Delta health scoring all require criteria to be live and agent-accessible before they can be built.

**Write ownership:** AIOS `spec/success-criteria/**`, criteria evaluator/artifact storage, skill-to-criteria mapping, agent workflow docs, project applicability metadata. Do not create project health scoring, Taski remediation, or standards versioning here.

---

## Phase 1 — Core Infrastructure
*Starts after Phase 0 completes. 1a and 1b can run in parallel only because their write sets should be independent. 1c runs after 1a and 1b produce enough system state to audit.*

---

### 1a — Prompt Library Phase 1
**Spec:** [`2026-04-08-prompt-library-design.md`](2026-04-08-prompt-library-design.md) — Phase 1 section

**Requirements:**
- Build a reusable, versioned, evaluable prompt template library for recurring AI workflows across all development projects. Templates live as YAML-frontmatter + markdown body files in `~/AIOS/prompts/`, validated and indexed by `bin/validate-prompts.py`, synced to the Obsidian Vault by `bin/sync-prompts.py`, and auto-suggested by the existing `hook-prompt-submit.py`.
- Use the Phase 1 schema in `2026-04-08-prompt-library-design.md` as canonical: `id`, `name`, `version`, `classification`, `tags`, `purpose`, `when_to_use`, `when_not_to_use`, `required_inputs`, `output_contract`, `eval_criteria`, `owner`, `last_updated`, and `changelog`, with `optional_inputs` allowed. Seed with at least 5 strong templates for major recurring task types. The `prompts_used.reusable_candidate=1` flag has been set on 71 existing prompts — the library provides the promotion destination.
- Keep Phase 1 strictly scoped: no validation pipelines, no promotion state machines, no experimentation infrastructure. Those belong in Phase 2.

**Why here:** Foundational asset store consumed by Phase 2 (execution strategies) and Workflow Orchestration (normalization stage). Must exist before either can be built.

---

### 1b — Anti-Slop ESLint Ratchet
**Spec:** [`2026-04-08-anti-slop-eslint-design.md`](2026-04-08-anti-slop-eslint-design.md)

**Requirements:**
- Audit the already-wired `eslint-plugin-anti-slop` integration in `aios-ui/` and the reusable plugin package at `../../projects/eslint-plugin-anti-slop`.
- Ratchet only missing pieces: per-rule documentation, tests/fixtures for discovered false positives, AIOS project-profile metadata, CI/check wiring, and rollout guidance for additional TypeScript/React repos.
- Preserve the plugin's narrow purpose: structural quality, not taste. Rules must block obvious boilerplate and pattern violations with high confidence — no aesthetic scoring.

**Why here:** Independent of everything else. Ratcheting it early means all subsequent UI and frontend work in linked TypeScript/React projects can be checked against the current rule set.

---

### 1c — Improvement Engine Audit
**Spec:** [`2026-04-22-aios-improvement-engine-audit.md`](2026-04-22-aios-improvement-engine-audit.md)

**Requirements:**
- **Audit only — no implementation.** Produce a decision-quality report measuring the delta between the current AIOS improvement system and an ideal cron-driven experimentation/research engine. Audit seven capability areas: scheduled experimentation infrastructure, prompt experimentation, rule experimentation, evaluation system, improvement loop integrity, operational architecture, and cost/complexity tradeoffs.
- Score each area current/10 vs ideal/10. Explicitly classify what can run deterministically without an LLM, what should stay hybrid, and what fundamentally requires LLM or human judgment. Deliver three decision paths (lean deterministic / hybrid / LLM-heavy) with benefits, risks, engineering complexity, and ROI for each. End with a "Brutal Truth" section.
- Output is a decision memo, not an implementation plan. The findings directly gate the scope of Prompt Library Phase 2.

**Why here (audit only):** Findings determine how much experimentation and promotion infrastructure Phase 2 actually needs. Do not build the cron/eval machinery before this report exists.

---

## Phase 2 — Core Systems
*Depends on Phase 1. Workflow Orchestration (2a) must precede Prompt Library Phase 2 (2b).*

---

### 2a — Workflow Orchestration
**Spec:** [`2026-04-22-aios-workflow-orchestration.md`](2026-04-22-aios-workflow-orchestration.md)

**Requirements:**
- Audit and extend the existing orchestration/control-plane primitives rather than rebuilding them. AIOS already has `orchestration_runs`, invocation handshake, event trace tables, `/control`, and a managed local runtime path.
- Move the remaining freeform prompt composition toward a deterministic execution model with a typed workflow registry, explicit stage model, and first-class skill registry that can run against any linked project. Each workflow (e.g. `academic_paper_v1`, `prd_generation_v1`, `bugfix_v1`) defines ordered stages, required/optional skills, required validations, output contract, project/profile requirements, and observability fields. Skills declare input/output schemas, allowed stages, invariants, and whether they are deterministic or heuristic.
- Implement at minimum one full reference workflow (`academic_paper_v1`) wiring: prompt library normalization stage, Obsidian personal corpus retrieval adapter for voice enrichment, humanizer stage with an explicit contract (must preserve factual meaning and citations; may improve rhythm and readability; must not invent evidence or weaken claims), and validation gates for structure, citations, and meaning preservation.
- Deliver: workflow registry, stage model, skill registry, validation hooks, schema/types for future workflow additions, execution reporting (structured report per run showing stages, skills, validations, artifacts), tests, and observability. The humanizer contract and corpus retrieval interface must be explicit even if the Obsidian integration is stubbed.

**Why here:** This is the runtime execution layer. Prompt Library Phase 2 strategies execute within workflows. The UI Command Center surfaces workflow runs. Neither can be built without this foundation.

---

### 2b — Prompt Library Phase 2 (Execution Strategies)
**Spec:** [`2026-04-08-prompt-library-design.md`](2026-04-08-prompt-library-design.md) — Phase 2 section

**Requirements:**
- Evolve the Phase 1 template library into a validation-driven execution strategy system. The core artifact is no longer a raw prompt — it is an execution strategy bundle containing: canonical task spec, surface adapter (Claude Code or Codex), command template, skill bundle, context profile, validation profile, and model/effort profile. Strategies are shared at the task-family level but have distinct adapter implementations per surface.
- Treat the lifecycle, replay, shadow, canary, promotion, and rollout machinery as conditional scope. Implement only the subset justified by the 1c Improvement Engine audit; if 1c recommends a lean or hybrid path, build schema and manual/semi-automated gates before heavy experimentation infrastructure.
- Seed with canonical task specs and at least one Claude Code + one Codex strategy bundle for a small first slice selected from: architecture_review, audit_and_implement, PRD_generation, repo_refactor, bug_investigation, research_summary, writing_rewrite, handoff_doc_generation. Do not require all task families in the first implementation pass unless 1c explicitly justifies the cost.

**Why here:** Depends on Phase 1 prompt library (asset store), Workflow Orchestration (strategies execute within workflows), and Improvement Engine findings (determines scope of experimentation infrastructure).

---

## Phase 3 — Visibility + Governance
*Depends on Phase 2 being stable. 3a before 3b.*

---

### 3a — UI Command Center MVP
**Spec:** [`2026-04-22-aios-ui-command-center.md`](2026-04-22-aios-ui-command-center.md)

**Requirements:**
- Audit and implement a major pass on AIOS_UI to turn it into a true command center: system monitor, control plane, knowledge browser, workflow debugger, and experiment console in one surface.
- Required MVP surfaces for this phase: global command center homepage, workflow/run observability, approvals/interventions inbox, change timeline, and source-backed status/provenance model.
- Remaining target surfaces may be scaffolded or planned, but should not block MVP completion unless backed by real data sources: agent registry/orchestration map, prompts/rules/skills console, experiment and learning console, cron/jobs/automation console, project/knowledge browser, and chat + grounded inspect mode.
- Statuses must be source-backed and distinguish confirmed / inferred / stale / missing state. Every important UI claim must be traceable to a source of truth. Dense information is acceptable if it remains legible. Deliver three artifact docs: `docs/aios-ui-command-center-audit.md`, `docs/aios-ui-command-center-implementation-plan.md`, and `docs/aios-ui-command-center-handoff.md`.
- Large refactors to the app shell and navigation are allowed and expected if the current IA does not support a command-center product. Thin display pages, consolidated helpers, and explicit state modeling are required. Cosmetic redesign without IA improvement is explicitly out of scope.

**Why here:** Needs live workflow run data (2a), JSON CLI surfaces (0b), and evaluation results (0c) to power its surfaces. Building it before those exist produces a UI with no real data to show.

---

### 3b — Standards Delta / Project Health
**Spec:** [`2026-04-22-aios-standards-delta-health.md`](2026-04-22-aios-standards-delta-health.md)

**Requirements:**
- Build a governance + remediation control plane that measures every linked development project against structured AIOS standards and computes an explainable health score. Standards are first-class objects with fields for id, domain, weight, severity, evaluation_method (auto/semi_auto/manual), expected_state, remediation_playbook, version, project applicability, and waiver policy. Domains: architecture, code quality, testing, security, observability, documentation, workflow/agent control, release/CI discipline, product readiness.
- Health score is derived from standards delta using an explicit penalty model: pass=0, partial=0.5×weight, fail=1.0×weight, unknown=0.75×weight, regressed fail=1.25×weight, waived=0 (marked). Normalize to 0–100. Also compute domain-level scores, critical delta count, regression count, and evaluation confidence. Unknown must remain a distinct visible state — do not collapse it into fail. Backfill prioritization uses `priority = (severity × leverage × dependency_unlock × regression_penalty) / effort` and classifies items into foundational / high leverage / quick wins / blocked / deferred.
- Integrate with Taski: delta items generate actionable tasks traceable to specific standards. Support standards versioning so the system distinguishes "failing current standard" from "met previous standard but not yet upgraded." Waivers require structured rationale, owner, and review date and must remain visible. Deliver seed standards for AIOS, a scoring engine separated from UI components, trend/history persistence, and tests for scoring, delta generation, prioritization, and waiver handling.

**Why here:** Requires standards to be live and agent-accessible (0c), a UI surface to render health views (3a), and workflow runs to assess projects against (2a). This is the final governance layer — it needs real data from the whole stack to be meaningful.

---

## Execution Summary

```
Phase 0  (serial)           0a Architecture Enforcement
                            0b Agent Workflow CLI Audit + JSON Surfaces
                            0c Success Criteria System

Phase 1  (parallel-safe)    1a Prompt Library Phase 1
                            1b Anti-Slop ESLint Ratchet
         (after 1a+1b)      1c Improvement Engine Audit  ← audit only, findings gate Phase 2 scope

Phase 2  (serial)           2a Workflow Orchestration
                            2b Prompt Library Phase 2    ← scoped by 1c findings

Phase 3  (serial)           3a UI Command Center MVP
                            3b Standards Delta / Health
```

---

## Already Executed (reference)

| Spec | File | Evidence |
|------|------|----------|
| AIOS UI (original) | [`2026-04-08-aios-ui-design.md`](2026-04-08-aios-ui-design.md) | `aios-ui/` app exists |
| Code Topology Service | [`2026-04-08-aios-code-topology-service-design.md`](2026-04-08-aios-code-topology-service-design.md) | `bin/cts-*.py` + `data/cts*` exist |
| Anti-Slop ESLint initial wiring | [`2026-04-08-anti-slop-eslint-design.md`](2026-04-08-anti-slop-eslint-design.md) | `aios-ui/eslint.config.mjs` references `eslint-plugin-anti-slop`; `aios-ui/package.json` has `lint` |
| Execution control-plane primitives | [`PROJECT.md`](../../../PROJECT.md) | `orchestration_runs`, invocation handshake, event traces, `/control`, and managed runtime are recorded as implemented |

---

## Notes

- **1c is audit-only in Phase 1.** If findings recommend heavy cron/eval infrastructure, that scope enters Phase 2 as an addendum to 2b. If hybrid is sufficient, 2b scopes down accordingly. Never build the experimentation machinery without this report.
- **0a, 0b, 0c are serial by default.** Parallel execution is allowed only with explicit file ownership because they all touch shared scripts, hooks, docs, and runtime contracts.
- **Anti-Slop ESLint (1b) is TypeScript/React only.** Architecture Enforcement (0a) defines the broader cross-project enforcement model and uses stack-specific adapters such as Dependency Cruiser/ESLint for TS and ruff/import checks for Python.
- **3a and 3b could merge into one pass** if the UI work naturally encompasses the health scoring views.
- **`spec/success-criteria/testing-trust.md`** is the first live criterion. The Success Criteria System (0c) must create the index and wiring for additional criteria to be added cleanly.
