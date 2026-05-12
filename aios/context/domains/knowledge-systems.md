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
---

Knowledge-system work should distinguish authoritative context, graph navigation, and broad search.
Load map-of-content nodes before traversing detailed notes.
Receipts should show which knowledge clusters were used and which were skipped.

## Acceptance Criteria

- Retrieval starts from routing nodes or explicit source refs.
- Broad semantic search does not replace authoritative packet selection.
