# AIOS UI Command Center Audit

Date: 2026-04-23  
Scope: Phase 3a MVP audit + implementation pass

## Current State Summary

AIOS UI already had broad surface coverage (`/control`, `/runs`, `/prompts`, `/automations`, `/feedback`, `/compare`, `/knowledge`) and strong control-plane data sources. The major gap was not feature count; it was **operational clarity and trust semantics**.

## Strengths

- Durable control-plane primitives already exposed in UI (`orchestration_runs`, invocations, events, writebacks, findings).
- Existing run detail had real timeline/event/invocation data.
- Existing alignment and efficiency pages already surfaced quality and cost dimensions.
- Navigation already separated core system domains.

## High-Impact Weaknesses

- Homepage behaved as a general overview, not a command-center operations console.
- Status semantics lacked explicit provenance classification (`confirmed` vs `inferred` vs `stale` vs `missing`).
- Approval queue visibility existed in `/control` but not surfaced on the global command center.
- Change timeline did not unify runs, approvals, experiments, and changes into one source-backed history strip.
- Navigation labels underrepresented command-center intent (e.g., no clear experiment/alignment routing in primary nav).

## Missing MVP Surfaces Before This Pass

- Source-backed “needs attention now” summary.
- Explicit provenance badge model reused across pages.
- Command-center-level approvals/interventions inbox.
- Unified timeline with operational event provenance.

## Architectural Issues

- Status interpretation logic lived ad hoc in components.
- No shared state/provenance helper contract for orchestration and writeback states.

## Data-Model / Observability Gaps

- No machine-readable categorization of status certainty in frontend model layer.
- No stale-signal classification policy centralized in UI logic.

## UX Issues

- Operations data existed but required too much page-hopping to determine action priority.
- At-a-glance “what needs attention now” was implicit rather than explicit.

## Current → Ideal Delta

- Before: rich data, weak command-center synthesis.
- After this pass: source-backed command center homepage + provenance model + interventions inbox + timeline synthesis.
- Remaining for full ideal: deeper live orchestration map, richer cron/job provenance (beyond seeded health), and denser prompt/rule/skill rollout evidence visualization.

## Prioritized Recommendations

1. Keep provenance classification centralized and reused for every new status surface.
2. Add workflow dependency visualization and critical-path blocking analysis.
3. Extend timeline ingestion to include strategy promotions/rollbacks and standards-health deltas.
4. Add explicit stale-data thresholds per surface type via shared config.
