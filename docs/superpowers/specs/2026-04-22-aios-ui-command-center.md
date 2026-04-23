# AIOS UI — Command Center Audit + Implementation Prompt

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Author:** jakyeamos
**Precedes:** `2026-04-08-aios-ui-design.md` (original UI spec, executed)

---

## Purpose

Audit the current AIOS_UI and implement the highest-leverage improvements to turn it into a true command center — a system monitor, control plane, knowledge browser, and workflow debugger in one surface. The overriding priority is maximum visibility, clarity, controllability, and trust.

---

## Prompt

You are performing an audit + implementation pass on AIOS_UI.

Goal:
Turn AIOS_UI into a true command center for the broader AIOS system, not just a UI. This is a complex setup with many moving parts, and the overriding priority is maximum visibility, clarity, controllability, and trust for the user. The result should help a human instantly understand what the system is doing, what is healthy, what is blocked, what is stale, what needs approval, what is improving, and where to act next.

Operating stance:
- Be opinionated.
- Make best-practice product and architecture decisions without waiting for me unless a decision is truly blocking.
- Large refactors are allowed if they materially improve maintainability, observability, or product quality.
- Prefer a clean control-center architecture over clever but fragile implementations.
- Treat this as a tier-one product review and build pass.
- Do not stop at "here are the findings." Implement the highest-leverage improvements in the same run.
- If the full ideal cannot be completed in one pass, leave behind a strong handoff document and truth files so the next run can continue cleanly.

Core product vision:
AIOS_UI should feel like the operating system surface area for my AI workflows:
- a command center
- a system monitor
- a control plane
- a knowledge browser
- a chat surface
- a workflow debugger
- a progress and experiment console
- a place where hidden automation becomes visible and understandable

The user should be able to answer, at a glance:
1. What is the system doing right now?
2. What changed recently?
3. What is healthy vs failing vs stale?
4. Which workflows, agents, prompts, rules, hooks, and cron jobs are active?
5. What requires my approval or intervention?
6. Where is quality improving or regressing?
7. Which experiments are running, which won, and what changed because of them?
8. What is the cost / latency / model-effort profile of the system?
9. What information is powering each conclusion?
10. What should I do next?

High-level mandate:
Audit the current AIOS_UI state against that ideal, identify the delta, then implement the highest-value improvements needed to move it toward a real command center.

Important context to preserve in your decisions:
- AIOS is evolving toward a sub-agent-driven system.
- Orchestration depth, runtime visibility, approvals, experiment tracking, workflow registry quality, and prompt/rule improvement over time are all important.
- There is strong product value in making hidden automation legible.
- The user wants maximum visibility across the whole stack, including workflows, experiments, prompts, rules, jobs, approvals, and execution state.
- This should support a wiki-like browse experience and a chat/Q&A surface, but the main focus here is command-center visibility and control.
- Dense information is good if it remains understandable.
- Every surface should answer a real operational question.

---

## Audit Dimensions

### 1. Information architecture
- Is the UI organized around how a human actually operates AIOS?
- Are the primary entities clear: projects, workflows, agents, runs, jobs, experiments, prompts, skills, rules, hooks, approvals, truth files, knowledge sources, alerts?
- Is there a coherent navigation model?
- Are critical relationships visible instead of buried?

### 2. Operational visibility
- Can the UI show live or near-live system state?
- Are statuses explicit, trustworthy, and source-backed?
- Are in_progress / failed / canceled / completed states driven by real runtime signals or only heuristics?
- Is staleness visible?
- Is ambiguity visible instead of hidden?

### 3. Control-plane clarity
- Can the user see what can be acted on?
- Are approvals, retries, reruns, resume points, blocked states, and queued work visible?
- Are workflow dependencies and orchestration paths understandable?
- Is there a visible distinction between observation and action?

