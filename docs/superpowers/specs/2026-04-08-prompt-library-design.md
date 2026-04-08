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
