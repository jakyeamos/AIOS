# AIOS Prompt Library — Design Spec

**Date:** 2026-04-08
**Status:** Approved
**Author:** jakyeamos

---

## Executive Summary

A reusable, versioned, evaluable prompt template library for recurring AI workflows. Templates live as markdown files in the repo, are validated and indexed by a script, synced to the Vault for Obsidian browsing, and auto-suggested by the existing prompt-submit hook. The system fits inside the existing 3-store architecture without adding new stores or breaking existing conventions.

---

## Problem

Recurring AI tasks (debugging, research, summarization, planning, content writing, reasoning) are currently prompted from scratch every session. This means:
- Quality is inconsistent across sessions
- Good prompt structures are not captured or improved
- The `prompts_used.reusable_candidate=1` flag has been set on 71 prompts with no place to promote them
- `prompt_library_links` and `prompt_template` experiment surface exist in the DB and experiment runner but are unpopulated

---

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Template file format | YAML frontmatter + markdown body | Self-contained, human-editable, machine-parseable |
| Master file location | `~/AIOS/prompts/` | Repo-managed, version-controlled via git |
| Vault sync | `sync-prompts.py` → `07 Templates/Prompts/` | Obsidian browsability, fits STORES.md contract |
| Machine index | `registry.json` (auto-generated) | Hook reads O(1); humans never hand-edit it |
| Hook injection | Rendered snippet: purpose + inputs inline | Actionable without bloating context |
| Eval approach | Structured cases.md + `run-experiment.py` | Rigour without automation overhead |
| Classification mapping | Matches `prompts_used.classification` values | No translation layer needed |

---

## File Layout

```
~/AIOS/
  prompts/
    README.md               # System docs
    registry.json           # GENERATED — output of validate-prompts.py, never hand-edited
    research.md
    summarization.md
    coding_debug.md
    content_writing.md
    reasoning.md
    evals/
      research/cases.md
      summarization/cases.md
      coding_debug/cases.md
      content_writing/cases.md
      reasoning/cases.md

  bin/
    validate-prompts.py     # Parses prompts/*.md, checks fields, writes registry.json
    sync-prompts.py         # Copies .md → Vault, updates prompt_library_links in DB

  tests/
    test_validate_prompts.py
    fixtures/
      prompts/
        valid_template.md
        missing_fields.md
        duplicate_id.md
```

---

## Template Format

Each template is a single `.md` file. The YAML frontmatter is the machine contract; the markdown body is the prompt instructions.

### Required frontmatter fields

This Phase 1 field list is canonical for `bin/validate-prompts.py`. Do not use the older roadmap shorthand fields (`title`, `category`, `surfaces`, `reuse_count`, `quality_score`, `variables`, `example_inputs`, `evaluation_criteria`, `notes`) unless this spec is deliberately revised and the validator is updated in the same change.

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique, snake_case identifier (matches filename) |
| `name` | string | Human display name |
| `version` | string | Semver-like (`"1.0"`, `"1.1"`) |
| `classification` | string | One of: `debug`, `plan`, `refactor`, `implement`, `review`, `explain`, `other` |
| `tags` | list[string] | Keywords used for hook matching |
| `purpose` | string | One paragraph: what this template achieves |
| `when_to_use` | string | Triggering conditions |
| `when_not_to_use` | string | Anti-patterns or wrong contexts |
| `required_inputs` | list[{name: description}] | Inputs the user must provide |
| `output_contract` | string | What a good output looks like |
| `eval_criteria` | list[string] | Pass/fail criteria for evaluation |
| `owner` | string | Template author/maintainer |
| `last_updated` | string | ISO date |
| `changelog` | list[{version, date, note}] | Revision history |

### Optional frontmatter fields

| Field | Type | Description |
|---|---|---|
| `optional_inputs` | list[{name: description}] | Inputs that improve output when provided |

### Body structure (markdown)

```markdown
## Instructions

Step-by-step prompt instructions. Written for the AI, not the human.
Imperative voice. No hedging.

## Example

**Inputs:** (filled-in example)
**Output:** (expected output shape — prose or structured)
```

