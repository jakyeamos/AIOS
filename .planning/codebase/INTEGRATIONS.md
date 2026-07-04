---
last_mapped: 2026-05-13
last_mapped_commit: c8817f21
---

# AIOS Integrations Map

## Scope

This document maps the concrete integration surface in `/Users/jakyeamos/AIOS` as of `2026-05-13`.
It focuses on persistence, auth posture, external APIs, local machine dependencies, webhooks/hooks, and operator prerequisites.
Treat this as the practical reference for what AIOS talks to, reads from, or assumes exists on the workstation.

## Integration Model Summary

- AIOS is primarily a local-first system.
- The main integration pattern is not SaaS-to-SaaS HTTP orchestration; it is local SQLite + local filesystem + local macOS apps + occasional external API access.
- Most integrations are operator-mediated or best-effort rather than always-on services.
- There is no implemented end-user login/auth system in the UI today.

## Primary Database

- Canonical operational database is SQLite at `~/AIOS/data/aios.db`.
- This path is referenced directly in `README.md`, `services/aios_cli.py`, `bin/hook-session-start.py`, `bin/hook-stop.py`, and `aios-ui/server/db.ts`.
- `AIOS_DB` can override the default DB path in multiple Python entrypoints, including `bin/aios-managed-run.py` and hook scripts.
- `schema.sql` is the checked-in schema snapshot for this database.
- Major integration domains inside `schema.sql` include:
  - sessions and tool telemetry
  - prompts and artifacts
  - bug tracking
  - AI history imports
  - orchestration runs and invocations
  - RTK compression events
  - knowledge topics, references, markers, and relationships
  - automation run history
  - divergent strategy and workflow synthesis tables
  - success-criteria evaluations and findings

## Secondary Local Datastores

- CTS keeps per-repo graph indexes under `~/AIOS/data/cts/` per `docs/STORES.md`.
- `services/cts/graph_store.py` backs those indexes with SQLite.
- CTS data is derived, rebuildable, and explicitly non-canonical relative to source repositories.
- The UI also contains schema bootstrap code in `aios-ui/server/aios/schema.ts` for tables it expects to exist.

## Local Filesystem Stores

- Operational logs live under `~/AIOS/logs/`, referenced in `README.md`.
- Session linkage depends on `~/AIOS/logs/current_session`, used by `bin/hook-session-start.py`, `bin/record-metric.py`, `bin/eval-session.py`, and `bin/hook-precompact.py`.
- Staging artifacts live under `~/AIOS/staging/`, described in `docs/STORES.md`.
- Context compiler outputs and receipts are file-backed under `aios/context/compiled/` and `aios/context/receipts/`.
- The UI reads some file-backed state indirectly via server modules such as `aios-ui/server/aios/filesystem.ts` and `aios-ui/server/aios/context-compiler.ts`.

## Obsidian Vault Integration

- The main human-readable knowledge store is the Obsidian vault at `AIOS_VAULT_ROOT`.
- Default vault resolution is `~/projects/Vaults/Command-Center/` in `README.md`, `docs/STORES.md`, `bin/takeout-process.py`, `bin/weekly-maintenance.sh`, and `bin/aios_paths.py`.
- Some scripts still mention `~/Vaults/Command-Center`, so path conventions are not fully uniform across the repo.
- `AIOS_VAULT_ROOT` is the main override environment variable.
- Vault-linked tables and pointers include:
  - `projects.obsidian_path`
  - `sessions.handoff_path`
  - `patterns.vault_path`
  - `prompt_library_links.obsidian_note_path`
- Vault content is used for:
  - session handoffs
  - project notes
  - wiki and domain knowledge
  - imported personal corpus content
  - generated reports

## Local macOS App Integrations

- Apple Notes integration is implemented in `bin/ingest-apple-notes.py`.
- That script reads Notes via AppleScript using `osascript`, not direct Notes DB decoding.
- Imported Apple Notes are written into SQLite table `apple_notes` and mirrored into the vault.
- iMessage integration is implemented in `bin/ingest-imessage.py`.
- That script reads `~/Library/Messages/chat.db` by copying it to a temp DB to avoid WAL locking.
- Imported iMessage contact activity is written into SQLite table `imessage_contacts` and mirrored into the vault.
- Multiple hooks use `osascript` for desktop notifications:
  - `bin/hook-stop.py`
  - `bin/hook-update-focus.py`
  - `bin/hook-precompact.py`

## AI Session and History Imports

- AI history ingestion is handled by `bin/import-ai-history.py` and `bin/import_ai_history.py`.
- Supported sources called out in code include:
  - ChatGPT exports
  - Claude exports
  - Codex session rollouts
  - Claude Code local JSONL sessions
- Imported records land in SQLite table `ai_history_imports`.
- Promotion and review flows depend on:
  - `bin/promote-imports.sh`
  - `bin/review-imports.sh`
  - vault destination paths

## GitHub Integration

- The main explicit external API integration is GitHub.
- `bin/discover-github-skills.py` calls the GitHub REST API at `https://api.github.com`.
- Auth is optional and acquired through either:
  - `--token`
  - `gh auth token`
