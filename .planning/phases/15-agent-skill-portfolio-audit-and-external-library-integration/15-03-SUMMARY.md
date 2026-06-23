# Plan 15-03 Summary: Diagnose Debugging Skill

## Outcome

Created the global diagnose skill at `/Users/jakyeamos/.claude/skills/diagnose/SKILL.md`.

The skill is an intent-specific debugging route that triggers on errors, unexpected behavior, test failures, production incidents, performance regressions, flaky tests, build failures, integration failures, and bugs before fixes are proposed.

## Evidence

- Read local equivalents before writing: `gsd-debug`, `gsd-forensics`, `gsd-health`, and plugin `systematic-debugging`.
- The skill covers the seven required behaviors: feedback loop first, reproduce before hypothesizing, ranked falsifiable hypotheses, one hypothesis at a time, regression test at the correct seam, debug artifact cleanup, and postmortem or commit explanation.
- The skill includes concrete unit/integration/E2E seam guidance.
- The skill includes the required `architecture-handoff` note directing structural friction to the upcoming `simplifier` architecture review.

## Verification

- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify artifacts .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-03-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify references .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-03-PLAN.md` passed.
- `node /Users/jakyeamos/.claude/get-shit-done/bin/gsd-tools.cjs verify key-links .planning/phases/15-agent-skill-portfolio-audit-and-external-library-integration/15-03-PLAN.md` passed.
- `rg` confirmed the seven behavior labels, seam guidance, and `architecture-handoff` marker exist in the global skill.

## Notes

- The receiving `simplifier` skill is created in Plan 15-04, so Plan 15-03 links its handoff to the 15-04 plan contract.
- The global skill file is outside the AIOS git repository; this repo records the plan contract, summary, and planning truth updates.
