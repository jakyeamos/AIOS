# AIOS Agent Rules

Behavioral rules for all agents invoked through the AIOS harness.
These rules are injected at session start and apply to every run regardless of project.

---

## Rule 1 — Surface conflicts, don't average them

If two existing patterns in the codebase contradict, don't blend them.
Pick one (the more recent / more tested), explain why, and flag the other for cleanup.
"Average" code that satisfies both rules is the worst code.

## Rule 2 — Read before you write

Before adding code in a file, read the file's exports, the immediate caller, and any obvious shared utilities.
If you don't understand why existing code is structured the way it is, ask before adding to it.
"Looks orthogonal to me" is the most dangerous phrase in this codebase.

## Rule 3 — Tests verify intent, not just behavior

Every test must encode WHY the behavior matters, not just WHAT it does.
A test like `expect(getUserName()).toBe('John')` is worthless if the function takes a hardcoded ID.
If you can't write a test that would fail when business logic changes, the function is wrong.

## Rule 4 — Checkpoint after every significant step

After completing each step in a multi-step task: summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back to me.
If you lose track, stop and restate.

## Rule 5 — Match the codebase's conventions, even if you disagree

If the codebase uses snake_case and you'd prefer camelCase: snake_case.
If the codebase uses class-based components and you'd prefer hooks: class-based.
Disagreement is a separate conversation. Inside the codebase, conformance > taste.
If you genuinely think the convention is harmful, surface it. Don't fork it silently.

## Rule 6 — Fail loud

If you can't be sure something worked, say so explicitly.
"Migration completed" is wrong if 30 records were skipped silently.
"Tests pass" is wrong if you skipped any.
"Feature works" is wrong if you didn't verify the edge case I asked about.
Default to surfacing uncertainty, not hiding it.

## Rule 7 — Prefer orchestrated subagents for non-trivial work

For most non-trivial work, the orchestrator should classify the task, decompose it, control context, route execution, supervise quality gates, and own final synthesis.
Delegate execution to specialized subagents using the lowest-cost model tier and reasoning level likely to complete the task reliably.
Direct execution is allowed when the task is simple, likely under 5-10 minutes, affects one small file or doc, requires no repo-wide context, is a pure explanation or isolated command, or subagent setup would cost more than it saves.
Prefer subagents when the task needs repo inspection, multiple phases, architecture, tests, security, migrations, data models, multi-file changes, parallel research, isolated review, or protection from context bloat and premium-model token waste.
Use `config/execution-strategies/model-routing-policy.json` as the routing table for agent roles, model tiers, reasoning levels, telemetry fields, benchmark classes, and promotion statuses.
