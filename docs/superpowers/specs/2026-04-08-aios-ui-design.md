# AIOS Command — UI Design Spec

**Date:** 2026-04-08
**Status:** Approved
**Stack:** Next.js (App Router) + tRPC + better-sqlite3 + Recharts
**Target:** Local dev only (`next dev`), no auth

---

## Product Thesis

1. **Observability over decoration** — every screen answers a real question about system behavior; nothing exists for aesthetic completeness
2. **Real data by default** — connected to `aios.db` from day one; seeded data fills sparse tables, not replaces real ones
3. **Decision-oriented layout** — each metric ties to one of three actions: keep, fix, or automate further
4. **Drill-down in ≤2 clicks** — home → detail → root cause, no dead ends
5. **Prompt systems as first-class assets** — rules, hooks, and prompts are versioned, evaluated, and benchmarked, not hidden configuration
6. **Waste is always visible** — expensive failures, repeated context, idle tokens are surfaced proactively, not buried
7. **Personal, not generic** — vocabulary matches the actual system (sessions, patterns, tool events, rule bundles) not abstract SaaS concepts
8. **Operator aesthetic** — dark, dense, technical; closer to a CI dashboard or observability tool than a chat product

---

## Information Architecture

### Primary Navigation (persistent left sidebar)

| # | Route | Label | Purpose |
|---|---|---|---|
| 1 | `/` | Command Center | Health at a glance, active runs, anomalies |
| 2 | `/runs` | Run Inspector | Per-session drill-down, trace, tool events |
| 3 | `/workflows` | Workflows | Reusable systems, success rates, cost, usage |
| 4 | `/prompts` | Prompts & Rules | Pattern candidates, approved rules, evals |
| 5 | `/costs` | Efficiency | Token usage, waste, trends by project/tool |
| 6 | `/automations` | Automations | Hooks, cron jobs, triggers, reliability |
| 7 | `/projects` | Projects | Per-project runs, health, attached workflows |
| 8 | `/feedback` | Alignment | Score outputs, behavior rating, drift detection |
| 9 | `/compare` | Diff & Compare | A/B workflow/prompt/policy comparisons |
| 10 | `/settings` | Settings | Model defaults, budgets, guardrails |

### Sub-routes

- `/runs/[id]` — single session trace view
- `/prompts/[hash]` — single prompt/pattern detail
- `/projects/[id]` — per-project dashboard
- `/compare/[a]/[b]` — side-by-side diff view

### Priority Build Order

MVP (real data, fully interactive):
1. `/` Command Center — sessions, tool_events, workflow_metrics
2. `/prompts` Prompts & Rules — prompts_used, patterns, experiments
3. `/costs` Efficiency — tool_events, sessions, workflow_metrics

Remaining pages: scaffolded with functional navigation and seeded data.

---

## Component Architecture

```
aios-ui/
├── app/
│   ├── layout.tsx                # Root layout: sidebar + topbar
│   ├── page.tsx                  # Command Center
│   ├── runs/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── prompts/
│   │   ├── page.tsx
│   │   └── [hash]/page.tsx
│   ├── costs/page.tsx
│   ├── automations/page.tsx
│   ├── projects/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── workflows/page.tsx
│   ├── feedback/page.tsx
│   ├── compare/page.tsx
│   └── settings/page.tsx
├── server/
│   ├── db.ts                     # better-sqlite3 singleton (path: ~/AIOS/data/aios.db)
│   ├── trpc.ts                   # tRPC init, context
│   └── routers/
│       ├── _app.ts               # root router
│       ├── sessions.ts
│       ├── prompts.ts
│       ├── costs.ts
│       ├── patterns.ts
│       ├── projects.ts
│       └── experiments.ts
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── TopBar.tsx
│   │   └── PageShell.tsx
│   ├── primitives/
│   │   ├── StatCard.tsx          # { label, value, delta?, trend?, status? }
│   │   ├── StatusBadge.tsx       # { status: 'healthy'|'warning'|'error'|'unknown' }
│   │   ├── TimelineEvent.tsx     # single tool_events row in trace view
│   │   └── Sparkline.tsx         # inline mini chart
│   ├── charts/
│   │   ├── BarChart.tsx
│   │   ├── AreaChart.tsx
│   │   └── HeatmapCalendar.tsx
│   ├── panels/
│   │   ├── SessionCard.tsx
│   │   ├── PromptCard.tsx
│   │   ├── PatternRow.tsx
│   │   ├── AnomalyAlert.tsx
│   │   └── CostBreakdown.tsx
│   └── command-center/
│       ├── ActiveRuns.tsx
│       ├── RecentActivity.tsx
│       ├── HealthGrid.tsx
│       └── WhatChanged.tsx
├── lib/
│   ├── trpc.ts                   # client-side tRPC hooks (TRPCReact)
│   ├── seed.ts                   # fills sparse tables (costs, anomalies, automations)
│   ├── format.ts                 # token formatting, duration, dates
│   └── constants.ts
└── styles/
    └── globals.css               # CSS custom properties, base styles
```

### Key Component Contracts

- `StatCard` — `{ label: string, value: string|number, delta?: number, trend?: 'up'|'down'|'flat', status?: 'healthy'|'warning'|'error' }`
- `StatusBadge` — `{ status: 'healthy'|'warning'|'error'|'unknown', label?: string }`
- `SessionCard` — renders one run row; expandable inline to show objective, tool counts, artifacts
- `TimelineEvent` — renders one `tool_events` row in trace; shows type, time delta, payload preview
- `PatternRow` — renders one pattern with state badge; approve/reject wired to tRPC mutations

---

