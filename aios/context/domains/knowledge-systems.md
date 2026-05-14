---
id: domains.knowledge-systems
title: Knowledge Systems Domain Standard
tier: domain
scope:
  - knowledge_systems
priority: high
status: active
summary: Routing standard for vault, retrieval, topic graph, and second-brain workflows.
applies_when:
  - task_touches_knowledge_system
  - task_touches_obsidian
load_if_matched:
  - packets/knowledge.obsidian-routing.md
tags:
  - knowledge
  - obsidian
  - retrieval
  - second-brain
last_reviewed: 2026-05-12
wiki_status: current
wiki_confidence: medium
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: partial
source_refs:
  - doc:docs/specs/2026-04-03-knowledge-layer-design.md|Knowledge layer design spec|2026-05-14
  - code:aios-ui/server/aios/knowledge.ts|Knowledge UI data assembly|2026-05-14
  - code:aios-ui/server/aios/topic-graph.ts|Topic graph indexing and retrieval|2026-05-14
  - code:bin/hook-prompt-submit.py|Prompt-time wiki retrieval path|2026-05-14
known_stale_areas:
  - Obsidian/vault retrieval is partly policy and hook based; verify actual vault paths before relying on page coverage.
related_pages:
  - packets.knowledge.obsidian-routing
  - features.obsidian-search
---

Knowledge-system work should distinguish authoritative context, graph navigation, and broad search.
Load map-of-content nodes before traversing detailed notes.
Receipts should show which knowledge clusters were used and which were skipped.

## Acceptance Criteria

- Retrieval starts from routing nodes or explicit source refs.
- Broad semantic search does not replace authoritative packet selection.
