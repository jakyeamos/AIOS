# Phase 30: QR remediation: aios - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning
**Source:** PRD Express Path (/Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/aios.md)

<domain>
## Phase Boundary

Plan the remediation work for aios from Quality Runner run qr-fleet-continue-20260704-aios.
This phase is planning-only until execute-phase runs. Quality Runner remains advisory-only: it identifies findings, remediation clusters, and verification suggestions, but all source changes happen in /Users/jakyeamos/projects/AIOS.

Findings: 22
Severity: `observation` 6, `warning` 16
Categories: `structural:deduplicate` 1, `structural:harden` 7, `structural:ponytail` 2, `structural:simplify` 4, `structural:speed` 1, `structural:ui_structural` 7
Fleet phase candidate: Phase 5 - Large Structural Apps
Requirement: QR-AIOS

</domain>

<decisions>
## Implementation Decisions

### D-01 - QR summary is the planning source
- Use /Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/aios.md and the artifacts under /Users/jakyeamos/projects/AIOS/.quality-runner/runs/qr-fleet-continue-20260704-aios as the source of truth for this remediation phase.

### D-02 - Cluster-oriented remediation
- Plan and execute coherent remediation batches by QR cluster, not one isolated edit per finding row.

### D-03 - Behavior preservation
- Prefer behavior-preserving refactors, hardening, and simplification. Do not change product behavior unless a QR hardening cluster explicitly requires safer behavior.

### D-04 - Existing project conventions first
- Read the target files and local manifests before editing. Follow existing package-manager, formatter, test, and architecture conventions. Use pnpm for JavaScript package scripts.

### D-05 - Evidence-backed closure
- A cluster is done only when focused repo verification passes and a post-remediation QR run shows the fingerprints cleared or are dispositioned with evidence.

### Claude's Discretion
- Choose exact helper extraction boundaries, naming, and task order when the QR document identifies the finding but not the implementation shape.
- If a cluster turns out to require product, API, or design decisions, stop that cluster and capture the question instead of guessing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Quality Runner Inputs
- `/Users/jakyeamos/.local/state/quality-runner/fleet/per-repo-summaries-20260704/aios.md` - Per-repo QR summary used as this phase PRD.
- `/Users/jakyeamos/projects/AIOS/.quality-runner/runs/qr-fleet-continue-20260704-aios/quality-audit.json` - Quality audit report.
- `/Users/jakyeamos/projects/AIOS/.quality-runner/runs/qr-fleet-continue-20260704-aios/remediation-plan.json` - QR remediation plan.
- `/Users/jakyeamos/projects/AIOS/.quality-runner/runs/qr-fleet-continue-20260704-aios/code-quality-scan.json` - Code-quality scan fingerprints.
- `/Users/jakyeamos/projects/AIOS/.quality-runner/runs/qr-fleet-continue-20260704-aios/resolution-ledger.md` - Resolution ledger for closure evidence.
- `/Users/jakyeamos/projects/AIOS/.quality-runner/runs/qr-fleet-continue-20260704-aios/agent-handoff.md` - QR agent handoff.

</canonical_refs>

<specifics>
## Top Findings

