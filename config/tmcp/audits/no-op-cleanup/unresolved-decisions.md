# Unresolved Decisions

Date: 2026-06-24

No unresolved blocker-level decisions remain.

## Accepted Limits

- No executable model ablation was run because all candidates were resolved by
  static proof. Future uncertain removals should use paired representative cases.
- Generated harvested skill output under `skills-library/**` was not edited.
  Regeneration can pick up source changes later through the existing skills
  graph workflow.
- The scanner is advisory by default. It can fail CI only when invoked with
  `--fail-on-candidates`.
