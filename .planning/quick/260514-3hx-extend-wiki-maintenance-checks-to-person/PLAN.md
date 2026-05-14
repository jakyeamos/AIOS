# Quick Task: Extend wiki maintenance checks to personal corpus references

## Scope

Extend `pnpm wiki:check` so source refs can point to personal corpus records, not only repo files or vault markdown paths.

## Ref Types

- `pattern`
- `session`
- `run`
- `packet`
- `memory_update`
- `knowledge_topic`
- `vault_note`
- `imported_conversation`
- `agent_summary`
- `task`

## Verification

- `pnpm test:wiki`
- `pnpm wiki:check`
- `pnpm context:validate`
