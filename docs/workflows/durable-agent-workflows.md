# Durable Agent Workflows

Durable agent workflows extend AIOS from single-run code execution into governed long-running work loops. They are additive to the existing context compiler, workflow registry, TMCP, pre-CR checks, quality gates, anti-slop checks, and repository rules.

## Model

### Durable Workspace

A durable workspace is a persistent local-first state surface for a recurring stream of work. It can be a planning directory, run directory, issue, PR thread, spreadsheet, dashboard, or other reviewable artifact chosen by the workflow. It preserves:

- Decisions
- Blockers
- Owners
- Dates
- Useful links
- Verification status
- Known pitfalls
- Next actions

Update it only when something meaningful changes. Avoid duplicate summaries, transcript dumps, speculation recorded as fact, and churn that makes the next agent read more without learning more.

### Goal

A goal is a longer-running task with a clear finish line. Every goal must include:

- Objective
- Verifier
- Stopping condition
- Allowed work surfaces
- Out-of-scope surfaces
- Current checkpoint
- Next action

Vague goals such as "implement the plan" should be rejected or rewritten. Strong goals name a verifier: typecheck passes, lint passes, unit tests pass, build passes, validation matrix passes, repro is fixed, benchmark improves, deployment succeeds, or artifact audit is complete.

### Steering

Steering is an immediate correction to execution direction. Use `/steer` when the agent is actively going the wrong way.

Pattern:

```text
/steer Preserve the existing workflow registry shape; add a candidate route instead of changing active routing.
```

Steering preserves the current goal unless the operator explicitly changes the goal.

### Queuing

Queuing records work that should run after the current checkpoint completes. Use `/queue` when a new instruction should not interrupt in-flight verification.

Pattern:

```text
/queue After the current validation matrix is verified, add a follow-up to audit PR comment automation.
```

Queued work must be visible in the run log or durable workspace state.

## Work Surfaces

Every durable workflow should declare allowed and out-of-scope surfaces before expanding tool reach.

| Surface | Scope |
|---|---|
| Repo work | Code, tests, migrations, configs, docs |
| Artifact work | PDFs, decks, spreadsheets, reports, generated specs, HTML outputs |
| Surface work | Browser UI, Storybook, deployed previews, static pages, data apps |
| Communication work | Slack, Gmail, PR comments, review comments, issue threads |
| Monitoring work | Deployment checks, failing gates, review responses, regressions, external state changes |
| Memory work | Decisions, blockers, TODOs, owners, dates, known pitfalls, reusable workflows |

Communication and destructive work require explicit project permission. Prefer draft/review flows for outbound communication.

## Artifact Rule

For substantial work, the chat transcript is not the source of truth. Use a reviewable artifact when the work needs continuity or auditability:

- Validation matrix
- Implementation checklist
- Audit log
- Canonical spreadsheet
- Generated behavioral spec
- PR review summary
- Issue tracker
- Decision ledger
- Failing-gate report
- Static HTML dashboard
- Deployment verification report

The artifact should connect expected behavior, implementation status, test status, failures, fixes, and final verification.

## Automation Rule

AIOS distinguishes two automation modes:

- Scheduled automation starts fresh from a durable workspace on a recurring schedule.
- Thread or workspace automation wakes the same durable workspace and continues with existing context.

Use automations for PR comment checks, deployment status checks, repeated gate runs, report refreshes, review feedback monitoring, repeated failure collection, and unresolved blocker summaries.

Automations must not silently send external communications or perform destructive actions unless the project rules explicitly permit that behavior.

## Memory Rule

Important context must not live only in the conversation transcript. Prefer the repo's existing truth structure. Useful durable memory surfaces include `AGENTS.md`, `TODO.md`, `DECISIONS.md`, `BLOCKERS.md`, `QUALITY_GATES.md`, `WORKLOG.md`, `SKILL_CANDIDATES.md`, and `PROJECT_STATE.md` when the project uses them.

Memory updates should preserve decisions, blockers, owners, dates, verification results, known pitfalls, useful links, reusable workflow patterns, and unresolved questions. They should avoid note sprawl, duplicate summaries, noisy transcript copying, and speculation recorded as fact.

## TMCP Skill Candidacy

A durable workflow becomes a TMCP skill candidate only after repeated evidence shows it is worth packaging:

- The workflow repeated across multiple runs or repos.
- The same failure mode appeared more than once.
- The workflow has a reusable decision tree.
- The workflow has a reusable verifier.
- Packaging would reduce tokens, variance, or repeated mistakes.
- Scope and non-scope are clear.
- The skill can be evaluated objectively.

Do not create skills from vague preferences or no-op instructions. Convert generic phrases into observable behavior, checks, examples, or rejection criteria first.
