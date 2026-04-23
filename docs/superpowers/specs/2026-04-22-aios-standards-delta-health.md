# AIOS Standards Delta / Project Health — Governance + Remediation Control Plane Prompt

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Author:** jakyeamos
**Scope:** AIOS UI + Taski integration

---

## Purpose

Add a first-class "Standards Delta / Project Health" system that measures each project against AIOS-defined standards, computes an explainable health score, and makes the path to backfilling the project to standard operationally clear.

**This is not a cosmetic scoring feature.** Treat it as a governance + remediation control plane for project quality.

**Core product idea:**
- AIOS defines the expected standard
- Each project is assessed against that standard
- The system computes delta from expectation
- That delta powers: health score, domain-level scores, regression visibility, prioritized Taski backfill tasks, trend reporting, migration visibility

---

## Prompt

You are working on the AIOS UI + Taski project management system.

Objective:
Add a first-class "Standards Delta / Project Health" system that measures each project against AIOS-defined standards and rules, computes an explainable health score, and makes the path to backfilling the project to standard operationally clear.

This is not a cosmetic scoring feature. Treat it as a governance + remediation control plane for project quality.

Your task:
Audit the current codebase and product model, then design and implement this system end-to-end. Large refactors are allowed if needed to make the architecture clean, maintainable, and extensible. Prefer durable primitives over one-off UI hacks.

---

### 1. Standards as First-Class Objects

Create a model for AIOS standards/rules/success criteria. Each standard is a structured object, not freeform prose.

Relationship to `spec/success-criteria/`:
- Success criteria are the judging rubrics used during agent work and workflow validation.
- Standards are project-health expectations used to assess and remediate projects over time.
- A standard may reference one or more success criteria as evaluation evidence, but 3b must not redefine the criteria schema created in 0c.
- If a criterion needs health-scoring metadata, add explicit mapping fields (`standard_id`, `domain`, `weight`, `evaluation_method`, `applicability`) rather than duplicating the criterion body in a second format.

Minimum fields:
- id
- title
- description
- domain
- weight
- severity_if_missing
- evaluation_method: `auto | semi_auto | manual`
- expected_state
- remediation_playbook
- blocking_dependencies
- version
- applicability rules
- waiver policy metadata

Domains must cover at minimum:
- architecture
- code quality
- testing
- security
- observability
- documentation
- workflow / agent control
- release / CI discipline
- product readiness

Make the system extensible so new domains and standards can be added without schema churn.

---

### 2. Project Assessments

Each project has an assessment layer recording current compliance against standards.

Supported statuses: `pass | partial | fail | unknown | waived | not_applicable`

Each assessment item stores:
- project_id
- standard_id
- status
- measured_state
- expected_state_snapshot
- reason
- evidence / source links where possible
- last_evaluated_at
- evaluator type
- confidence
- regression flag
- waiver rationale if waived
- owner if applicable

**Important:** Do not collapse `unknown` into `fail`. Unknown must remain visible — incomplete evaluation is itself a useful signal.

---

### 3. Health Score

Implement an explainable health score derived from standards delta.

**Health means:** "How closely does this project match its declared operational standard?"

Do not implement an opaque vibe-based score.

Scoring model:
- pass = 0 penalty
- partial = 0.5 × weight
- fail = 1.0 × weight
- unknown = 0.75 × weight
- regressed fail = 1.25 × weight
- waived = 0 penalty (visibly marked)
- not_applicable = excluded from denominator

Normalize to a 0–100 score.

Also compute:
- domain-level scores
- weighted delta
- unmet standards count
- critical delta count
- regression count
- unknown coverage
- evaluation confidence

Make the scoring engine configurable, not hardcoded into UI components.

---

### 4. Delta Model

Create a first-class `DeltaItem` concept representing the gap between expected and actual state.

Each delta item includes:
- project_id
- standard_id
- domain
- severity
- status
- why it is failing or partial
- remediation playbook reference
- estimated impact on health
- blockers / dependencies
- whether it is foundational or downstream
- linked Taski task ids if present
- created_at / updated_at

This is the primitive connecting standards evaluation to project management.

---

### 5. Taski Integration

Taski should become standards-aware.

For important delta items, generate or sync actionable tasks that include:
- linked standard id
- clear problem statement
- expected state
- acceptance criteria
- effort estimate if derivable
- dependency chain
- expected health impact
- owner
- priority
- blocked/unblocked state

Do not create generic debt tickets. Each Taski item must be traceable to a specific delta against a specific standard.

---

### 6. Prioritized Backfill Path

Implement a backfill prioritization system.

Do not rank only by severity. Use a composite formula:

