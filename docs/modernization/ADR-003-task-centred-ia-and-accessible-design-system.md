# ADR-003: Task-Centred Information Architecture and Accessible Design System

**Status:** Accepted v2 target contract<br>
**Date:** 2026-07-13<br>
**Scope:** Operator information architecture, interaction contract, and
prototype acceptance for the Next.js UI. This decision does not implement UI
changes or alter the control-plane API.

## Decision

AIOS v2 presents one operator loop rather than fifteen peer-level destinations:

```text
Today → Start work → Current run → Verify → Gated review → Closeout
  ↑                                                        ↓
  └──────────── Daily flow / next responsible action ─────┘
```

The local operator should always be able to answer five questions without
opening logs or guessing from color:

1. What is the current task and project scope?
2. Which stage is active, blocked, or waiting for a human decision?
3. What evidence supports the current state?
4. What authority or approval is required before the next effect?
5. What is the next responsible action and what remains unresolved?

The UI remains a local client and projection of the Python-owned control plane
defined by [ADR-001](ADR-001-v2-operating-loop-and-trust-boundary.md) and
[ADR-002](ADR-002-canonical-state-and-migration-authority.md). No page may
imply that a browser mutation is authoritative, self-approved, or remote-safe.

## Target information architecture

### Primary modes

| Mode | URL shape | Purpose | Required content |
| --- | --- | --- | --- |
| **Today** | `/` | Resume the operating loop | Current project/run, next action, blockers, approvals, daily-flow replay, source/provenance links |
| **Start work** | `/start` (new v2 surface; may initially reuse existing route data) | Turn intent into a scoped route | Objective, project resolution, ambiguity state, selected workflow/agent, expected evidence, approval classes, explicit start action |
| **Current run** | `/runs/:id` | Execute and inspect one run | Stage rail, current status, invocation, evidence, logs/artifacts, failures, resume action, authority boundary |
| **Review** | `/runs/:id/review` (new v2 state within run) | Verify before promotion or closeout | Criteria, checks, evidence freshness, missing evidence, approval request, reject/return path |
| **Closeout** | `/runs/:id/closeout` (new v2 state within run) | Make the result durable and actionable | Changed artifacts, checks, approvals, unresolved risks, writeback proposals, next action, replay link |

`Today` is the default landing surface. Start, review, and closeout are
explicit states of the same run, not separate dashboard destinations. A
breadcrumb or compact stage rail keeps the URL and current stage visible.

### Contextual surfaces

Project selection, knowledge, search, and settings support the primary modes;
they do not compete with them in the main navigation. A contextual link must
return the operator to the originating project or run with scope preserved.

### Current-route disposition

This is the migration posture for the existing Next routes. “Retire” means
remove the route after its durable value has a replacement; it does not mean
delete the underlying data or server capability.

| Current route | Disposition | V2 placement |
| --- | --- | --- |
| `/` Command Center | **Preserve and rename** | Today; keep source-backed alerts, next actions, daily flow, approvals, and timeline, but order them by responsibility rather than metric count |
| `/projects`, `/projects/:id` | **Preserve, contextualize** | Project picker and project context inside Start work/Today; retain a project detail drill-down |
| `/control` | **Merge** | Current run and Review/Closeout subviews; keep control-plane diagnostics under Systems |
| `/runs`, `/runs/:id` | **Merge** | Current run history and run detail; `/runs/:id` is the canonical run URL |
| `/writebacks` | **Merge** | Review queue and Closeout follow-up; keep a direct filtered link for operators |
| `/knowledge`, `/knowledge/:slug` | **Demote** | Contextual evidence/knowledge drill-down from a project, route, or run |
| `/search`, `/query` | **Demote** | Global command/search affordance and contextual evidence lookup |
| `/settings` | **Demote** | Systems → Settings; never part of the daily stage rail |
| `/prompts`, `/workflows` | **Demote** | Systems → Governed assets; surfaced only when route selection or review needs them |
| `/automations` | **Demote** | Systems → Automations; warnings still appear in Today when actionable |
| `/context` | **Demote** | Systems → Context compiler; receipts link back to the run that used them |
| `/compare`, `/runs/divergent`, `/runs/divergent/:id` | **Demote** | Review evidence and experiment drill-down; no peer-level primary nav item |
| `/feedback` | **Demote** | Review/Closeout learning and alignment evidence |
| `/costs` | **Demote** | Run/project efficiency drill-down; show an actionable budget warning in Today when needed |
| `/skills/candidates` | **Demote** | Governed assets/review; candidate promotion remains approval-gated |
| `/workflows/:id`, `/prompts/:hash` | **Preserve as drill-downs** | Open from route selection, evidence, or governed asset review |