### Full example

```markdown
---
id: coding_debug
name: Coding Debug
version: "1.0"
classification: debug
tags: [debug, bug, error, fix, crash, failing, broken]
purpose: >
  Systematically diagnose a failing or broken piece of code by isolating
  the root cause before proposing a fix.
when_to_use: >
  Error messages, unexpected behavior, test failures, performance regressions.
when_not_to_use: >
  Exploratory refactors or design questions — use the reasoning template instead.
required_inputs:
  - symptom: "What is broken or failing (error message or observed behavior)"
  - context: "Relevant file path(s) and code snippet"
optional_inputs:
  - hypothesis: "Your current best guess at root cause"
  - constraints: "Fix constraints (no new deps, must stay backward-compatible, etc.)"
output_contract: >
  Root cause identified with evidence. Fix scoped to minimum change. No
  speculative refactoring. If root cause is ambiguous, states the top 2
  hypotheses and what would distinguish them.
eval_criteria:
  - Root cause is named explicitly, not just described
  - Fix touches only what is broken
  - No introduced regressions in adjacent code
  - Uncertainty is stated rather than hidden
owner: jakyeamos
last_updated: "2026-04-08"
changelog:
  - version: "1.0"
    date: "2026-04-08"
    note: "Initial seed"
---

## Instructions

Given the symptom and context, work through this sequence:

1. **Reproduce mentally** — restate what you expect vs. what is actually happening
2. **Isolate** — identify the smallest unit of code that could cause this
3. **Hypothesize** — state your top candidate root cause and the evidence for it
4. **Verify** — cite specific code evidence that confirms or refutes the hypothesis
5. **Fix** — apply the minimum change; explain why it resolves the root cause
6. **Check** — scan adjacent code for anything the fix might affect

Do not refactor beyond the fix. Do not add error handling for unrelated paths.

## Example

**Inputs:**
- symptom: "`TypeError: Cannot read properties of undefined (reading 'id')`"
- context: "`user.profile.id` accessed in `getUser()` after a LEFT JOIN on profiles"

**Output:** "The LEFT JOIN means `profile` is null when no profile row exists.
Fix: guard with `user.profile?.id` or change to INNER JOIN if a profile is
always required. Depends on whether a missing profile is a valid application state."
```

---

## Validation Script (`bin/validate-prompts.py`)

Checks performed on every `prompts/*.md` file:

1. **Required fields present** — all 14 required frontmatter keys exist and are non-empty
2. **No duplicate IDs** — `id` is unique across all templates
3. **ID matches filename** — `id` field equals the filename without extension
4. **Classification is valid** — one of the 7 known classification values
5. **`required_inputs` is a non-empty list**
6. **`eval_criteria` is a non-empty list**
7. **Eval directory exists** — `prompts/evals/<id>/cases.md` exists (warning, not error)
8. **`changelog` is a non-empty list**

On success: writes `prompts/registry.json` and exits 0.
On failure: prints all violations and exits 1.

Run: `python3 bin/validate-prompts.py`

---

## Registry Format (`prompts/registry.json`)

Auto-generated. Never edit by hand.

```json
{
  "generated_at": "2026-04-08T18:00:00Z",
  "templates": [
    {
      "id": "coding_debug",
      "name": "Coding Debug",
      "version": "1.0",
      "classification": "debug",
      "tags": ["debug", "bug", "error", "fix", "crash", "failing", "broken"],
      "purpose": "Systematically diagnose a failing piece of code...",
      "required_inputs": [
        {"symptom": "What is broken or failing"},
        {"context": "Relevant file path(s) and code snippet"}
      ],
      "optional_inputs": [
        {"hypothesis": "Your current best guess at root cause"}
      ],
      "last_updated": "2026-04-08",
      "file": "prompts/coding_debug.md"
    }
  ]
}
```

---

## Hook Integration (`bin/hook-prompt-submit.py`)

After classification, before context assembly:

