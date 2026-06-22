# NotebookLM MCP CLI Backend Contract

Date: 2026-06-13

Backend: `jacob_bd_notebooklm_mcp_cli`

Source: `jacob-bd/notebooklm-mcp-cli`

## Status

This is an experimental backend contract for AIOS. It is not an official Google NotebookLM API contract.

The upstream project documents programmatic access to Google NotebookLM through a CLI and MCP server. It also warns that it uses undocumented internal APIs and browser-cookie extraction. AIOS must treat this backend as optional, revocable, and unsuitable for sensitive or unbounded source bundles.

## Installation And Commands

Expected installation:

```bash
uv tool install notebooklm-mcp-cli
```

Expected commands:

- `nlm`
- `notebooklm-mcp`

Agent setup:

```bash
nlm setup add codex
nlm skill install codex
```

Recommended readiness checks:

- executable lookup for `nlm`
- executable lookup for `notebooklm-mcp`
- `nlm login --check` for operator-auth status
- MCP `server_info` tool probe when an MCP host is available

## Required MCP Tools

AIOS only depends on the small stable subset needed for bounded synthesis:

- `server_info`
- `notebook_create`
- `source_add`
- `notebook_query`

Optional tools:

- `studio_create`
- `download_artifact`
- `cross_notebook_query`
- `tag`
- `batch`

## AIOS Mode Mapping

| AIOS mode | Tool plan |
| --- | --- |
| `bounded_source_synthesis` | `notebook_create` -> `source_add` -> `notebook_query` |
| `connection_discovery` | `notebook_create` -> `source_add` -> `notebook_query` |
| `knowledge_cartography` | `notebook_create` -> `source_add` -> `notebook_query` |
| `tmcp_module_discovery` | `notebook_create` -> `source_add` -> `notebook_query` |
| `learning_opportunity_detection` | `notebook_create` -> `source_add` -> `notebook_query` |
| `contradiction_drift_detection` | `notebook_create` -> `source_add` -> `notebook_query` |
| `project_resurfacing` | `notebook_create` -> `source_add` -> `notebook_query` |
| `briefing_digest` | `notebook_create` -> `source_add` -> `studio_create` |

## Safety Rules

- Do not send raw operational logs, session traces, credentials, secrets, or the whole vault.
- Do not use this backend until AIOS has a bounded source bundle and route reason.
- Record backend key, command names, upstream source URL, source bundle ID, and whether local retrieval ran first.
- If executables or auth are missing, return `skipped_unavailable`.
- If MCP tool probing fails, return `skipped_unavailable`.
- NotebookLM output remains staged and requires review before promotion to Obsidian, TMCP, or project docs.

## Live CLI Adapter

AIOS may use the `nlm` CLI directly before wiring a full MCP client. The guarded sequence is:

```text
nlm login --check
nlm notebook create "<bounded bundle title>" --quiet
nlm source add <notebook-id> --file <path> --wait
nlm notebook query <notebook-id> "<mode-specific query>"
```

For URL, text, or Drive sources, the source-add flags become `--url`, `--text --title`, or `--drive`.

The adapter must fail closed when auth is unavailable, when a source bundle is empty, when any source was excluded, or when command execution fails. It must stage results and record provenance instead of promoting NotebookLM output directly.

## Non-Goals

- AIOS does not vendor the upstream package.
- AIOS does not treat this as an official Google API.
- AIOS does not scrape NotebookLM directly.
- AIOS does not require this backend for boot, context compilation, or local retrieval.
