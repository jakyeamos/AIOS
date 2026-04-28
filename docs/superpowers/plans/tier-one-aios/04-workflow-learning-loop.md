# Workflow Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AIOS improve workflows from evidence instead of only displaying run history.

**Architecture:** Terminal runs produce classified learning events. Learning events can become workflow proposals, prompt strategy proposals, standards-health evidence, bug/quality findings, or explicit no-learning signals. Promotions require durable rationale.

**Tech Stack:** Python services, SQLite writebacks, workflow registry JSON, Next.js workflow UI, pytest.

---

## Files

- Modify: `services/workflow_synthesis.py`
- Modify: `services/aios_cli.py`
- Modify: `bin/hook-stop.py`
- Modify: `aios-ui/server/aios/learning.ts`
- Modify: `aios-ui/server/routers/workflows.ts`
- Modify: `aios-ui/app/workflows/page.tsx`
- Modify: `tests/test_workflow_synthesis.py`
- Modify: `tests/test_aios_cli.py`
- Modify after each code commit: `PROJECT.md`

## Evidence Types

Canonical evidence types:

- `workflow_evidence`
- `prompt_template_evidence`
- `standards_health_evidence`
- `bug_quality_evidence`
- `no_learning_signal`

### Task 1: Persist WorkflowLearningEvent

**Files:**
- Modify: `services/workflow_synthesis.py`
- Modify: `bin/aios_orchestration_runtime.py`
- Test: `tests/test_workflow_synthesis.py`

- [ ] **Step 1: Add schema**

Create table:

```sql
CREATE TABLE IF NOT EXISTS workflow_learning_events (
  id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES orchestration_runs(id),
  evidence_type TEXT NOT NULL,
  proposal_target TEXT,
  confidence REAL NOT NULL DEFAULT 0.5,
  approval_state TEXT NOT NULL DEFAULT 'not_required',
  rationale TEXT NOT NULL,
  source_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
```

- [ ] **Step 2: Insert event on terminal closeout**

On `hook-stop.py`, classify completed, failed, canceled, and abandoned runs.

- [ ] **Step 3: Avoid duplicate learning events**

Use `run_id + evidence_type + proposal_target` as logical uniqueness.

### Task 2: Promotion Gates

**Files:**
- Modify: `services/workflow_synthesis.py`
- Modify: `aios-ui/server/routers/workflows.ts`

- [ ] **Step 1: Gate repeated patterns**

Workflow proposal requires:

- at least two supporting terminal runs or one high-confidence explicit operator proposal
- no unresolved failed-validation blocker
- cited run evidence

- [ ] **Step 2: Gate prompt changes**

Prompt strategy proposal requires:

- prompt hash or template key
- evidence of repeated reuse or failure recovery
- approval if it changes default packet content

- [ ] **Step 3: Preserve rejection rationale**

Rejected proposals must write decision actor, note, timestamp, and resulting state.

### Task 3: No-Learning Signals

**Files:**
- Modify: `services/aios_cli.py`
- Modify: `aios-ui/server/aios/learning.ts`

- [ ] **Step 1: Classify no-learning explicitly**

Runs with no durable reusable signal should create a no-learning event with rationale:

- one-off task
- insufficient evidence
- failed before useful artifact
- missing closeout summary

- [ ] **Step 2: Audit no-learning volume**

`workflow-learning-audit` should report no-learning reasons by count.

### Task 4: Workflow UI

**Files:**
- Modify: `aios-ui/app/workflows/page.tsx`
- Modify: `aios-ui/server/routers/workflows.ts`

- [ ] **Step 1: Show proposal queue**

Columns:

- target
- evidence type
- supporting runs
- confidence
- approval state
- rationale

- [ ] **Step 2: Show accepted/rejected history**

Accepted/rejected proposals should not disappear.

### Tier-One Workflow Learning Acceptance

- [ ] terminal runs produce learning or no-learning events
- [ ] repeated successful patterns create reviewable proposals
- [ ] failed or abandoned runs create diagnostic findings
- [ ] proposal approvals and rejections preserve rationale
- [ ] workflow registry changes cite evidence
