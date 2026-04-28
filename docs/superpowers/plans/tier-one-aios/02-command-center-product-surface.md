# Command Center Product Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the UI from a collection of dashboards into a decision-oriented command center.

**Architecture:** The UI should render only trusted backend contracts. It should prioritize attention, blocked work, recent outcomes, and explainable metrics over raw tables. Stage this after runtime, knowledge, workflow learning, and contract audits are reliable.

**Tech Stack:** Next.js App Router, React Server Components where possible, tRPC, TypeScript, `better-sqlite3`, existing AIOS UI components.

---

## Files

- Modify: `aios-ui/app/page.tsx`
- Modify: `aios-ui/app/control/page.tsx`
- Modify: `aios-ui/app/projects/page.tsx`
- Modify: `aios-ui/app/costs/page.tsx`
- Modify: `aios-ui/app/automations/page.tsx`
- Modify: `aios-ui/app/knowledge/page.tsx`
- Modify: `aios-ui/server/routers/insights.ts`
- Modify: `aios-ui/server/routers/projects.ts`
- Modify: `aios-ui/server/routers/automations.ts`
- Modify: `aios-ui/lib/trusted-signals.ts`
- Add: `aios-ui/components/common/SignalInspector.tsx`
- Add: `aios-ui/components/common/AttentionList.tsx`
- Add tests where existing test framework supports them, or add router-level tests if no UI test harness exists.
- Modify after each code commit: `PROJECT.md`

## Product IA Target

Final command center navigation:

- **Command Center:** what needs attention now
- **Work:** active runs, blocked runs, recent outcomes
- **Knowledge:** search, browse, citations, graph, memory
- **Projects:** health, risks, deltas, missing data
- **Automations:** reliability, failures, approvals, next run
- **Efficiency:** cost, waste, value, trend
- **Settings:** integrations, paths, contracts, diagnostics

### Task 1: Define Attention Model

**Files:**
- Modify: `aios-ui/server/routers/insights.ts`
- Add: `aios-ui/components/common/AttentionList.tsx`

- [ ] **Step 1: Add router contract**

Add an `attention` query returning:

```ts
type AttentionItem = {
  id: string;
  surface: "runtime" | "project" | "automation" | "knowledge" | "workflow" | "telemetry";
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  summary: string;
  source: string;
  href: string;
  freshness: string;
  confidence: number;
  reason: string;
};
```

- [ ] **Step 2: Source attention from existing contracts**

Include:

- blocked or failed-validation runs
- unsupported lifecycle states
- project critical deltas
- automations with failure or missing run history
- knowledge objects without sources
- terminal runs with no learning signal
- RTK no-data or token-regressive states

- [ ] **Step 3: Render attention list**

Create `AttentionList.tsx` with severity, title, source, and href. Do not include explanatory prose that describes the product; the list itself should be the product.

- [ ] **Step 4: Verify**

```bash
cd aios-ui
npm run lint
```

### Task 2: Rebuild Home Page Around Decisions

**Files:**
- Modify: `aios-ui/app/page.tsx`
- Use: `aios-ui/components/common/AttentionList.tsx`

- [ ] **Step 1: Replace generic overview hierarchy**

Top of `/` should show:

- top attention items
- active/blocked work
- recent outcomes
- system contract health

- [ ] **Step 2: Remove raw telemetry-first ordering**

Do not lead with token totals, counts, or raw tables unless they answer a decision.

- [ ] **Step 3: Add inspectable source affordance**

Every metric block should include a source link or use `SignalInspector`.

### Task 3: Add Signal Inspector

**Files:**
- Add: `aios-ui/components/common/SignalInspector.tsx`
- Modify: `aios-ui/lib/trusted-signals.ts`

- [ ] **Step 1: Component contract**

Render these fields when available:

- value
- source label/table/field
- freshness
- confidence
- provenance
- missing reason
- contradiction detail

- [ ] **Step 2: Replace tooltip-only definitions**

Use `SignalInspector` in Projects, Efficiency, Automations, and Knowledge where a metric could otherwise be ambiguous.

### Task 4: Work Surface

**Files:**
- Modify: `aios-ui/app/control/page.tsx`
- Modify: `aios-ui/components/control/ControlPlaneStudio.tsx`

- [ ] **Step 1: Split work states**

The work surface should group runs by:

- active
- blocked
- waiting for user
- waiting for tool
- failed validation
- recently completed
- superseded

- [ ] **Step 2: Inspect run reason**

Each run must show `status_reason_json` in human-readable form and link to the event trace.

### Task 5: UI Regression Checklist

Before completion verify screenshot-backed issues are gone:

- [ ] no raw RRULE is the primary automation trigger display
- [ ] no `0/5 ERROR` contradiction as primary pipeline state
- [ ] no unlabeled health parenthetical
- [ ] no RTK zero state without active/inactive/no-data explanation
- [ ] no broad `ACTIVE` project badge without a meaningful subtype
- [ ] no table text overlap in Automations
- [ ] no dashboard metric visible without inspectable source

### Tier-One UI Acceptance

- [ ] home page answers "what needs attention now?"
- [ ] every visible metric has an inspection path
- [ ] command center prioritizes decisions over raw telemetry
- [ ] UI uses backend contract states only
- [ ] no feature claims exceed backend capability
- [ ] `npm run lint` passes with no errors
