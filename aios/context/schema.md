---
id: context.schema
title: Context Frontmatter Schema
tier: global
scope:
  - all_projects
priority: immutable
status: active
summary: Required schema for AIOS Context Compiler Markdown files.
applies_when:
  - all_tasks
tags:
  - schema
  - validation
  - markdown
conflicts:
  protected_topics:
    - context_schema
last_reviewed: 2026-05-12
---

Every context file must use frontmatter with `id`, `title`, `tier`, `scope`, `priority`, `status`, `summary`, `applies_when`, and `tags`.
Allowed tiers are `global`, `domain`, `project`, `feature`, `packet`, `handoff`, `task`, and `evidence`.
Allowed priorities are `immutable`, `high`, `normal`, `low`, and `deprecated`.
Allowed statuses are `active`, `draft`, `candidate`, `deprecated`, and `archived`.
Optional fields include `load_if_matched`, `conflicts`, `related`, `owned_by`, `last_reviewed`, and `token_budget`.

## Acceptance Criteria

- `pnpm context:validate` passes before a context file is treated as authoritative.
- `load_if_matched` links point to existing files relative to `aios/context/`.
- Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
