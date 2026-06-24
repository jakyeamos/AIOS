# Codex AIOS Command Trigger Plan

## Goal

Make AIOS routing usable from Codex with an explicit command prefix instead of manually composing project ids and follow-up commands.

## Scope

- Add a helper that infers the AIOS project from the current working directory or accepts an explicit project.
- Route the objective through `aios start-work`.
- Return the run metadata and follow-up inspection commands.
- Teach Codex, through `AGENTS.md`, that `/aios` is the governed AIOS routing command and creates a shadow lane by default.
- Keep automatic shadowing enabled for ordinary non-`/aios` tasks, with AIOS route metadata treated as evidence only.
- Keep `scripts/codex-aios-route.py` as the explicit `/aios-route-only` helper for rare no-shadow runs.
- Document the command pattern in `README.md`.

## Acceptance

- `python3 scripts/codex-aios-route.py "<objective>" --db /tmp/aios-field-pressure.db --cwd /Users/jakyeamos/AIOS` creates a routed run.
- Unit tests cover project resolution by name and current working directory.
- Future Codex sessions can route by `/aios` without user-provided shell commands, and route-only behavior requires `/aios-route-only`.
