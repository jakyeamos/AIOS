---
id: packets.knowledge.obsidian-routing
title: Obsidian Graph Routing Packet
tier: packet
scope:
  - knowledge_systems
priority: high
status: active
summary: Packet for treating Obsidian notes as graph nodes and loading MOCs before detailed notes.
applies_when:
  - task_touches_obsidian
  - task_touches_knowledge_system
tags:
  - obsidian
  - moc
  - graph
  - vault
last_reviewed: 2026-05-12
---

Future Obsidian retrieval should classify the task, find relevant note clusters, load Map-of-Content notes first, traverse backlinks/tags/frontmatter, and then compile the smallest sufficient packet.
Candidate MOC nodes include `MOC.AIOS.md`, `MOC.Soundscape.md`, `MOC.JobSearch.md`, and `MOC.WritingStyle.md`.
Notes should be treated as graph nodes with provenance, not flat text files.

## Acceptance Criteria

- MOC notes act as routing nodes into deeper context.
- Backlink and tag traversal is receipt-backed.
- Broad vault search cannot weaken authoritative project or global rules.
