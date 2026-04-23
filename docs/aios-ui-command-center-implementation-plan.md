# AIOS UI Command Center Implementation Plan

Date: 2026-04-23  
Scope: Phase 3a MVP

## Target IA (MVP)

Primary navigation should map to operator tasks, not generic app buckets:

1. Command Center (`/`)
2. Control Plane (`/control`)
3. Runs (`/runs`)
4. Prompts & Rules (`/prompts`)
5. Experiments (`/compare`)
6. Alignment (`/feedback`)
7. Automations (`/automations`)
8. Efficiency (`/costs`)
9. Knowledge / Projects / Query

## MVP Surface Map

- Global command center homepage: health, alerts, run observability, approvals inbox, timeline.
- Workflow/run observability: `/control` run history + run detail with event/invocation/writeback/finding evidence.
- Approvals/interventions inbox: `/control` and mirrored summary on command center home.
- Change timeline: unified feed on command center home from runs/writebacks/changes/experiments.

## Shared Domain Components

- `lib/status-provenance.ts`
  - run status assessment
  - writeback status assessment
  - attention alert synthesis
  - timeline synthesis
- `components/primitives/ProvenanceBadge.tsx`
  - visual marker for `confirmed / inferred / stale / missing`

## Data Dependencies

- `controlPlane.overview()`
- `changes.list()`
- `automations.list()`
- `experiments.list()`
- Existing run detail data in control-plane surfaces

## Rollout Stages

1. Add shared provenance + alert helpers.
2. Add provenance badge primitive and visual language.
3. Rebuild homepage as command-center operations console.
4. Add provenance badges in control-plane run + approval surfaces.
5. Update navigation labels to reflect command-center operation model.
6. Ship audit/plan/handoff docs with truth-file update.

## Backend Dependencies Not Blocking MVP

- Real automation run history and missed-run provenance (currently seeded automation health).
- Expanded prompt/rule/skill rollout provenance in unified timeline.
- Dedicated workflow dependency graph endpoint.

## Risks

- Overloading homepage without clear severity ordering.
- Drift in staleness thresholds if heuristics are duplicated.

## Mitigations

- Single helper module for status/provenance policy.
- “Needs Attention Now” list prioritized by severity.
- Explicit source attribution on every synthesized status.
