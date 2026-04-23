# AIOS Agent Workflow CLI Handoff (Phase 0b)

Date: 2026-04-23  
Status: Implemented

## What Changed

Implemented a unified AIOS CLI surface with JSON-first contracts for agent control-plane startup and inspection:

- New unified entrypoint:
  - `python3 ~/AIOS/bin/aios.py`
- New shared CLI service:
  - `services/aios_cli.py`
- New instruction registry:
  - `config/instruction-registry.json`
- New tests:
  - `tests/test_aios_cli.py`

## New Command Surfaces

All commands support `--json` and use a consistent envelope:

```json
{
  "ok": true,
  "command": "<command-name>",
  "generated_at": "<iso8601>",
  "data": { ... }
}
```

Error envelope:

```json
{
  "ok": false,
  "command": "<command-name>",
  "generated_at": "<iso8601>",
  "error": {
    "code": "<semantic-code>",
    "message": "<details>",
    "exit_code": 4
  }
}
```

### Status / Health

- `aios status --json`  
  compact run/session/project/bug snapshot
- `aios health --json`  
  status snapshot + log-file existence/size checks

### Metadata Snapshot

- `aios metadata --json`  
  single-shot startup snapshot including:
  - system paths (`db`, `logs`, `vault`, config)
  - linked project/profile bindings
  - runtime snapshot (current + last session, run counts)
  - instruction sync summary
  - health snapshot
  - failure preview
  - available command surfaces

### Logs / Failures

- `aios logs --json --last 50 [--source hooks]`
- `aios recent-failures --json --last 20`

Failure aggregation currently includes:
- orchestration terminal failures/cancels
- bug log events
- error/fail lines from hooks log tail

### Skills / Instructions Refresh

- `aios skills status --json`
- `aios skills refresh --json` (dry-run)
- `aios skills refresh --json --apply` (writes updates)

Registry-backed source->target sync is now declarative via `config/instruction-registry.json`.

## Semantic Exit Codes

- `0` success
- `2` usage/argument errors
- `3` not found
- `4` dependency/config missing (e.g., DB path not found)
- `5` runtime/processing failure

## What Remains

- Migrate high-value legacy scripts to shared exit-code/error envelope helpers.
- Add optional `aios project metadata --json` scoped command.
- Add richer failure classification (auth/config/transient/runtime categories) as more commands adopt the shared framework.
- Integrate these command surfaces into UI command center views in Phase 3.

## Recommended Agent Startup Sequence

1. `aios metadata --json`
2. `aios recent-failures --json --last 10`
3. `aios skills status --json`
4. If outdated: `aios skills refresh --json --apply`