1. Load `registry.json` if it exists; skip silently if missing
2. Score each template: `score = (classification_match ? 1 : 0) + (tag_overlap_count)`
3. Take the highest-scoring template above a minimum threshold (score ≥ 1)
4. If match found, inject into context block:

```
**Prompt template match: Coding Debug v1.0**
Purpose: Systematically diagnose a failing piece of code by isolating root cause before fixing.
Required: symptom, context | Optional: hypothesis, constraints
Full template: cat ~/AIOS/prompts/coding_debug.md
```

- Snippet capped at ~200 chars for purpose text
- Only best match injected (not all matches)
- `retrieval_source` recorded as `"prompt_library"` in `prompts_used`
- Fall back to existing behavior if `registry.json` is absent or unreadable

---

## Sync Script (`bin/sync-prompts.py`)

1. Reads all `prompts/*.md` files
2. Copies each to `~/Vaults/Command-Center/07 Templates/Prompts/<id>.md`
3. Computes `sha256` of template body (body only, not frontmatter)
4. Upserts row in `prompt_library_links`: `(prompt_hash, obsidian_note_path, promoted_at)`
5. Prints a summary of what was synced/updated

Run: `python3 bin/sync-prompts.py`

---

## Eval Workflow (`prompts/evals/<id>/cases.md`)

Structure per case:

```markdown
## Case N: <short description>

**Inputs:**
- required_input_1: value
- required_input_2: value

**Expected output shape:**
- (prose description of what the output should contain or look like)

**Pass criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

**Last run:** YYYY-MM-DD | **Result:** pass/fail | **Notes:** —
```

**Improvement loop:**

1. Run the template manually; fill in case results
2. If a case fails, open a `run-experiment.py` experiment: `surface=prompt_template`, hypothesis states what change is being tested
3. Edit template instructions, increment version, add changelog entry
4. Re-run affected cases; record new results
5. Close experiment with verdict (`keep` / `discard` / `inconclusive`)
6. Run `validate-prompts.py` to regenerate registry

---

## Seed Templates

Five templates to be created:

| File | Classification | Purpose |
|---|---|---|
| `research.md` | `plan` | Multi-source research → synthesized briefing |
| `summarization.md` | `explain` | Long content → structured summary |
| `coding_debug.md` | `debug` | Diagnose broken code → root cause + minimum fix |
| `content_writing.md` | `other` | Draft structured prose for a defined audience |
| `reasoning.md` | `plan` | Work through an ambiguous problem → reasoned recommendation |

---

## Docs (`prompts/README.md`)

Covers:
- Why the library exists
- How to pick a template
- How to fill inputs and run a template manually
- How to add a new template
- How to revise an existing template
- How to run validation
- How to evaluate a template
- When a recurring task deserves its own template
- Anti-patterns to avoid

---

## Risks and Non-Goals

**Risks:**
- Registry drift: if `validate-prompts.py` is not run after edits, hook sees stale data. Mitigation: document in README; consider adding a pre-commit hook note.
- Vault sync divergence: if templates are edited in Vault directly instead of repo, they'll be overwritten on next sync. Mitigation: README states repo is master.

**Non-goals:**
- Automated prompt execution (no CLI runner that calls the API)
- Prompt A/B testing automation (manual via run-experiment.py)
- Prompt versioning via git tags (changelog in frontmatter is sufficient)
- TypeScript/Node tooling (Python throughout)

---

## Phase 2 — Validation-Driven Execution Strategy System

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Supersedes:** The prompt library vision above. This phase reframes raw prompt templates as validated execution strategy bundles.

### Purpose

Build a system that improves AI output quality over time by transforming raw human requests into validated, task-specific execution strategies before they are sent to the model.

This is not a loose prompt library.
This is not a bag of magic strings.
Treat this as core infrastructure.

**Core objective:** Optimize for the highest rate of high-quality completions under acceptable safety, trust, and cost constraints.

**Primary principle:** The validated artifact is NOT a raw prompt. The validated artifact is an execution strategy bundle.