### 4. Experimentation + improvement loops
- Are prompt/rule/skill/workflow experiments visible?
- Can the UI show variants, metrics, outcomes, winners, regressions, and rollouts?
- Is there a place to see how AIOS improves over time?
- Can the user understand why a format/rule/prompt is considered "proven"?

### 5. Auditability + trust
- Can the user trace each important UI claim back to a source of truth?
- Are timestamps, last-updated times, run lineage, and provenance visible?
- Is there a clear difference between inferred status and confirmed status?
- Are contradictions or drift surfaced instead of silently ignored?

### 6. Health + alerting
- Is there a system-health overview?
- Are failures, degraded subsystems, stale syncs, dead cron jobs, bad runs, and missing data made obvious?
- Are there alerts for things that matter, not just noise?
- Is there prioritization by severity and impact?

### 7. Knowledge + chat integration
- Does the UI support exploration of the system like a knowledge base?
- Can users ask questions grounded in visible data?
- Are important entities linkable and inspectable?
- Can the user move naturally between "browse", "inspect", and "ask"?

### 8. UX + usability
- Is the interface dense but legible?
- Are critical dashboards understandable without hunting?
- Are timelines, logs, and relationships digestible?
- Does the design feel like a serious operations product rather than a generic app dashboard?

### 9. Architecture + maintainability
- Is the current frontend architecture scalable for a command-center product?
- Are data fetching, state management, component boundaries, and domain models clean?
- Are views thin and logic consolidated?
- Are there obvious refactors needed to support future growth?

### 10. Missing surfaces
Identify major missing surfaces that a real command center should have.

---

## Required Product Surfaces

### A. Global command center homepage
A high-signal overview with:
- overall system health
- active runs / queued runs / blocked runs
- stale or failing jobs
- pending approvals
- recent major changes
- important alerts
- experiment activity
- cost / token / model usage snapshot
- "what needs attention now"

### B. Workflow and run observability
For each workflow / run:
- current status
- start/end/duration
- trigger source
- stage breakdown
- logs/events
- artifacts produced
- dependent systems
- retry / failure reason
- lineage / parent-child relationship
- whether status is real, inferred, or stale

### C. Agent registry / orchestration map
A surface that shows:
- what agents exist
- what each agent is for
- where each is invoked
- inputs / outputs
- connected tools / skills / rules
- current health and recent activity
- gaps between intended and real invocation

### D. Prompts / rules / skills / formats console
A surface that shows:
- active prompt formats
- where they are used
- which are experimental vs proven
- validation evidence
- recent edits
- dependencies on workflows or agent types
- rollout state
- regression risk
- linked experiments

### E. Experiment and learning console
A surface that shows:
- experiments running
- hypothesis
- variants
- metrics
- current best performer
- confidence / evidence
- rollout decisions
- follow-up recommendations
- historical improvement timeline

### F. Cron / jobs / automation console
A surface that shows:
- scheduled jobs
- last run
- next run
- status
- failure history
- missed runs
- runtime duration trends
- outputs produced
- downstream impact

### G. Approvals and interventions inbox
A surface that shows:
- pending approvals
- blocked proposals
- risky changes
- global proposals
- token-regressive or quality-regressive suggestions
- what action is needed and why

### H. Project / knowledge browser
A wiki-like browse experience for:
- projects
- truth files
- specs / PRDs
- implementation status
- linked workflows
- known risks
- latest changes
- related runs / artifacts / discussions

### I. Chat + grounded inspect mode
A chat surface tightly tied to visible system objects, so a user can ask:
- why is this failing?
- what changed yesterday?
- what experiments are improving output quality?
- which jobs are stale?
- what is blocking project X?
Answers should be grounded in visible entities, not detached from the command center.

### J. Change timeline / system history
A single timeline showing:
- deployments
- config changes
- workflow changes
- prompt/rule/skill changes
- approvals
- experiments started / stopped / promoted
- failures / recoveries
- major outputs

---

## Implementation Expectations

