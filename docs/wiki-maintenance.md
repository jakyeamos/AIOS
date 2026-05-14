# AIOS Wiki Maintenance Workflow

AIOS wiki and context pages are agent context controls, not source-of-truth replacements.
Use them to decide where to look, what rules apply, what may be stale, and what source files must be verified.

## Maintenance Metadata

Wiki/context entries may carry maintenance metadata:

- `wiki_status`: `current`, `planned`, `deprecated`, `historical`, `experimental`, or `unverified`
- `wiki_confidence`: `high`, `medium`, `low`, or `unknown`
- `last_validated_at`: ISO date or timestamp
- `validated_by`: `human`, `agent`, `script`, or `unknown`
- `source_coverage`: `strong`, `partial`, `weak`, or `none`
- `source_refs`: typed source refs such as `code:services/foo.py#L10-L20|Foo service|2026-05-14`
- `known_stale_areas`: explicit drift risks
- `related_pages`: related wiki/context page identifiers

Source refs can point to repo files or personal corpus records:

- file-backed refs: `code`, `doc`, `prd`, `test`
- corpus-backed refs: `pattern`, `session`, `run`, `packet`, `memory_update`, `knowledge_topic`, `vault_note`, `imported_conversation`, `agent_summary`, `task`

Corpus refs validate against `aios.db` when it is present. Examples:

- `pattern:pattern-id|Approved debugging pattern|2026-05-14`
- `session:session-id|Original agent session|2026-05-14`
- `packet:briefing-packet-id|Run briefing packet|2026-05-14`
- `memory_update:memory-id|Post-run memory summary|2026-05-14`
- `knowledge_topic:topic-slug|Indexed topic graph node|2026-05-14`
- `vault_note:06 Knowledge/Wiki/AIOS-Hook-Architecture.md|Curated vault note|2026-05-14`
- `imported_conversation:conversation-slug|Imported personal corpus conversation|2026-05-14`
- `agent_summary:path/to/summary.md|Agent-written summary artifact|2026-05-14`
- `task:task-id|Task/backfill/writeback record|2026-05-14`

The UI computes a maintenance score from 0 to 5:

- 0: untrusted
- 1: rough note
- 2: source-linked
- 3: agent-usable
- 4: verified
- 5: operational

## Agent Packet Rule

Before using a wiki page to route work, generate or inspect its agent packet.
The packet should identify the subsystem, maintenance score, stale areas, source files to inspect, applicable rules, current-vs-planned notes, and verification checklist.

The packet is a map. Source files, docs, tests, validation scripts, and project truth files remain authoritative.

## Drift Check

Run:

```sh
pnpm wiki:check
```

The check validates critical wiki source refs, flags current pages without refs, validates corpus-backed refs against `aios.db` when available, warns on missing validation timestamps, and checks referenced `pnpm` commands against known package scripts.

## Post-Task Checklist

After meaningful work, ask:

- Did this change architecture?
- Did this change a public API?
- Did this change a workflow?
- Did this change a command?
- Did this change a source-of-truth file?
- Did this invalidate an existing wiki claim?
- Did this create a new rule, risk, or failure mode?
- Should a wiki page or project truth file be updated?

If the answer is yes, update the wiki metadata or project truth as part of the same logical change set.
