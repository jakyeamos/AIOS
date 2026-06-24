# Improvement Report

Date: 2026-06-24

## Summary

- Instruction surfaces inspected: 96 active editable files.
- Candidates identified: 6.
- Clauses removed: 0.
- Clauses rewritten: 1.
- Duplicates consolidated into canonical TMCP hygiene guidance: 1 module and 1
  task route.
- Clauses retained with justification: 5.
- Unverified candidates presented as proven no-ops: 0.

## Before And After

| Metric | Before | After | Notes |
|---|---:|---:|---|
| Unallowlisted scanner candidates | 6 | 0 | Before run used no allowlist; after run used justified allowlist and rewritten prompt clause. |
| Generic `high-quality` prompt-library clause | 1 | 0 | Rewritten in `prompts/README.md`. |
| Advisory scanner command | 0 | 1 | `pnpm tmcp:no-op-scan`. |
| Scanner unit test command | 0 | 1 | `pnpm test:no-op-scan`. |
| TMCP instruction-hygiene route | 0 | 1 | Added task, module, manifest entry, router edge, and routing fixture. |

## Size Measurements

Prompt clause measurement:

- Before clause: `Capture repeatable high-quality prompting patterns.` (45
  characters, approximately 5 whitespace tokens).
- After clause: `Capture repeatable prompt patterns with frontmatter, output
  contracts, eval cases, and validation commands.` (105 characters,
  approximately 13 whitespace tokens).

The prompt-library sentence became longer because the remediation rewrote a
vague legitimate requirement into observable acceptance criteria rather than
deleting the sentence. Overall repository size increased because this task added
scanner tooling, tests, TMCP routing, and audit records.

Approximate token counts use whitespace splitting and are not model-token exact.
