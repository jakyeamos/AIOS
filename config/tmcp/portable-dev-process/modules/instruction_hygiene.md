# Module: Instruction Hygiene

Module ID: `@module:instruction_hygiene`

Use this module when creating, revising, consolidating, reducing, or reviewing
agent-facing instructions, prompts, skills, routers, workflow definitions, or
context packets.

## Operational No-Op Definition

Treat a clause as behaviorally inert only when all conditions hold:

- It adds no unique decision rule, action, output field, boundary, or validation
  check.
- The same behavior is already required by a higher-priority instruction,
  adjacent executable rule, schema, hook, evaluator, tool contract, or canonical
  module.
- Static evidence or paired ablation shows no material regression in task
  correctness, required fields, tool use, safety behavior, error handling,
  repository convention compliance, or edge-path handling.
- It is not a safety, security, compliance, authorization, compatibility, or
  explicit user-preference rule.

## Candidate Categories

Flag these as candidates, not automatic deletions:

- Generic quality exhortations without acceptance criteria.
- Restatements of ordinary task completion.
- Duplicates of inherited or adjacent rules.
- Motivational prose directed at the agent.
- Requirements expressed only through adjectives.
- Obsolete references or stale generated-output instructions.
- Examples that merely restate the preceding rule.
- Conflicts with higher-priority instructions.

## Scoring

Score each candidate before editing:

- Behavioral specificity: `0` no identifiable behavior, `1` general intention,
  `2` explicit behavior or output requirement, `3` executable or testable rule.
- Redundancy: `0` unique, `1` partial overlap, `2` effective duplicate, `3`
  inherited or repeated verbatim.
- Removal risk: `0` no plausible consequence, `1` presentation or quality
  consequence, `2` workflow or correctness consequence, `3` safety, security,
  authorization, compliance, or destructive-action consequence.

## Evidence Requirements

- Exact duplicates and inherited clauses may use static proof.
- Behavioral claims require paired representative cases unless executable
  evaluation is not possible.
- Unverified candidates stay marked `unverified`; do not present them as proven
  no-ops.
- Record the canonical source that makes a duplicated clause redundant.

## Dispositions

- Remove only when the no-op hypothesis is proven and removal risk is acceptable.
- Rewrite legitimate intent as an observable rule with a stop condition or
  validation signal.
- Consolidate duplicates into the narrowest canonical layer covering all
  consumers.
- Retain clauses that encode safety, explicit preference, compatibility,
  downstream evaluator needs, project-specific judgment, or untestable behavior.
- Resolve conflicts by precedence and record unresolved conflicts.

## Safety Exclusions

Do not weaken permission boundaries, destructive-action safeguards, network or
credential rules, privacy controls, compliance constraints, or explicit user
preferences. If a clause is vague but protects those areas, rewrite it instead
of deleting it.

## Required Records

For non-trivial instruction cleanup, record:

- discovery report and instruction inventory
- skipped files with reasons
- candidate ledger with scores and dispositions
- duplication, drift, and conflict notes
- ablation plan and results, or a static-proof rationale
- improvement and merge reports
- validation commands and outcomes
- unresolved decisions

## Validation Procedure

Run the advisory scanner when available:

```bash
pnpm tmcp:no-op-scan
```

Then run the relevant prompt, skill, routing, lint, typecheck, test, and context
validation checks for the touched surfaces. Fresh-review the final diff for
lost project-specific rules, broken inheritance, generic replacement prose,
stale links, and safety regressions.