- `structural-simplify-large-source-file` warning structural:simplify: 62 large-source-file structural findings in simplification and shrink pass. Fix: 62 findings, aggregate score 558: Split mixed responsibilities into focused modules. Evidence: aios-ui/components/control/ControlPlaneStudio.tsx:1: large-source-file; aios-ui/components/projects/TaskiProjectSurface.tsx:1: large-source-file; aios-ui/lib/control-plane.ts:1: large-source-file
- `structural-harden-uninstrumented-trpc-procedure` warning structural:harden: 92 uninstrumented-trpc-procedure structural findings in API hardening, errors, instrumentation, logging. Fix: 92 findings, aggregate score 552: Use an instrumented procedure or document an explicit opt-out. Evidence: aios-ui/server/routers/automations.ts:9: uninstrumented-trpc-procedure; aios-ui/server/routers/automations.ts:187: uninstrumented-trpc-procedure; aios-ui/server/routers/automations.ts:228: uninstrumented-trpc-procedure
- `structural-simplify-deep-nesting` warning structural:simplify: 87 deep-nesting structural findings in simplification and shrink pass. Fix: 87 findings, aggregate score 522: Flatten guard clauses, extract decision helpers, or split rendering branches. Evidence: aios-ui/components/eval/ShadowCandidateQueue.tsx:76: deep-nesting; aios-ui/components/next-action/NextActionPanel.tsx:68: deep-nesting; aios-ui/components/projects/TaskiProjectSurface.tsx:151: deep-nesting
- `structural-ui_structural-off-scale-spacing` warning structural:ui_structural: 48 off-scale-spacing structural findings in UI accessibility and structural quality. Fix: 48 findings, aggregate score 288: Use the project's spacing scale instead of arbitrary raw values. Evidence: aios-ui/styles/globals.css:148: off-scale-spacing; aios-ui/styles/globals.css:159: off-scale-spacing; aios-ui/styles/globals.css:169: off-scale-spacing
- `structural-simplify-nested-ternary` warning structural:simplify: 28 nested-ternary structural findings in simplification and shrink pass. Fix: 28 findings, aggregate score 252: Replace nested ternaries with named branches or helpers. Evidence: aios-ui/app/page.tsx:157: nested-ternary; aios-ui/components/control/ControlPlaneStudio.tsx:208: nested-ternary; aios-ui/components/panels/PatternRow.tsx:13: nested-ternary
- `structural-harden-sql-string-interpolation` warning structural:harden: 8 sql-string-interpolation structural findings in API hardening and type safety. Fix: 8 findings, aggregate score 72: Use parameterized queries or the ORM parameter API. Evidence: aios-ui/server/aios/control-plane.ts:219: sql-string-interpolation; aios-ui/server/aios/operator-search.ts:201: sql-string-interpolation; aios-ui/server/aios/operator-search.ts:433: sql-string-interpolation
- `structural-speed-await-in-loop` warning structural:speed: 6 await-in-loop structural findings in performance and batching improvements. Fix: 6 findings, aggregate score 36: Batch independent work or document required sequencing. Evidence: tools/context-compile.mjs:526: await-in-loop; tools/no-op-instruction-scan.mjs:152: await-in-loop; tools/wiki-check.mjs:232: await-in-loop
- `structural-harden-bare-trpc-error` warning structural:harden: 3 bare-trpc-error structural findings in API hardening, errors, instrumentation, logging. Fix: 3 findings, aggregate score 27: Use the project typed error taxonomy when available. Evidence: aios-ui/server/routers/projects.ts:454: bare-trpc-error; aios-ui/server/routers/projects.ts:471: bare-trpc-error; aios-ui/server/routers/projects.ts:478: bare-trpc-error

## Remediation Clusters

1. remediate-structural-aios-ui-styles-globals-css (medium, score 336) - Remediate structural cluster in aios-ui/styles/globals.css
2. remediate-structural-scripts-aios-corpus-eval-cjs (medium, score 260) - Remediate structural cluster in scripts/aios-corpus-eval.cjs
3. remediate-structural-tools-wiki-check-mjs (medium, score 152) - Remediate structural cluster in tools/wiki-check.mjs
4. remediate-structural-aios-ui-server-routers-insights-ts (medium, score 105) - Remediate structural cluster in aios-ui/server/routers/insights.ts
5. remediate-structural-tools-context-compile-mjs (medium, score 91) - Remediate structural cluster in tools/context-compile.mjs
6. remediate-structural-aios-ui-server-routers-control-plane-ts (medium, score 78) - Remediate structural cluster in aios-ui/server/routers/control-plane.ts

</specifics>

<deferred>
## Deferred Ideas

- Broad rewrites outside the QR clusters.
- Running Quality Runner as an executor or letting QR mutate source code.
- Remediating repos outside aios; each repo gets its own GSD phase.

</deferred>

---

*Phase: 30*
*Context gathered: 2026-07-04 via QR per-repo PRD*
