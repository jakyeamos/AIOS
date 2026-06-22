# NotebookLM MCP Add-On Architecture

NotebookLM MCP is a bounded source-synthesis and second-brain connection-discovery backend for AIOS. It is useful when an agent needs to reason over a selected packet of documents, discover relationships across notes, identify reusable TMCP modules, detect learning opportunities, or find contradictions in a curated slice of the second brain. It is not the canonical second brain. Obsidian remains the durable human-readable memory layer, local stores remain the operational memory layer, and TMCP remains the agent-facing skill/context layer.

## Why It Is An Add-On

AIOS is local-first. Obsidian, markdown, SQLite, TMCP, and context packets preserve canonical state and provenance. NotebookLM is useful for higher-order synthesis, but it should not own truth, raw operational memory, or automatic promotion.

## Knowledge Synthesis Loop

```text
User task
-> AIOS classifies task
-> local retrieval finds candidate notes/sources
-> AIOS builds a bounded source bundle
-> NotebookLM MCP synthesizes over the bundle
-> AIOS validates and structures the result
-> output is written to staging
-> reviewed output may be promoted into Obsidian, TMCP, or project docs
```

## Supported Modes

- Knowledge cartography: concepts, unresolved questions, clusters, tensions, links.
- TMCP module discovery: repeated workflows, decision branches, conflict branches, shortcut candidates.
- Learning opportunity detection: repeated study themes, missing prerequisites, exercises, learning paths.
- Contradiction and drift detection: stale assumptions, outdated notes, architecture drift, rules that may need revision.
- Project resurfacing: prior notes, decisions, and concepts relevant to a new task.
- Source-bundle briefing: digest, onboarding brief, FAQ, glossary, and next actions.

## Adapter Boundary

`services/notebooklm_synthesis.py` defines `NotebookLMMCPAdapter`. The adapter reads backend metadata from `config/notebooklm/backends.json` and currently targets the experimental `jacob_bd_notebooklm_mcp_cli` backend from `jacob-bd/notebooklm-mcp-cli`.

The backend contract is documented in `docs/contracts/notebooklm-mcp-cli-contract.md`. AIOS only depends on a small MCP tool subset: `server_info`, `notebook_create`, `source_add`, and `notebook_query`, with optional use of `studio_create`, `download_artifact`, and `cross_notebook_query`.

The adapter checks whether `nlm` and `notebooklm-mcp` are present and returns a structured `skipped_unavailable` result with provenance when the backend is missing. This keeps AIOS boot independent from external MCP availability. Live MCP invocation is still not wired directly; the next step is to connect the ready backend to the MCP host once auth and tool probing are approved.

`NotebookLMCLIAdapter` provides the first automated live path for agents. It shells out to `nlm`, runs `nlm login --check`, creates a bounded notebook, adds each approved source with `--wait`, queries the notebook, and returns a staged synthesis result. It fails closed when auth is missing, when any sources were excluded from the bundle, or when the CLI command fails.

## Source Bundles

`build_source_bundle` records included and excluded sources. It excludes sensitive classes, raw operational paths, and sources beyond the configured cap. Bundles are reusable artifacts, not canonical memory.

## Staging Template

`notebooklm_staging_note_template` provides the review surface for NotebookLM output. Promotion targets are explicit checkboxes: Obsidian, TMCP, project docs, keep staged, or discard.

## Validation

Routing behavior is covered in `tests/test_notebooklm_synthesis.py`, including the nine required scenarios from the implementation request. The tests also verify source-bundle filtering, backend registry loading, mode-to-tool planning, CLI automation command sequencing, auth failure behavior, unavailable-adapter behavior, and the staging template.