**Scope gate:** This phase is intentionally downstream of the Improvement Engine audit. Treat the lifecycle, experiment environments, promotion automation, and number of seeded task families below as maximum target architecture, not mandatory first-pass scope. The actual implementation slice must be calibrated by the audit's recommendation: lean deterministic, hybrid, or LLM-heavy.

A strategy bundle may include:
- canonical task spec
- surface adapter
- command template
- skill bundle
- context profile
- validation profile
- model/effort profile
- execution mode

This matters because AIOS runs across multiple surfaces:
- Claude Code, where execution is often command + skills + context + validations
- Codex, where execution is often looser prose and structured task framing

The system must support both without pretending they are identical.

### Prompt

You are auditing and implementing a validation-driven prompt and execution-strategy system for AIOS.

Goal:
Build a system that improves AI output quality over time by transforming raw human requests into validated, task-specific execution strategies before they are sent to the model.

This is not a loose prompt library.
This is not a bag of magic strings.
Treat this as core infrastructure.

Core objective:
Optimize for the highest rate of high-quality completions under acceptable safety, trust, and cost constraints.

Primary principle:
The validated artifact is NOT a raw prompt.
The validated artifact is an execution strategy bundle.

A strategy bundle may include:
- canonical task spec
- surface adapter
- command template
- skill bundle
- context profile
- validation profile
- model/effort profile
- execution mode

This matters because AIOS runs across multiple surfaces:
- Claude Code, where execution is often command + skills + context + validations
- Codex, where execution is often looser prose and structured task framing

The system must support both without pretending they are identical.

What to build:
Design and implement a validation-driven system with these layers:

1. Canonical Task Spec Registry
2. Surface-Specific Execution Strategy Registry
3. Prompt / Instruction Compiler
4. Evaluation and Validation Pipeline
5. Experiment Logging System
6. Rollout State Machine
7. Seeded Strategies for major task families

Critical design decision:
Use shared canonical task families across Claude Code and Codex, with shared core rubric philosophy, but different surface-specific execution strategies and adapter behavior.

---

#### System Architecture Requirements

**A. Canonical Task Spec Layer**
This layer is shared across surfaces.

Each canonical task spec must define:
- task_family
- task_intent_description
- required_inputs
- optional_inputs
- output_contract
- hard_constraints
- quality_rubric_profile
- default_context_requirements

This layer is the stable abstraction.
Do not let surface-specific prompt wording replace it.

**B. Execution Strategy Bundle Layer**
This is the actual validated unit.

Each execution strategy bundle must include:
- strategy_id
- strategy_version
- task_family
- surface (claude_code, codex, later extensible)
- status (draft, experimental, shadow, canary, validated, watchlist, deprecated, rolled_back)
- command_adapter_version
- skill_bundle_version
- context_profile_version
- validation_profile_version
- model_profile
- execution_mode
- token_budget_class
- expected_repo_scope
- safety_scope
- rollout_policy
- parent_strategy_id
- change_hypothesis
- created_at
- created_by

Interpretation by surface:
- In Claude Code, command_adapter_version refers to slash command / harness entrypoint shape.
- In Codex, command_adapter_version refers to prose renderer / instruction assembly shape.

Skill bundle handling:
- Skill files are not validated individually as the main promoted artifact.
- Skill bundles are validated only as part of bundled execution strategies.
- Still version skill bundles separately for traceability and rollback analysis.

**C. Surface Adapter Layer**
Support at minimum:
- Claude Code adapter
- Codex adapter

Claude Code adapter should assume execution is influenced by:
- slash commands
- skills
- injected repo context
- validation routines
- handoff behavior
- effort/model routing

Codex adapter should assume execution is influenced by:
- compiled prose structure
- explicit constraints
- output contracts
- attached context
- model profile

Do not force both surfaces into the same rendering shape.
Keep the task-family lineage shared, but the adapter implementation distinct.

**D. Prompt / Instruction Compiler**
The compiler must assemble:
- raw user ask
- extracted intent and parameters
- canonical task spec
- selected execution strategy bundle
- relevant context profile
- hard constraints
- output contract
- validation expectations

