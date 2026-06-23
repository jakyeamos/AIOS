# Platform Skill Pack Pattern

Use this pattern when adding future platform-specific skills such as macOS,
iOS, Android, Windows, browser-extension, database, cloud, or deployment packs.

## Principle

Keep always-loaded agent files thin. Platform knowledge belongs behind
intent-specific routers, task nodes, modules, and permission branches unless the
rule applies to all development work.

Before editing agent files, decide whether the behavior is:

- always-loaded: applies to nearly every task across projects
- intent-specific: applies only after a platform/task trigger
- module-specific: applies only inside a narrower subtask
- branch-specific: applies only when risk, mutation, network, secrets, or
  publishing is involved

Default to intent-specific placement.

## Required Artifacts

- Audit current repo skill/TMCP conventions.
- Audit donor/source material with provenance, freshness, safety, and rejection
  decisions.
- Add task-shaped skills.
- Split broad reference knowledge into small modules.
- Add hard permission branches before risky behavior.
- Add a router file with triggers and anti-triggers.
- Add a manifest with IDs, paths, dependencies, provenance, gates, tests, and
  validation commands.
- Add behavior fixtures.
- Add a validation command.
- Add operator docs and a final report workflow.

## Node Rules

- Use stable strict IDs.
- Give every task a purpose, triggers, anti-triggers, dependencies, required
  tools, permission gates, validation commands, provenance, freshness notes, and
  behavior tests.
- Give every module a narrow topic and related-module pointers.
- Keep routes short and auditable.
- Do not add a route that means "load everything for this platform."

## Donor Transformation Rules

Record what was:

- adopted
- split
- adapted
- hardened
- inferred
- rejected

Do not run donor build, release, deploy, publishing, or mutation commands during
audit. Treat donor executable automation as source material until safety gates
exist.

## Validation Rules

A platform pack validator should check:

- unique IDs
- route pointer resolution
- referenced files exist
- provenance entries exist
- behavior fixtures exist
- permission-gated actions are represented
- broad always-load triggers are absent
- secret/private-key patterns are absent
- publish/release/deploy actions are gated

## Report Format

Final reports should include:

- scope and source material
- files added or modified
- routes, tasks, modules, and branches added
- validation commands and results
- failures or skipped checks
- assumptions and freshness risks
- accepted tradeoffs
- follow-up repair recommendations