The current 15-item `PRIMARY_NAV` in `aios-ui/lib/constants.ts` is therefore a
temporary compatibility map, not the v2 navigation contract. The redesign
must not add another peer-level item for every new subsystem.

## Representative prototype: start work to closeout

The following prototype is intentionally structural. It is the acceptance
contract for the first vertical slice; implementation may change component
names while preserving hierarchy, states, and evidence placement.

### Screen A — Today / Start work

```text
┌ AIOS ─ Today ─────────────────────────────── [project scope] [Search] ┐
│ Today                                                                  │
│ Current work                                                           │
│  [Resume run]  Refactor billing boundary     VERIFYING   evidence 4/5 │
│                                                                         │
│ Next responsible action                                                │
│  Resolve missing migration check for soundscape-app                     │
│  Why: verification is incomplete · source: run-… / receipt             │
│  [Open current run]                                      [Start work]   │
│                                                                         │
│ Approvals and blockers                         Daily flow               │
│  1 pending human approval                         doctor ✓              │
│  1 missing evidence                               intent ✓              │
│  [Review queue]                                   next action →         │
└─────────────────────────────────────────────────────────────────────────┘
```

`Start work` opens an intent form with a labelled objective, project
resolution, ambiguity explanation, selected route, expected evidence, and
approval classes. The primary action is disabled until a project and route are
resolved; ambiguity is an explicit blocked state with choices, never a silent
guess.

### Screen B — Current run / Verify

```text
┌ Run: Refactor billing boundary ─ VERIFY ─ [Pause] [View evidence] ─────┐
│ 1 Intent ✓ ─ 2 Route ✓ ─ 3 Execute ✓ ─ 4 Verify ● ─ 5 Review ○ ─ 6 Close │
│                                                                        │
│ Verification criteria                         Evidence                 │
│ ✓ typecheck                  passed · 12:14       [open receipt]       │
│ ✓ unit tests                 passed · 12:16       [open report]        │
│ ! migration restore drill    missing              [why required]       │
│                                                                        │
│ Status: needs evidence                                                  │
│ This run cannot enter gated review until the restore drill is attached. │
│ [Return to execution]                         [Request review] disabled │
└────────────────────────────────────────────────────────────────────────┘
```

The stage rail is informational and keyboard navigable; it is not a row of
unlabelled clickable divs. Each criterion exposes its result, timestamp,
source, freshness, and remediation. “Missing”, “stale”, “failed”, and “not
applicable” are distinct values.

### Screen C — Gated review / Closeout

```text
┌ Review required ─ human authority ─────────────────────────────────────┐
│ Proposed effects                                                       │
│  • update project truth: 2 files                                       │
│  • writeback: one learning candidate                                  │
│ Evidence: 5/5 checks passed · receipt run-…                           │
│                                                                        │
│ [Approve and close out]  [Reject with reason]  [Return for more work]   │
│                                                                        │
│ Closeout preview                                                       │
│ Changed artifacts · checks run · approvals touched · unresolved risks  │
│ Next action: update PROJECT_TRUTH.md after this approved commit         │
└────────────────────────────────────────────────────────────────────────┘
```

Approval copy must name the effect, scope, evidence, and actor. A successful
closeout is not a green badge alone: it contains the durable summary and an
explicit next action. Rejection and return-for-work preserve the reason and
stage rather than discarding the run.