## Data Schema (UI Layer)

```typescript
type Session = {
  id: string
  projectId: string
  projectName: string
  tool: 'claude-code' | 'codex' | 'desktop-claude'
  startedAt: string
  endedAt: string | null
  objective: string | null
  status: 'open' | 'closed' | 'abandoned'
  cwd: string | null
  // computed
  durationMs: number | null
  promptCount: number
  toolEventCount: number
  artifactCount: number
}

type ToolEvent = {
  id: string
  sessionId: string
  sourceTool: string
  eventType: 'SessionStart' | 'UserPromptSubmit' | 'PreToolUse' | 'PostToolUse' | 'Stop' | 'SubagentStop' | 'PreCompact'
  eventTime: string
  payloadJson: Record<string, unknown>
}

type Prompt = {
  id: string
  sessionId: string
  promptHash: string | null
  promptText: string | null
  classification: 'debugging' | 'planning' | 'refactor' | 'review' | 'explain' | 'implement' | 'other'
  outcomeScore: number | null
  reusableCandidate: boolean
  retrievalFired: boolean
  retrievalSource: string | null
}

type Pattern = {
  id: string
  state: 'notice' | 'observation' | 'hypothesis' | 'rule'
  humanApproved: boolean
  sessionCount: number
  lastSeen: string
}

type Experiment = {
  id: string
  name: string
  surface: string
  hypothesis: string
  baselineValue: number | null
  challengerValue: number | null
  verdict: string | null
  startedAt: string
  endedAt: string | null
  notes: string | null
  // computed
  delta: number | null
  winner: 'baseline' | 'challenger' | 'inconclusive' | null
}

type Project = {
  id: string
  name: string
  repoPath: string
  status: 'active' | 'archived'
  createdAt: string
  // computed
  sessionCount: number
  lastActiveAt: string | null
  openBugs: number
}

type CostSummary = {
  period: 'day' | 'week' | 'month'
  totalTokens: number
  byProject: { projectId: string; projectName: string; tokens: number }[]
  byClassification: { classification: string; tokens: number }[]
  byTool: { tool: string; tokens: number }[]
  abandonedSessionTokens: number
  failedRunTokens: number
}

type AnomalyAlert = {
  id: string
  type: 'token_spike' | 'abandon_rate' | 'pattern_regression' | 'long_session' | 'repeated_failure'
  severity: 'warning' | 'error'
  message: string
  sessionId: string | null
  detectedAt: string
}
```

---

## Visual Design Language

**Aesthetic:** Cold Terminal — monochromatic base with surgical green accent. Bloomberg terminal × Vercel dashboard.

### Color System

```css
--bg:             #0a0a0b;   /* near-black base */
--surface:        #111113;   /* cards, panels */
--surface-raised: #18181c;   /* hover, selected */
--border:         #1e1e24;   /* separators */
--text-primary:   #e8e8ed;
--text-secondary: #6b6b7a;
--text-muted:     #3d3d4a;

--accent:         #4ade80;   /* green: healthy, success, CTA */
--warning:        #fbbf24;   /* amber: degraded, needs attention */
--error:          #f87171;   /* red: failing, waste, anomaly */
--info:           #60a5fa;   /* blue: neutral counts, info */

--chart-1:        #4ade80;
--chart-2:        #60a5fa;
--chart-3:        #fbbf24;
--chart-4:        #a78bfa;
--chart-5:        #fb923c;
```

### Typography

- **Display / headings:** JetBrains Mono — reinforces terminal feel, data-dense headings
- **Body / UI labels:** Geist — clean, readable at small sizes
- **Data / numbers:** JetBrains Mono — fixed-width, aligned columns

### Layout Grammar

- 240px fixed left sidebar, collapsible to 64px (icon only)
- 16px base grid, 24px section gaps, 32px page padding
- Cards: 1px border (`--border`), 4px border-radius, no box-shadow (flat)
- Tables for lists of runs/prompts — dense, sortable, scannable
- Status always shown as color dot + text badge, never color alone (accessible)

### Motion

- Page transitions: 150ms fade
- Expanding rows: 200ms height transition
- Data refresh: instant swap + 100ms background pulse on changed cells
- No bounce, no spring, no decorative animation

---

## Screen-by-Screen Purpose

| Screen | Question it answers |
|---|---|
| Command Center | Is AIOS healthy right now? What needs attention today? |
| Run Inspector | Why did that session behave that way? Where did it stall? |
| Workflows | Which reusable systems are actually worth keeping? |
| Prompts & Rules | Are my prompt systems improving results? Which patterns are ready to promote? |
| Efficiency | Where am I wasting tokens? Which failures cost the most? |
| Automations | Are my hooks and cron jobs running reliably? |
| Projects | How is AIOS behaving per project? Which have open failures? |
| Alignment | Is the system becoming more aligned with how I like to work? |
| Diff & Compare | Did that system change actually improve things? |
| Settings | What guardrails and defaults am I operating under? |

---

## Technical Decisions

- **DB path:** `~/AIOS/data/aios.db` resolved at server startup via `better-sqlite3`
- **tRPC:** v11 with Next.js App Router adapter; server components call procedures directly, client components use React Query hooks
- **Charts:** Recharts (lightweight, composable, works with RSC pattern)
- **Fonts:** loaded via `next/font` from Google Fonts (Geist + JetBrains Mono)
- **Seeded data:** `lib/seed.ts` exports typed fixtures for cost summaries, anomalies, automations, and workflows — merged with real DB data in tRPC procedures. Sessions, prompts, patterns, and projects read from real DB only and are never replaced by seeds.
- **No auth:** local dev only, no middleware
