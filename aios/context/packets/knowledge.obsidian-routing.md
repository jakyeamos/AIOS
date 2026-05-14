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
wiki_status: planned
wiki_confidence: medium
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: partial
source_refs:
  - doc:docs/specs/2026-04-03-knowledge-layer-design.md|Knowledge layer design and vault layout|2026-05-14
  - code:bin/hook-prompt-submit.py|Current prompt-time wiki retrieval|2026-05-14
  - code:aios-ui/server/aios/topic-graph.ts|Topic graph topic/reference assembly|2026-05-14
  - code:aios-ui/server/aios/filesystem.ts|Vault root and wikilink parsing helpers|2026-05-14
known_stale_areas:
  - MOC-first traversal is a target routing pattern; current prompt hook still uses simple filename/term matching.
related_pages:
  - domains.knowledge-systems
  - features.obsidian-search
---

Future Obsidian retrieval should classify the task, find relevant note clusters, load Map-of-Content notes first, traverse backlinks/tags/frontmatter, and then compile the smallest sufficient packet.
Candidate MOC nodes include `MOC.AIOS.md`, `MOC.Soundscape.md`, `MOC.JobSearch.md`, and `MOC.WritingStyle.md`.
Notes should be treated as graph nodes with provenance, not flat text files.

## Acceptance Criteria

- MOC notes act as routing nodes into deeper context.
- Backlink and tag traversal is receipt-backed.
- Broad vault search cannot weaken authoritative project or global rules.