## Accessible design-system contract

### Semantic roles and structure

- Use one `<main>` per page, a labelled `<nav>`, meaningful `<header>` and
  `<section>` headings, and a skip link that targets the main content.
- Use native `<a>`, `<button>`, `<input>`, `<select>`, `<textarea>`,
  `<fieldset>`, and `<legend>` elements. Do not make a `div` or `span`
  clickable, and do not add `role="button"` when a native button works.
- Replace grid-like div tables with `<table>`, `<caption>`, `<thead>`,
  `<tbody>`, `<th scope>`, and `<td>`. Sort controls must expose the active
  direction with `aria-sort` and a visible label.
- Every form control has a visible or visually-hidden `<label>`. Errors are
  associated with the control through `aria-describedby` and `aria-invalid`.
- Navigation exposes the active mode with `aria-current="page"`; tabs, if
  used inside a run, expose `aria-selected`, `role="tablist"`, and keyboard
  arrow behavior according to the WAI-ARIA pattern.
- Run status updates use a concise `aria-live="polite"` region. Destructive
  or approval-required changes use an explicit confirmation region and never
  rely on a toast that disappears before it can be read.

### Tokens and visual language

The existing dark instrument direction is retained, but its low-contrast
secondary and muted tokens are not. The implementation should centralize
semantic tokens rather than page-local colors:

| Role | Target token behavior |
| --- | --- |
| Canvas / surface / raised surface | Three restrained dark layers; no decorative gradients or glass treatment |
| Primary text | Minimum 4.5:1 against every normal surface |
| Secondary text | Minimum 4.5:1 at normal body and label sizes; never use the current `#6b6b7a` token for required content |
| Subtle text | Used only for non-essential metadata; required meaning must be repeated in text or structure |
| Accent | Primary action/current selection only; not a decorative wash |
| Warning / error / success / info | Each has text label plus icon or shape; color is never the sole status channel |
| Borders / dividers | Visible enough to separate regions without becoming the primary hierarchy |

Typography uses Geist/system sans for interface copy and JetBrains Mono only
for IDs, timestamps, commands, and other structured values. Use a fixed product
scale (12, 14, 16, 20, 24, 32px), 65–75ch for prose, and balanced headings.
Use a 4/8/12/16/24/32px spacing rhythm, 4–12px radii, and one consistent
button/control vocabulary. Do not pair a decorative border with a wide shadow
or introduce oversized rounded cards.

Every interactive component defines default, hover, focus, active, disabled,
loading, and error behavior. Loading uses skeleton structure where content
shape is known. Empty states explain what the operator can do next. Blocked
states explain the gate and link to its evidence. Motion is limited to state
feedback (150–250ms) and has a `prefers-reduced-motion: reduce` path.

### Responsive behavior

Validate at 375×812, 768×1024, and 1440×900. The layout is structural:

- Desktop: sidebar, main task column, and optional evidence/approval rail.
- Tablet: collapsible sidebar and stacked task/evidence regions.
- Mobile: compact top bar/menu, one-column stage and evidence flow, and a
  persistent current-action region. Do not use a hidden-scroll horizontal
  navigation strip as the primary way to discover modes.
- Tables either reflow to labelled rows/cards or use an explicitly labelled
  overflow region with the first identifying column retained. Never require
  unannounced 480–1080px horizontal scrolling for the core decision.
- Focus order follows the operating loop and remains visible after layout
  changes. Touch targets are at least 44×44 CSS px.

## State contract for the vertical slice

Every mode must specify these states before code is accepted:

