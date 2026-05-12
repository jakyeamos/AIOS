---
id: features.obsidian-search
title: Obsidian Search Feature
tier: feature
scope:
  - knowledge_systems
priority: high
status: active
summary: Feature context for future Obsidian vault retrieval and graph-aware note routing.
applies_when:
  - task_touches_obsidian
  - task_touches_knowledge_system
load_if_matched:
  - packets/knowledge.obsidian-routing.md
tags:
  - obsidian
  - vault
  - search
  - graph
last_reviewed: 2026-05-12
---

Obsidian search should treat notes as graph nodes, not flat files.
Start from MOC notes, frontmatter, tags, and backlinks before loading detailed notes.
Future integration should produce the same kind of receipt as file-backed context compilation.

## Acceptance Criteria

- MOC notes are preferred as routing nodes.
- Loaded notes and skipped clusters are auditable.
- Vault search does not override authoritative project or global standards.