```
priority = (severity × leverage × dependency_unlock × regression_penalty) / effort
```

The UI should classify backfill items into:
- foundational
- high leverage
- quick wins
- blocked
- waived / deferred

The user should see the shortest credible path to bringing a project closer to standard.

---

### 7. Standards Versioning and Migration Delta

Standards will evolve. Implement version-aware behavior to distinguish:
- project is failing its declared standard
from
- project met its previous standard but has not been upgraded to the latest AIOS standard set

Each project should show:
- current attached standards profile version
- latest standards version
- delta introduced by newer standards
- migration backlog required to upgrade

---

### 8. Waivers and Deferrals

Support waivers, but make them structured and reviewable.

Required fields:
- rationale
- owner
- review date or expiration
- whether waiver affects portfolio reporting

Waivers must be visible in UI and must not silently remove debt from view.

---

### 9. Portfolio and Project UI

#### Portfolio / Overview Level
Each project card shows:
- health score
- trend
- critical delta count
- top failing domains
- backfill status
- unknown coverage

#### Project Detail View

**A. Health Header**
- overall score, trend, target score, last evaluated timestamp, confidence

**B. Domain Breakdown**
- architecture, testing, security, docs, observability, workflow, etc.

**C. Delta Matrix**
Standards table with filters for: failing, unknown, critical, waived, domain, auto vs manual evaluations

**D. Backfill Lane**
Prioritized remediation showing: what to do first, what unlocks the most improvement, what is blocked, what has the biggest score impact

**E. Standards Migration View**
Newly introduced requirements not yet backfilled.

The UX should feel like a control center, not a spreadsheet dump.

---

### 10. Trend and History

Persist enough history to show:
- health score over time
- domain score trends
- regressions introduced
- backfill completed
- standards coverage changes
- version migration progress

---

### 11. Evaluation Architecture

Design assessments to come from:
- automated evaluators
- semi-automated review flows
- manual assessments

Do not tightly couple to one evaluation source. If automated evaluators already exist, wire them in. If not, create clean interfaces/stubs.

---

### 12. Explainability

Every score and every delta must be inspectable. A user should be able to answer:
- Why is this project at 68 and not 81?
- Which standards are driving the score down?
- Which unknowns are lowering confidence?
- What 3 tasks would improve this the most?
- What changed recently?
- Is the project regressing or just incomplete?
- Is the gap due to old standards or true failure?

---

### 13. Architecture Expectations

Prioritize:
- maintainability
- strong typing
- thin display pages
- consolidated helper/service layers
- clear domain models
- testability
- separation of scoring logic from presentation
- future support for new standards, projects, evaluators, and UI surfaces

Avoid:
- hardcoding scoring logic into components
- freeform JSON blobs where domain models should exist
- magical numbers with no config
- UI-only implementations with no durable backend/domain layer
- fake demo data masquerading as finished architecture

---

### 14. Deliverables

**A. Audit**
- current state
- gaps versus target architecture
- risks
- what must change structurally

**B. Implementation**
- schema/domain model changes
- service layer
- scoring engine
- delta generation
- Taski integration
- UI views/components
- trend/history support

**C. Documentation**
- system architecture overview
- scoring model explanation
- how standards are defined
- how projects are assessed
- how backfill prioritization works
- how waivers/versioning work

**D. Seed Standards**
Create a reasonable starter standards profile for AIOS so the feature is functional, not empty.

**E. Tests**
- scoring
- delta generation
- prioritization
- waiver handling
- standards versioning
- UI-critical logic where appropriate

---

### 15. Execution Style

Work iteratively but decisively. Do not stay at the discussion layer. Make best-practice choices without unnecessary back-and-forth. If the codebase is weak in this area, improve it aggressively.

As you work:
- keep architecture clean
- update any truth/state docs if the repo uses them
- document assumptions
- leave the codebase in a more coherent state than you found it

---

### Definition of Done

- projects can be measured against structured AIOS standards
- a real health score is computed from explainable delta
- domain scores and confidence are visible
- unknowns, regressions, waivers, and version gaps are handled explicitly
- Taski can show actionable remediation tied to standards delta
- the UI clearly shows the best path to backfill a project to standard
- the system is architected to grow with AIOS rather than needing a rewrite later

---

### North Star

When a user opens AIOS, they should immediately understand:
- which projects are healthiest
- which are farthest from standard
- which are regressing
- what is missing vs merely unevaluated
- what few actions would most improve a project
- what backfill path gets the repo closest to target standard fastest

Do not implement a vanity score. Implement a standards delta system that makes project quality measurable, auditable, and operationally improvable.
