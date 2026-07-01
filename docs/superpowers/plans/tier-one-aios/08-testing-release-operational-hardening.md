# Testing Release And Operational Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make AIOS reliable enough to operate as the default command center without silent regressions.

**Architecture:** Establish a test pyramid around runtime contracts, CLI audits, service modules, UI type safety, and screenshot-backed confusion regressions. Release gates must be local-first and CI-ready.

**Tech Stack:** pytest, pnpm lint/typecheck, Next.js build, SQLite fixture DBs, GitHub Actions.

---

## Files

- Modify: `.github/workflows/aios-ui-quality.yml`
- Add: `.github/workflows/aios-python-quality.yml`
- Modify: `README.md`
- Modify: `tests/test_aios_cli.py`
- Modify: `tests/test_orchestration_runtime.py`
- Add: `tests/test_tier_one_regressions.py`
- Modify: `aios-ui/package.json`
- Modify after each code commit: `PROJECT.md`

### Task 1: Make Python Suite Green

**Files:**
- Modify files required by the failing test
- Test: `tests/test_orchestration_runtime.py`

- [ ] **Step 1: Run suite**

```bash
uv run pytest -q
```

Expected before work: 115 passing, 1 failing managed runtime test.

- [ ] **Step 2: Fix runtime failure**

Follow [Runtime Task 1](./01-runtime-and-invocation-reliability.md#task-1-repair-managed-runtime-completion).

- [ ] **Step 3: Verify**

```bash
uv run pytest -q
```

Expected: all pass.

### Task 2: Add Tier-One Regression Tests

**Files:**
- Add: `tests/test_tier_one_regressions.py`

- [ ] **Step 1: Add CLI regression tests**

Cover:

- no unsupported lifecycle states
- contracts audit includes seven canonical contracts
- capability audit reports missing data reasons
- knowledge objects report source coverage
- workflow learning audit reports no-learning count

- [ ] **Step 2: Add screenshot-backed regressions**

At service/CLI level, assert:

- pipeline contradiction is not primary `0/5 ERROR`
- RTK zero has explanation
- health parenthetical is not the only trend indicator
- automation raw RRULE is not the primary schedule label

### Task 3: CI Quality Gate

**Files:**
- Add: `.github/workflows/aios-python-quality.yml`
- Modify: `.github/workflows/aios-ui-quality.yml`

- [ ] **Step 1: Python workflow**

Run:

```bash
uv run pytest -q
```

- [ ] **Step 2: UI workflow**

Run:

```bash
cd aios-ui
pnpm install --frozen-lockfile
pnpm lint
pnpm build
```

- [ ] **Step 3: Document local parity**

Update `README.md` so local quality checks match CI.

### Task 4: Warning Ratchet

**Files:**
- Modify: `aios-ui/.config/anti-slop.json`
- Modify: `aios-ui/eslint.config.mjs`

- [ ] **Step 1: Record current warning baseline**

Current known UI lint state includes anti-slop warnings. Either fix them or explicitly ratchet the allowed count.

- [ ] **Step 2: Prevent growth**

CI should fail if warnings increase above baseline.

### Tier-One Hardening Acceptance

- [ ] Python suite green
- [ ] UI lint/typecheck green
- [ ] UI build green
- [ ] CI mirrors local checks
- [ ] screenshot-backed confusion cases have regression coverage
- [ ] warning baseline cannot grow silently
