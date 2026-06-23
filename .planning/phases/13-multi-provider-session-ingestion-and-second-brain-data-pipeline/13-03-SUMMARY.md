---
phase: 13-multi-provider-session-ingestion-and-second-brain-data-pipeline
plan: "03"
subsystem: session-providers
tags:
  - session-ingestion
  - cursor
  - sqlite
key-files:
  created:
    - services/session_providers/cursor.py
  modified: []
metrics:
  commits: 1
  checks: 5
---

# Plan 13-03 Summary: Cursor Provider Implementation

## Outcome

Implemented the Cursor `SessionProvider` without registering it in `services/session_providers/__init__.py`, per parallel-worker ownership instructions. The provider discovers Cursor workspace SQLite databases, global SQLite database, and agent-transcript JSONL files; reads SQLite through read-only connections with locked-database temp snapshots; inspects `ItemTable` keys dynamically; normalizes workspace hash/path metadata; parses JSONL transcript events; and merges duplicate SQLite/JSONL sessions.

## Commits

| Commit | Description |
|--------|-------------|
| `c8424124` | Implemented the Cursor session provider with source discovery, read-only SQLite extraction, JSONL parsing, workspace metadata, deduplication, and debug-safe health counts. |

## Deliverables

- `services/session_providers/cursor.py` implements the `SessionProvider` contract for Cursor.
- Source discovery covers macOS Cursor paths for `workspaceStorage/**/state.vscdb`, `globalStorage/state.vscdb`, and `~/.cursor/projects/**/agent-transcripts/*.jsonl`, with Linux/other-platform best-effort path handling and warnings.
- SQLite reads use `file:<path>?mode=ro`, `PRAGMA query_only = ON`, and a `~/AIOS/staging/cursor-snapshots/` temp-copy fallback for locked databases.
- `ItemTable` inspection reads every key and filters dynamic Cursor chat/composer/agent/conversation keys plus `aiService.prompts`.
- Workspace metadata preserves the workspace storage hash as `workspace_id`, resolves `workspace.json` folder URIs to `workspace_path`, and marks missing folders as `workspace_orphaned` while setting the path to `None`.
- JSONL transcripts parse newline-delimited event objects into messages, tool calls, file edits, commands, and first/last timestamp metadata.
- Deduplication merges sessions by provider session id, falling back to timestamp/workspace overlap.
- `health_check()` reports source counts, per-source session counts, warnings, and read errors without printing message content.

## Verification

| Check | Result |
|-------|--------|
| `pnpm context:compile --task "Implement GSD Phase 13 Plan 13-03 Cursor SessionProvider in services/session_providers/cursor.py only"` | PASS |
| `uv run python -m py_compile services/session_providers/cursor.py` | PASS |
| `uv run ruff check services/session_providers/cursor.py` | PASS |
| `uv run basedpyright services/session_providers/cursor.py` | PASS |
| Synthetic Cursor smoke test with temp workspace DB, orphaned workspace DB, and JSONL transcript | PASS |

## Deviations from Plan

`services/session_providers/__init__.py` was not edited because this worker was explicitly instructed not to register providers; the orchestrator will register providers after parallel workers finish.

## Self-Check: PASSED

The owned provider artifact exists, implements all abstract methods, exercises read-only SQLite and JSONL paths in a smoke test, preserves workspace metadata, and exposes debug-safe health counts. Registration remains a known orchestrator follow-up outside this worker's ownership.
