# AIOS Benchmark Eval Architecture

Date: 2026-06-02
Status: Phase 1 Agent Eval Foundation

## Purpose

AIOS needs to prove whether its workflow harness, second-brain context, routing, verification, and writeback behavior improve agent outcomes. This architecture extends the deterministic fixture-backed `docs/evals/aios-harness-eval-v0.md` contract into real workflow evaluation, shadow-branch comparison, peer-run benchmarking, and future external benchmark adapters.

`docs/evals/aios-harness-eval-v0.md` remains the Phase 1 Harness Eval foundation. This document is the Phase 1 Agent Eval Foundation in the same evaluation family. Harness Eval tests deterministic fixture behavior; Agent Eval records real task quality, context profile, portability, failures, and confidence.

## Four-Layer Eval Stack

1. Local second-brain workflow testing
   - Measures real AIOS runs that use the local project graph, context compiler, memory, standards, and workflow rules.
   - Best for judging personalized productivity and second-brain lift.

2. Real workflow shadow testing
   - Compares a baseline branch or baseline harness against an AIOS branch for the same task and acceptance criteria.
   - Best for judging whether AIOS changes improve completion quality without depending only on self-reported success.

3. Peer passive and benchmark testing
   - Replays or observes peer traces with declared context boundaries.
   - Best for finding portability gaps, ambiguous instructions, contamination risks, and workflow assumptions that only work locally.

4. Controlled and external benchmarks
   - Wraps controlled benchmark tasks and external suites around the AIOS evidence model.
   - Best for compatibility with public comparisons after local workflow evidence is stable.

## Eight Rollout Phases

1. Foundation
   - Create vocabulary, context profiles, score formula, failure taxonomy, templates, and schema stubs.
2. Harness Eval
   - Maintain deterministic fixture-backed scoring through `aios-harness-eval-v0.md`.
3. Major Task Eval
   - Require structured eval records after large implementation and architecture tasks.
4. Shadow Branch
   - Compare baseline and AIOS branches for matched tasks.
5. Peer Passive
   - Evaluate peer traces without contaminating them with local second-brain context.
6. Controlled Benchmark
   - Add fixed task sets with stable acceptance criteria and repeatable scoring.
7. Cost And Routing
   - Sample model tier, reasoning level, tool calls, duration, and context profile.
8. External Harness
   - Adapt SWE-bench, Terminal-Bench, BFCL, or similar suites into the AIOS evidence model when the local contract is stable.

## AIOS Effectiveness Score

Overall score is a weighted 0-100 score:

```text
Task Success 30%
+ Quality Adherence 20%
+ Workflow Speed 15%
+ Cost Efficiency 10%
+ Context Effectiveness 10%
+ Autonomy 5%
+ User Trust 5%
+ Context Portability 5%
```

Score dimensions:

- Task Success: acceptance criteria satisfied and working behavior verified.
- Quality Adherence: standards, architecture, maintainability, security, privacy, observability, and testing expectations followed.
- Workflow Speed: elapsed time relative to task complexity and baseline.
- Cost Efficiency: tokens, model cost, and tool calls relative to quality.
- Context Effectiveness: selected context was necessary, sufficient, and not bloated.
- Autonomy: agent moved work forward without avoidable user intervention.
- User Trust: claims match evidence; blockers and risks are stated honestly.
- Context Portability: result can be reproduced outside local private context.

When a dimension is not measurable, record `not measured` in the template and explain why. Do not silently assign full credit.

## Context Comparisons

Second Brain Lift:

```text
Second Brain Lift = AIOS score under jakye_second_brain_full - AIOS score under jakye_repo_only
```

This measures the value of local second-brain context for a task. It does not prove portability.

Portability Gap:

```text
Portability Gap = AIOS score under jakye_second_brain_full - AIOS score under peer_portable_context_packet
```

This measures how much performance depends on private/local context. A large gap is not automatically bad, but it must be labeled.

Shadow Branch Delta:

```text
Shadow Branch Delta = AIOS branch score - baseline branch score
```

Use the same acceptance criteria, start SHA when possible, context profile, and check set. Record human corrections and failed checks separately from the numeric result.

## AIOS Conditions

Use one of these condition labels for eval runs and shadow comparisons:

1. baseline_repo_only
2. baseline_with_manual_context
3. aios_direct_repo_only
4. aios_context_compiler
5. aios_second_brain_full
6. aios_second_brain_limited
7. aios_workflow_governed
8. aios_shadow_branch
9. aios_peer_passive
10. aios_portable_context_packet
11. aios_external_clean_room
12. aios_controlled_benchmark
13. aios_model_routing_sample
14. aios_failure_recovery

## Failure Taxonomy

Select one or more labels when an eval finds a failure or meaningful risk:

1. acceptance_criteria_missed
2. false_completion_claim
3. verification_skipped
4. verification_too_narrow
5. test_modified_to_pass
6. runtime_path_not_exercised
7. context_missing_required_source
8. context_bloat
9. context_contamination
10. portability_overclaimed
11. second_brain_dependency_unlabeled
12. architecture_boundary_violation
13. maintainability_regression
14. security_regression
15. privacy_regression
16. observability_gap
17. governance_bypass
18. destructive_action_unguarded
19. data_model_mismatch
20. migration_or_schema_gap
21. flaky_or_non_deterministic_result
22. cost_or_token_regression
23. tool_use_error
24. user_correction_required
25. unresolved_followup_hidden

## Completion Gates

1. Acceptance gate
   - Original acceptance criteria are listed and evaluated.
2. Evidence gate
   - Checks, commands, rendered behavior, or direct execution prove the claim.
3. Quality gate
   - Maintainability, architecture, testing, security, privacy, and observability are reviewed proportionally.
4. Portability gate
   - Context profile is declared and any local second-brain dependency is labeled.
5. Truth gate
   - Durable docs, project truth, backfill notes, or failure records are updated when state changes.

## Anti-Cheating Rules

Agents must not:

1. Edit tests or fixtures merely to make a failing implementation pass.
2. Skip verification and claim success from static reasoning alone.
3. Suppress command errors, logs, warnings, or failed checks in the eval record.
4. Claim completion when blocker-level criteria still fail.
5. Use private second-brain context in peer_repo_only or external_clean_room runs.
6. Contaminate a baseline branch with AIOS-only fixes before comparison.
7. Change acceptance criteria after implementation without recording the change.
8. Report a narrow check as proof of a broader behavior.
9. Hide unresolved follow-ups that affect acceptance or quality.
10. Label personalized local wins as portable/core benchmark wins.

## Relationship To Harness Eval V0

`docs/evals/aios-harness-eval-v0.md` is the deterministic harness eval mode. It scores fixture artifacts for context routing, gates, success criteria, traces, false-completion prevention, recovery, and writebacks.

This architecture adds real-task eval records, declared context profiles, scorecards, failure taxonomy, shadow comparisons, and portability labeling. Future automation should instrument these records instead of replacing them.