1. First, audit the existing codebase and produce a sharp gap analysis between current AIOS_UI and the ideal command center.
2. Then implement the highest-leverage improvements immediately.
3. Favor foundational architecture that unlocks future surfaces over shallow polish.
4. Add or improve domain models if the current ones are too weak for observability.
5. Make hidden state explicit.
6. Add source-backed status metadata wherever possible.
7. Distinguish:
   - confirmed state
   - inferred state
   - stale state
   - missing state
8. Where the backend or data model cannot yet support a perfect UI, create honest placeholders with explicit TODOs and schema recommendations rather than faking certainty.
9. Do not oversimplify away important system complexity. Surface it well.
10. Prefer maintainable architecture:
   - thin display pages
   - consolidated helper functions
   - reusable domain components
   - coherent data-fetching boundaries
   - explicit state modeling
   - scalable navigation patterns

---

## Execution Order

Work in this order unless the repo strongly suggests a better sequencing:
1. Audit current information architecture and domain model
2. Audit runtime / state / observability data sources
3. Define the target command-center IA
4. Refactor the app shell / navigation if needed
5. Implement the global command center homepage
6. Implement or improve the highest-value detail views
7. Add missing status badges, timestamps, provenance, and severity markers
8. Add experiment / approvals / automation visibility surfaces
9. Add or improve system timeline and intervention inbox
10. Leave behind a clear continuation plan for any remaining work

---

## Required Deliverables

1. `docs/aios-ui-command-center-audit.md`
   - current state summary, strengths, weaknesses, missing surfaces, architectural issues, data-model issues, observability issues, UX issues, prioritized recommendations, current → ideal delta

2. `docs/aios-ui-command-center-implementation-plan.md`
   - proposed IA, page/surface map, component/domain plan, data dependencies, staged rollout plan, unresolved backend dependencies, risks

3. `docs/aios-ui-command-center-handoff.md`
   - what was completed, what remains, exact next steps, blockers, recommended next prompts / run order

4. Update project truth file(s) to reflect command-center work done and gaps remaining

5. Commit in logical increments after major milestones

---

## Acceptance Criteria

The first implementation pass is complete only when all MVP criteria are true:
- the homepage gives immediate situational awareness from source-backed data
- workflow/run observability shows status, lineage, timestamps, events/logs, artifacts where available, and whether each status is confirmed, inferred, stale, or missing
- approvals/interventions have a visible inbox with clear action requirements and provenance
- the change timeline shows recent runs, approvals, prompt/rule/workflow changes, failures, and recoveries from available sources
- status/provenance helpers are modeled explicitly and reused across the MVP surfaces
- the repo includes `docs/aios-ui-command-center-audit.md`, `docs/aios-ui-command-center-implementation-plan.md`, and `docs/aios-ui-command-center-handoff.md`

The broader command-center target is complete when most of the following are true:
- AIOS_UI clearly reads as a command center, not a generic product dashboard
- the main navigation reflects the actual operational model of AIOS
- the homepage gives immediate situational awareness
- runs, workflows, jobs, prompts, experiments, approvals, and alerts have visible homes
- statuses are more explicit, trustworthy, and explainable than before
- hidden automation is significantly more visible
- the user can quickly identify failures, staleness, and required interventions
- there is a meaningful improvement in provenance, timestamps, and traceability
- the architecture is cleaner and more extensible than before
- the repo includes clear documentation of the gap, the implementation, and the remaining work

---

## What Not to Do
- Do not make this primarily a cosmetic redesign
- Do not hide complexity by removing important information
- Do not invent backend certainty where none exists
- Do not leave findings disconnected from implementation
- Do not overfit to a single page if the bigger issue is information architecture
- Do not preserve weak architecture just to minimize refactor size

---

## End-of-Run Output Format
1. Summary of what you audited
2. Key gaps found
3. What you implemented
4. What remains
5. Files changed
6. Recommended next steps
