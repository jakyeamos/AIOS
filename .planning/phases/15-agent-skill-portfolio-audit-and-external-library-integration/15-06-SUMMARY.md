# Plan 15-06 Summary: Prototype Skill

## Outcome

Created the global prototype skill at `/Users/jakyeamos/.claude/skills/prototype/SKILL.md`.

The skill is an intent-specific route for answering one uncertainty with throwaway code, not a route for full feature implementation.

## Evidence

- Read nearby exploration skills before writing: `gsd-spike`, `gsd-sketch`, and plugin `playground`.
- The skill requires the agent to state the falsifiable prototype question before writing code.
- The skill distinguishes logic/state prototypes from UI prototypes based on the uncertainty being resolved.
- The skill enforces throwaway markers, single-command execution, no persistence by default, exposed internal state, delete-or-absorb closeout, and branch safety.

## Verification

- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-06-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify references .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-06-PLAN.md` passed.
- `rg` confirmed the question-first gate, logic/state and UI prototype selection, throwaway marker, single-command rule, no-persistence default, state exposure, delete-or-absorb closeout, and branch safety.
- `git diff --check` passed.

## Notes

- The global skill file is outside the AIOS git repository; this repo records the plan contract, summary, and planning truth updates.