| State | Operator meaning | Required UI |
| --- | --- | --- |
| Loading | Source is being fetched | Skeleton or labelled progress region; preserve heading and scope |
| Empty | No run/evidence/approval exists yet | Explain why and offer the next valid action |
| Healthy / passed | Evidence supports progress | Source, timestamp, and scope remain inspectable |
| Warning / stale | Progress is possible but trust is reduced | Plain-language reason, freshness, and remediation |
| Blocked / ambiguous | AIOS cannot safely continue | Gate owner, missing decision/evidence, and explicit choices |
| Needs review | Work is complete enough for human authority | Proposed effect, evidence summary, approve/reject/return actions |
| Failed | Execution or verification failed | Failure summary, logs/receipt link, retry or return path |
| Success / closed | Durable closeout completed | Changed artifacts, checks, approvals, unresolved follow-up, next action |

## Executable UI acceptance matrix

Ticket 007 owns restoring the blocked toolchain. Once that contract is green,
every implementation milestone for this slice must attach the following
evidence:

| Proof | Required check | Pass condition |
| --- | --- | --- |
| Structure | `pnpm lint:architecture`, component review, semantic scan | Existing boundaries hold; no page-local duplicate nav/status/table behavior; native semantics are present |
| Compile | `pnpm lint` from `aios-ui/` and `pnpm build` | ESLint, TypeScript, and offline production build complete without hidden skips |
| Browser | Run Today → Start work → Current run → Verify → Review → Closeout with seeded and empty data | URL/stage state, source evidence, approvals, and next action remain coherent |
| Keyboard | Keyboard-only pass at each screen | Skip link, nav, forms, stage rail, tables, dialogs, and approve/reject actions are reachable and visibly focused |
| Accessibility | Automated axe/contrast check plus manual labels/announcements | No critical/serious findings; normal text ≥4.5:1; states and errors are announced |
| Responsive | Screenshots at 375×812, 768×1024, 1440×900 | No clipped primary action, hidden required content, accidental horizontal nav, or unreadable table |
| Runtime | Browser console and network log during the slice | No duplicate React keys, hydration errors, failed tRPC requests, or unexplained console errors |
| Evidence | Screenshot and receipt paths attached to the run | A reviewer can reproduce the result from the recorded command and artifact links |

The current audit is the baseline, not a pass: it records 3.60:1 and 1.76:1
text ratios, div-based tables, unlabeled settings inputs, mouse-only canvas
stages, hidden-scroll mobile navigation, duplicate keys, intermittent
`runDetail` 500s, and blocked UI lint/build checks. Those findings remain
open until the implementation and Ticket 007 validation contract provide new
evidence.

## Consequences and non-goals

- The UI becomes easier to learn because the primary navigation mirrors the
  operating loop and satellites are reached through context.
- Evidence and approval state become first-class interaction content rather
  than decorative dashboard metadata.
- The first implementation slice is intentionally narrow; it does not require
  redesigning every route before a runnable vertical path exists.
- This ADR does not choose a new frontend framework, add a component library,
  migrate the database, or authorize remote access. Those decisions remain
  governed by the later subsystem and implementation-plan tickets.

## Evidence

- [Modernization audit](AUDIT.md) — current UI, browser, accessibility, and
  toolchain evidence.
- [V2 operating loop and trust boundary](ADR-001-v2-operating-loop-and-trust-boundary.md)
  — local operator authority and canonical loop.
- [Canonical state and migration authority](ADR-002-canonical-state-and-migration-authority.md)
  — Python mutation owner and UI projection boundary.
- [Existing Command Center plan](../aios-ui-command-center-implementation-plan.md)
  — source-backed overview and provenance strengths to preserve.
- `aios-ui/app/page.tsx`, `aios-ui/app/runs/page.tsx`,
  `aios-ui/components/layout/Sidebar.tsx`,
  `aios-ui/lib/constants.ts`, and `aios-ui/styles/globals.css` — current
  route, shell, navigation, and token evidence.
- Required context compile run on 2026-07-13 selected the AIOS UI,
  product-design, testing, security, observability, and approval-gate packets.
- Required shadow run `shadow-run-e61f34e9-ad23-45ad-8117-0df8d8481cf4` was
  trace-only because the baseline worktree was dirty; no shadow changes were
  merged or used as implementation evidence.
