# Task: Docs Update

Task ID: `@task:docs_update`

## Trigger

Use for README updates, developer guides, changelogs, release notes, hook docs, command docs, or architecture notes.

## Required Modules

- `@module:doc_update`
- `@module:diff_review`

## Instructions

1. Read the current docs and source behavior before editing.
2. Keep docs tied to runnable commands and real paths.
3. Avoid promising behavior that is not implemented.
4. Keep generated examples small and copy-pasteable.
5. Review docs for stale commands, package-manager drift, and missing prerequisites.

## Exit

Exit with changed doc targets, source evidence, and any staleness notes.