The compiler must preserve user intent and avoid hidden over-mutation.
Do not bloat every request into a giant template.
Select leaner strategies for simpler asks and deeper strategies for high-complexity asks.

---

#### Validation Philosophy

The system must NOT treat formats as proven because they "felt good once."

The first implementation pass may stop at schema validation, manual/semi-automated evidence capture, and a small number of seed strategies if the Improvement Engine audit finds that full replay/shadow/canary infrastructure would be premature.

A strategy becomes proven only through staged evidence:
- designed
- schema-validated
- tested offline
- shadowed in real usage
- canaried live
- promoted
- continuously monitored

Use this validation lifecycle:
- draft
- experimental
- shadow
- canary
- validated
- watchlist
- deprecated
- rolled_back

The system must support promotion, rollback, regression monitoring, and version lineage.

---

#### Evaluation Framework

Use four layers of evaluation, in this exact order:

**1. Hard Fail Gates**
These are promotion blockers. If any fail, the run cannot count as a success.

Hard fail examples:
- hallucination / fabricated repo facts
- critical constraint violation
- severe misalignment to the user ask
- missing required output contract sections
- dangerous over-scoping
- false claim of validation or completion

**2. Quality Score**
This is the primary score. Use a 100-point weighted score with task-family-specific weights.

Global quality dimensions:
- correctness / groundedness
- intent preservation
- specificity
- actionability
- scope discipline
- non-genericness
- correction burden

Add task-family-specific dimensions. Examples:

Architecture review:
- prioritization quality
- structural insight
- file-level practicality
- tradeoff clarity

PRD generation:
- requirement clarity
- acceptance criteria quality
- edge-case coverage
- implementation readiness

Bug investigation:
- root-cause clarity
- evidence-vs-guess separation
- targeted fix quality
- validation readiness

Writing rewrite:
- meaning preservation
- tone preservation
- clarity improvement
- voice retention

**3. Completion Score**
This is secondary to quality.

Completion dimensions:
- delivered usable output
- followed output contract
- low retry requirement
- low unnecessary clarification rate
- materially advanced the task

**4. Efficiency Score**
This is a tie-breaker, not a primary objective.

Efficiency dimensions:
- token cost
- latency
- context size
- tool-call count
- repo churn

Important: do not collapse everything into one global score at first.
Store: hard_fail_pass, hard_fail_types, quality_score, quality_dimension_breakdown, completion_score, efficiency_score.
Only derive higher-level promotion decisions after storing raw components.

---

#### Promotion Rules

**Draft → Experimental**
- schema-valid strategy bundle
- explicit hypothesis
- linked task family
- linked rubric
- complete required metadata

**Experimental → Shadow**
- offline evals beat baseline on quality_score
- no worse on hard-fail rate
- within acceptable efficiency budget
- sampled human review says the candidate is promising

**Shadow → Canary**
- shadow runs on real requests show stable quality advantage
- no major scope regressions
- no operational blowups
- no increase in severe correction burden

**Canary → Validated**
- statistically meaningful improvement or clearly durable directional win on quality and high-quality completion rate
- no hard-fail regression
- acceptable efficiency cost
- human review signoff for high-impact task families

**Validated → Watchlist**
Trigger when: quality drops over trailing window, correction burden rises, model/provider changes cause drift, token cost jumps, rollback-worthy incidents appear.

**Watchlist / Validated → Rolled_Back**
Trigger immediately when: hallucination spikes, damaging repo edits increase, correction burden rises above threshold, hard-fail rate materially exceeds incumbent.

Optimization target: highest rate of high-quality completions. Not highest raw completion rate.

---

#### Experiment Environments

**1. Offline Replay Harness**
Use historical tasks and curated eval corpora. This is where candidates become promising.

**2. Shadow Mode**
Run candidate strategies silently on real tasks without serving them. Mandatory before meaningful promotion.

**3. Canary Rollout**
Expose candidate strategies to a small slice of matching traffic. Measure quality, completion, trust, and cost before promotion.

---

#### Subrepo Testing for Claude Code

