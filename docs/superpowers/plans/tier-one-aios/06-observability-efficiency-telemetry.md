# Observability Efficiency And Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make telemetry actionable: cost, waste, value, reliability, failures, and urgency should explain what changed and what matters.

**Architecture:** Telemetry surfaces should classify states before rendering numbers. Zeroes need explanation. Failures need source records. Trends need enough history to be meaningful.

**Tech Stack:** Python RTK services, SQLite telemetry tables, Next.js costs/automations pages, tRPC routers, pytest.

---

## Files

- Modify: `services/rtk_integration.py`
- Modify: `services/aios_cli.py`
- Modify: `aios-ui/server/routers/costs.ts`
- Modify: `aios-ui/server/routers/automations.ts`
- Modify: `aios-ui/app/costs/page.tsx`
- Modify: `aios-ui/app/automations/page.tsx`
- Modify: `tests/test_rtk_integration.py`
- Modify: `tests/test_aios_cli.py`
- Modify after each code commit: `PROJECT.md`

### Task 1: RTK State Machine

**Files:**
- Modify: `services/rtk_integration.py`
- Modify: `aios-ui/server/routers/costs.ts`
- Test: `tests/test_rtk_integration.py`

- [ ] **Step 1: Canonical RTK states**

Use:

- `active`
- `inactive`
- `no_eligible_data`
- `misconfigured`
- `token_regressive`

- [ ] **Step 2: Explain zero values**

If tokens saved is zero, classify why:

- no eligible runs
- compression disabled
- compressed output larger than raw
- no RTK events

### Task 2: Efficiency Value Metrics

**Files:**
- Modify: `aios-ui/server/routers/costs.ts`
- Modify: `aios-ui/app/costs/page.tsx`

- [ ] **Step 1: Add value alongside cost**

Efficiency page should show:

- total tokens
- abandoned session tokens
- failed run tokens
- successful run tokens
- tokens per completed run
- token-regressive count
- trend if enough history exists

- [ ] **Step 2: Add actionability**

Each classification must explain what it means operationally without prescribing redesigns in the metric layer.

### Task 3: Automation Reliability Model

**Files:**
- Modify: `aios-ui/server/routers/automations.ts`
- Modify: `aios-ui/app/automations/page.tsx`

- [ ] **Step 1: Replace raw schedule primary display**

RRULE stays available as secondary evidence. Primary display should show readable schedule, next run, last run, last failure, and success rate.

- [ ] **Step 2: Add urgency**

Automation statuses:

- `healthy`
- `warning`
- `error`
- `stale`
- `disabled`
- `unknown`

Urgency should be based on last failure, missed schedule, approval waiting, and writeback proposals.

### Task 4: Recent Failures Unification

**Files:**
- Modify: `services/aios_cli.py`
- Modify: `aios-ui/server/routers/insights.ts`

- [ ] **Step 1: Combine failure sources**

Unify:

- orchestration failures
- bug log
- automation failures
- failed validation findings
- standards blockers

- [ ] **Step 2: Add source links**

Every failure item must include source table/id and href if UI routable.

### Tier-One Telemetry Acceptance

- [ ] no unexplained zero values
- [ ] no raw RRULE primary display
- [ ] efficiency metrics separate cost, waste, and value
- [ ] automation failures include urgency and last failure reason
- [ ] recent failures are unified across surfaces