- The script sends `Authorization: Bearer <token>` when available.
- If no token is present, the script warns about strict rate limits.
- Results are stored in local DB-backed workflow candidate tables and surfaced in `aios-ui/server/routers/workflows.ts`.
- Quality pipeline logic also inspects repo-local GitHub Actions workflows by reading `.github/workflows` in `aios-ui/server/aios/quality-pipeline.ts`.

## MCP and Agent Runtime Integrations

- CTS exposes an MCP server implementation in `services/cts/mcp_server.py`.
- That path requires `fastmcp` at runtime.
- Managed agent runtime backends are defined in `services/invocation_backends.py`.
- Confirmed backend surfaces are:
  - `codex-managed-runtime`
  - `claude-managed-runtime`
  - `manual-session-legacy`
- These are local orchestration integrations, not hosted external APIs.
- The run/session/invocation handshake is persisted through SQLite tables such as `orchestration_runs`, `orchestration_invocations`, and `orchestration_run_events`.

## Auth Posture

- There is no user authentication or session auth layer implemented for the Next.js UI.
- `aios-ui/server/trpc.ts` exposes only `publicProcedure`; there is no auth middleware in that file.
- The effective trust boundary is local-machine access to the workstation, filesystem, and SQLite database.
- GitHub API auth is the only clearly implemented bearer-token flow in the current repo.
- Security guidance exists in context files such as `aios/context/standards/global.security.md` and `aios/context/packets/security.oidc-secrets.md`, but that is policy context rather than a live product auth subsystem.

## Webhooks and Hook-Like Entry Points

- AIOS uses local hook scripts instead of remote webhooks for most event ingestion.
- Core hook entrypoints are:
  - `bin/hook-session-start.py`
  - `bin/hook-prompt-submit.py`
  - `bin/hook-post-tool-use.py`
  - `bin/hook-stop.py`
  - `bin/hook-precompact.py`
  - `bin/hook-precompact-prompt.py`
  - `bin/hook-update-focus.py`
- These scripts read stdin payloads, local files, session pointers, and SQLite state.
- `hook-post-tool-use.py` behaves like a local event processor and pattern detector for tool failures and artifacts.
- There are no confirmed inbound public HTTP webhook receivers in the root Python codebase.

## Automation and Scheduling Data

- Automation execution history is stored in `automation_run_history` per `schema.sql`.
- The UI’s automation surfaces read this table in `aios-ui/server/routers/automations.ts`.
- Scheduling metadata is modeled as persisted trigger strings, including RRULE-like values.
- The UI explicitly derives human-readable schedules from stored triggers instead of relying on an external scheduler API.
- This means the repo currently exposes automation observability more clearly than it exposes a built-in automation runner.

## External File/Export Pipelines

- Google Takeout ingestion is implemented in `bin/takeout-process.py` and `bin/takeout-ingest.sh`.
- Supported Takeout domains in code include:
  - Google Drive
  - Google Chat
  - Calendar
  - activity
  - NotebookLM
  - Google Voice
- These flows convert exports into vault markdown rather than calling live Google APIs.
- Document indexing scripts integrate with local files:
  - `bin/index-pdfs.py`
  - `bin/index-docx.py`

## Operator Dependencies

- Confirmed command-line/operator dependencies from source and docs include:
  - `uv`
  - `pnpm`
  - `sqlite3`
  - `gh`
  - `osascript`
  - `pandoc`
  - `pdftotext`
- Optional Python packages required by some ingestion paths include:
  - `icalendar`
  - `python-docx`
  - `pypdf`
  - `openpyxl`
  - `python-pptx`
  - `fastmcp`
- Homebrew is implied by `bin/takeout-ingest.sh`, which installs `pandoc` via `brew`.

## Operator Dependency Impact

- Missing `gh` weakens GitHub discovery by removing token auto-resolution and lowering rate limits.
- Missing `osascript` breaks Apple Notes ingestion and desktop notifications.
- Missing `pandoc`, `pdftotext`, or the optional Python document packages degrades Takeout and document-conversion coverage.
- Missing `sqlite3` breaks several shell-based maintenance and review scripts.
- Missing vault paths or stale DB pointers silently degrade knowledge writebacks and handoff linkage.

## Local Project and Repo Dependencies

- AIOS observes other local git repositories through project inventory and health tooling.
- `services/project_inventory.py` and quality-pipeline code treat local repo paths as first-class inputs.
- `docs/STORES.md` explicitly states code truth lives in external repos under `~/Projects/*/`.
- CTS per-repo intelligence is treated as local derived operational data, not canonical project source.

## Practical Takeaways

- The dominant integrations are local persistence and local desktop data sources, not cloud application APIs.
- SQLite and the Obsidian vault are the two most operationally sensitive dependencies.
- GitHub is the clearest live external API boundary.
- Auth is mostly workstation trust plus optional GitHub bearer tokens, not application-level identity.
- Before debugging a “broken integration,” check path assumptions, local binaries, and DB schema presence before assuming a network problem.