Claude Code strategy testing must support subrepo-based evaluation.

Subrepo testing should evaluate:
- command template changes
- skill bundle changes
- context profile changes
- validation profile changes
- effort/model routing changes
- handoff behavior changes

Do NOT validate individual skill files as standalone promoted artifacts.
Validate bundled Claude execution strategies.

Use subrepos representing different challenge patterns:
- clean small app
- messy monorepo
- backend-heavy service
- UI-heavy app
- repo with architecture drift
- repo with weak tests
- repo with misleading structure

---

#### Claude Code vs Codex

Shared across both:
- task family definitions
- hard fail gates
- core quality philosophy
- promotion lifecycle
- experiment logging envelope

Different per surface:
- renderer / adapter behavior
- context assembly
- effort routing
- component versions
- rubric weights where appropriate
- operational metrics emphasis

Claude Code strategy bundles: command-and-skill-driven execution packages.
Codex strategy bundles: compiled prose-and-context execution packages.

---

#### Experiment Logging Requirements

Store per-run evidence first, aggregate summaries second.

Every run must log at minimum:

Core metadata:
- run_id, timestamp, task_family, surface, strategy_id, strategy_version
- task_spec_version, model_profile, repo_or_project_id if applicable
- input_fingerprint, task_complexity_band, repo_size_band

Execution metadata:
- command_adapter_version, skill_bundle_version, context_profile_version
- validation_profile_version, execution_mode, token_budget_class

Outcome metadata:
- hard_fail_pass, hard_fail_types, quality_score, quality_dimension_breakdown
- completion_score, efficiency_score, human_review_score if sampled
- user_acceptance_proxy, correction_burden_proxy, retry_count
- fallback_used, latency, input_tokens, output_tokens

Claude-specific metadata:
- files_touched, validation_commands_run, validation_pass_fail
- handoff_doc_produced, repo_churn_size

Codex-specific metadata:
- output_structure_compliance, implementation_specificity, rewrite_depth if applicable

---

#### Initial Task Families to Seed

Target architecture should eventually cover:

- architecture_review
- audit_and_implement
- PRD_generation
- repo_refactor
- codebase_quality_cleanup
- bug_investigation
- research_summary
- writing_rewrite
- handoff_doc_generation

For the first implementation pass, seed only the highest-leverage subset justified by the Improvement Engine audit. For each selected task family:
- create canonical task spec
- define quality rubric profile
- define hard constraints
- define default context requirements
- create at least one Claude Code strategy bundle
- create at least one Codex strategy bundle
- define initial baseline strategy
- define validation hypothesis for next candidate strategy

---

#### Implementation Expectations

Expected outputs:
1. Executive Summary
2. Current-State Audit
3. Proposed Architecture
4. Data Model / Schemas
5. Runtime Flow
6. Validation Lifecycle Design
7. Evaluation Framework
8. Rollout / Promotion State Machine
9. Experiment Logging Design
10. Claude Code Strategy Design
11. Codex Strategy Design
12. Initial Seeded Task Specs and Strategies
13. Concrete Code / File Changes
14. Migration Plan from ad hoc prompts to validated execution strategies
15. Risks, Tradeoffs, and Failure Modes
16. Next Recommended Improvements

Implementation quality bar:
- prefer durable architecture over clever hacks
- prefer explicit schemas over freeform blobs
- prefer inspectability over hidden automation
- prefer bundle-level validation over folklore
- keep orchestration thin and helpers consolidated
- do not scatter strategy logic across the repo
- make versioning, promotion, and rollback explicit
- integrate with adjacent systems if they already exist instead of duplicating them

Naming guidance:
You may rename "prompt library" to something more accurate such as:
- prompt compiler
- task spec registry
- execution strategy registry
- instruction compiler
- validation-driven execution layer

Make the naming reflect the architecture, not prompt-engineering folklore.

Default bias:
Choose quality over raw completion.
Choose completion over efficiency.
Choose trust and traceability over magic.
Choose bundle-level validation over component mythology.
Choose per-run evidence over aggregate vibes.
