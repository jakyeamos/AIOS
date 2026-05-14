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
wiki_status: current
wiki_confidence: high
last_validated_at: 2026-05-14
validated_by: agent
source_coverage: strong
source_refs:
  - code:tools/context-compile.mjs|Frontmatter parser and validator|2026-05-14
  - test:tests/context-compiler.test.mjs|Schema validation tests|2026-05-14
  - doc:docs/wiki-maintenance.md|Wiki maintenance metadata extension|2026-05-14
known_stale_areas:
  - Maintenance metadata is optional in the context compiler today but enforced by `pnpm wiki:check` for agent usability.
related_pages:
  - context.index
  - context.router
---

Every context file must use frontmatter with `id`, `title`, `tier`, `scope`, `priority`, `status`, `summary`, `applies_when`, and `tags`.
Allowed tiers are `global`, `domain`, `project`, `feature`, `packet`, `handoff`, `task`, and `evidence`.
Allowed priorities are `immutable`, `high`, `normal`, `low`, and `deprecated`.
Allowed statuses are `active`, `draft`, `candidate`, `deprecated`, and `archived`.
Optional compiler fields include `load_if_matched`, `conflicts`, `related`, `owned_by`, `last_reviewed`, and `token_budget`.
Optional wiki-maintenance fields include `wiki_status`, `wiki_confidence`, `last_validated_at`, `validated_by`, `source_coverage`, `source_refs`, `known_stale_areas`, and `related_pages`.

## Acceptance Criteria

- `pnpm context:validate` passes before a context file is treated as authoritative.
- `load_if_matched` links point to existing files relative to `aios/context/`.
- Thin routing files stay below the deep-packet threshold unless they declare a larger `token_budget`.
