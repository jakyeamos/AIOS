# Codex AIOS Automatic Shadow Plan

## Goal

Let the user run their normal Codex process while every non-trivial Codex task creates a separate AIOS shadow lane for comparison and trust-building.

## Scope

- Make shadowing automatic for ordinary non-`/aios` tasks.
- Keep `/aios` as the governed-route variant, using the same shadow helper with `--governed-route`.
- Add a helper that infers project context, creates an AIOS route record, creates an isolated shadow worktree through existing AIOS shadow commands, and prints the separate Codex prompt to run there.
- Keep baseline workspace authority explicit: shadow output is evidence until reviewed and promoted.
- Ignore `.aios/shadow-worktrees/` in the AIOS repo.

## Acceptance

- `scripts/codex-aios-shadow.py` can create a shadow route in no-worktree mode.
- Unit tests cover shadow task id generation and separate-thread prompt output.
- `AGENTS.md` and `README.md` document automatic shadowing for all non-trivial tasks, `/aios` as governed routing, and `/aios-route-only` as the no-shadow opt-out.
