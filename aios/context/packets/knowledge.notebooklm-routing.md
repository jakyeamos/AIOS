---
id: packets.knowledge.notebooklm-routing
title: NotebookLM Bounded Synthesis Routing Packet
tier: packet
scope:
  - knowledge_systems
priority: high
status: active
summary: Packet for routing bounded source synthesis and second-brain connection discovery through optional NotebookLM MCP.
applies_when:
  - task_touches_knowledge_system
  - task_touches_obsidian
tags:
  - notebooklm
  - mcp
  - second-brain
  - synthesis
last_reviewed: 2026-06-13
wiki_status: current
wiki_confidence: medium
source_coverage: partial
source_refs:
  - doc:aios/policies/notebooklm-routing.md|NotebookLM routing policy|2026-06-13
  - doc:docs/contracts/notebooklm-mcp-cli-contract.md|Experimental jacob-bd backend contract|2026-06-13
  - code:services/notebooklm_synthesis.py|Optional route classifier and adapter boundary|2026-06-13
related_pages:
  - domains.knowledge-systems
  - packets.knowledge.obsidian-routing
---

Use NotebookLM MCP when the task is about relationships, not just facts.

Fact lookup uses local memory first. Connection discovery uses local memory to select sources, NotebookLM to synthesize the bounded bundle, AIOS to stage results, and reviewed promotion back into Obsidian/TMCP/project docs.

NotebookLM is not canonical memory. Obsidian remains the durable note layer, SQLite/local stores remain operational memory, and TMCP remains the agent-facing compiled context layer.

AIOS recognizes `jacob_bd_notebooklm_mcp_cli` as an experimental backend contract for `jacob-bd/notebooklm-mcp-cli`. Treat it as optional and unavailable unless `nlm`, `notebooklm-mcp`, authentication, and MCP tool probing are confirmed. This backend uses internal NotebookLM APIs and cookie auth according to upstream documentation.

Automated agent use may go through `NotebookLMCLIAdapter`, which runs `nlm login --check`, creates a notebook, adds approved sources with `--wait`, queries NotebookLM, and stages the result. The adapter must fail closed for missing auth, empty bundles, bundles with exclusions, unsafe sources, or command failures.

## Acceptance Criteria

- Source bundles are bounded and explicit before NotebookLM is used.
- Local retrieval runs before NotebookLM for second-brain source selection.
- NotebookLM output is staged before promotion.
- Raw operational memory and sensitive sources are excluded by default.
- Experimental backend readiness is checked before live NotebookLM routing.
- Automated CLI use records provenance and stages output instead of promoting directly.
