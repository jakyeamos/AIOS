# Projects Standards And Quality Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make project health comparable, source-backed, and actionable across linked repositories.

**Architecture:** Project health must be derived from standards snapshots, quality pipeline gates, runtime findings, and missing-data reasons. Every displayed project metric must be a trusted signal.

**Tech Stack:** Python standards services, SQLite, Next.js project routers, quality pipeline config, pytest, TypeScript.

---

## Files

- Modify: `services/standards_health.py`
- Modify: `services/quality_pipeline.py`
- Modify: `services/project_inventory.py`
- Modify: `services/capability_truth.py`
- Modify: `aios-ui/server/routers/projects.ts`
- Modify: `aios-ui/server/aios/quality-pipeline.ts`
- Modify: `aios-ui/app/projects/page.tsx`
- Modify: `aios-ui/app/projects/[id]/page.tsx`
- Modify: `tests/test_standards_health.py`
- Modify: `tests/test_quality_pipeline.py`
- Modify after each code commit: `PROJECT.md`

### Task 1: Project Profile Ratchet

**Files:**
- Modify: `config/architecture-enforcement/projects.json`
- Modify: `config/quality-pipeline.json`
- Modify: `services/project_inventory.py`

- [ ] **Step 1: Define priority project profiles**

Priority repos:

- `AIOS`
- `soundscape-app`
- `Terrace`
- `portfolio`
- `GitNexus`
- `amos-saas`

For each, define:

- repo path
- standards profile ids
- quality gates
- proof target flag
- expected CI command if known

- [ ] **Step 2: Represent missing repos explicitly**

If path does not exist, project health should be `missing_source`, not `active`.

### Task 2: Health Score Explainability

**Files:**
- Modify: `services/standards_health.py`
- Modify: `aios-ui/server/routers/projects.ts`

- [ ] **Step 1: Add score component breakdown**

Health snapshot should expose:

- base score
- weighted delta
- max penalty
- critical delta count
- unknown count
- unknown coverage
- confidence

- [ ] **Step 2: Render breakdown**

Project detail must show score reason and source snapshot id.

### Task 3: Pipeline State Normalization

**Files:**
- Modify: `services/quality_pipeline.py`
- Modify: `aios-ui/server/aios/quality-pipeline.ts`
- Test: `tests/test_quality_pipeline.py`

- [ ] **Step 1: Canonical gate statuses**

Use only:

- `pass`
- `fail`
- `running`
- `stale`
- `missing`
- `blocked`
- `unknown`

- [ ] **Step 2: Reject contradictory primary labels**

`0/5 ERROR` must be represented as contradiction or missing configuration, not rendered as failing checks.

### Task 4: Missing Data As First-Class Health

**Files:**
- Modify: `services/capability_truth.py`
- Modify: `aios-ui/server/routers/projects.ts`

- [ ] **Step 1: Missing health snapshots**

Projects without standards health snapshots should show:

- value: `null`
- provenance: `missing`
- missing reason: `No standards_health_snapshots row exists for this project.`

- [ ] **Step 2: Missing pipeline config**

Projects without required gates should show missing configuration, not healthy active status.

### Tier-One Projects Acceptance

- [ ] every project health metric has source/freshness/confidence
- [ ] priority repos have comparable profiles
- [ ] missing repo paths are visible
- [ ] no broad `ACTIVE` status without meaningful subtype
- [ ] health scores include component explanation
- [ ] project dashboard supports decision-making, not only status display
