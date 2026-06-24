# No-Op Instruction Cleanup Discovery Report

Date: 2026-06-24

## Scope Resolution

The repository does not have a top-level `tmcp/` directory. The editable TMCP
authority for this repo is `config/tmcp/`, so this audit records TMCP artifacts
under `config/tmcp/audits/no-op-cleanup/` and updates the portable development
process overlay in `config/tmcp/portable-dev-process/`.

The editable instruction-surface discovery command was:

```bash
git ls-files AGENTS.md config prompts skills research-domain-writing .cursor
```

The audit scanner narrows that tracked set to root agent instructions, agent
rules, TMCP records, workflow registries, prompt templates and eval cases,
project skills, RDW prompt/skill surfaces, and Cursor skill installs.

## Inventory Summary

The final scanner inspected 96 active instruction files:

| Surface group | Count |
|---|---:|
| root instruction | 1 |
| agent rules | 1 |
| TMCP | 46 |
| workflow registry | 2 |
| prompt library | 13 |
| project skills | 18 |
| RDW prompts/skills | 13 |
| Cursor skills | 2 |

## Generated Or External Sources

The audit excluded generated graph/library output, benchmark worktrees, runtime
logs, staging artifacts, local dependency trees, build output, and Python caches.
See `skipped-files.md` for the exclusion record.

## Findings Summary

Initial advisory detection found six generic-instruction candidates before the
new instruction-hygiene TMCP files and allowlist were added:

- one legitimate vague prompt-library clause in `prompts/README.md`
- two imported Remotion skill title fields in `config/workflows/skills.json`
- three quoted rejected-term examples in `skills/operating-language/SKILL.md`

The prompt-library clause was rewritten as an observable rule. The five retained
candidates are allowlisted in `config/tmcp/no-op-scan-allowlist.json` with
line-level reasons.

## Execution Mode

Direct execution was used. The repository preference favors sub-agent execution
for non-trivial work, but the available sub-agent tool contract in this session
allows spawning only when the user explicitly asks for it.
