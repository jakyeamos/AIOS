# AIOS Prompt Library Phase 1 (Phase 1a)

Date: 2026-04-23  
Status: Implemented baseline

## 1) What Was Missing

- No `prompts/` source tree existed.
- `prompt_library_links` was present in schema but had no producer flow.
- `hook-prompt-submit.py` had no deterministic template suggestion path.
- No validator existed to enforce prompt-template schema or generate a machine index.

## 2) Implemented Components

### Prompt source tree
- Added `prompts/README.md`.
- Added five seed templates:
  - `prompts/research.md`
  - `prompts/summarization.md`
  - `prompts/coding_debug.md`
  - `prompts/content_writing.md`
  - `prompts/reasoning.md`
- Added eval case scaffolds:
  - `prompts/evals/*/cases.md`

### Validation/index generation
- Added `bin/validate-prompts.py`:
  - parses YAML frontmatter + body
  - enforces canonical Phase 1 fields
  - checks duplicate IDs, filename alignment, classification validity
  - validates non-empty `required_inputs`, `eval_criteria`, `changelog`
  - warns on missing `prompts/evals/<id>/cases.md`
  - writes `prompts/registry.json`

### Vault + DB sync
- Added `bin/sync-prompts.py`:
  - copies templates to vault `07 Templates/Prompts`
  - hashes body-only content
  - upserts `prompt_library_links` by `prompt_hash`

### Hook integration
- Updated `bin/hook-prompt-submit.py`:
  - loads `prompts/registry.json`
  - scores template match via:
    - classification match (+1)
    - tag overlap count
  - injects compact template hint into retrieval context
  - marks retrieval source as `prompt_library` when template match is used

## 3) Verification

- `python3 bin/validate-prompts.py --prompts-root /Users/jakyeamos/AIOS/prompts`
- `uv run ruff check ...` on new/updated scripts + tests
- `uv run pytest tests/test_validate_prompts.py tests/test_hook_prompt_submit.py ...`
- `sync-prompts.py` smoke run against temporary DB/vault path succeeded (`copied=5`, `created_links=5`)

## 4) Remaining Ratchet Work

1. Add CI invocation for `validate-prompts.py` so registry drift is blocked automatically.
2. Add richer regression tests for frontmatter parser edge cases and malformed nested YAML.
3. Add optional JSON output mode to sync/validate scripts for command-center consumption.
