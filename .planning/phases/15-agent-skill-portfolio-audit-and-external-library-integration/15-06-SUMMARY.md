# Plan 15-06 Summary: Prototype Skill

## Outcome

Created the global prototype skill at `/Users/jakyeamos/.claude/skills/prototype/SKILL.md`.

The skill is an intent-specific route for answering one uncertainty with throwaway code, not a route for full feature implementation.

## Evidence

- Read nearby exploration skills before writing: `gsd-spike`, `gsd-sketch`, and plugin `playground`.
- The skill requires the agent to state the falsifiable prototype question before writing code.
- The skill distinguishes logic/state prototypes from UI prototypes based on the uncertainty being resolved.
- The skill enforces throwaway markers, single-command execution, no persistence by default, exposed internal state, delete-or-absorb closeout, and branch safety.

## 2026-06-23 Contract Alignment Correction

- Diffed `/Users/jakyeamos/.claude/skills/prototype/SKILL.md` against `15-06-PLAN.md` before patching.
- Patched only missing contract details in the existing global skill:
  - frontmatter description now includes the exact trigger phrases from the plan and excludes full feature implementation requests
  - question-first guard now halts when no specific question is stated
  - throwaway marker rule now includes the explicit `This file is throwaway. Do not merge. Delete or absorb after: [question]` line
  - standards now state the skill is standalone and prototype code must never be committed to `main` or a release branch
- Existing completion artifacts were preserved; this summary records a correction pass, not duplicate execution.

## Verification

- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-06-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify references .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-06-PLAN.md` passed.
- `rg` confirmed the question-first gate, logic/state and UI prototype selection, throwaway marker, single-command rule, no-persistence default, state exposure, delete-or-absorb closeout, and branch safety.
- `rg` confirmed the exact trigger phrases, no-feature-implementation exclusion, no-question halt, explicit throwaway line, standalone standard, and release-branch warning after the correction pass.
- `git diff --check` passed.

## Notes

- The global skill file is outside the AIOS git repository; this repo records the plan contract, summary, and planning truth updates.
