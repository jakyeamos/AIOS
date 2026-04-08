---
type: spec
title: Knowledge / Hypotheses / Rules Layer
date: 2026-04-03
status: approved
author: jakyeamos
approach: extend-existing-patterns-table
---

# Knowledge / Hypotheses / Rules Layer — Design Spec

## Summary

A structured knowledge layer that accumulates facts, promotes patterns into
validated rules, tracks hypotheses under testing, and injects actionable
knowledge into session context automatically.

Architecture: **Option A + Approach 3** — extend the existing `patterns` table
(no parallel tables), SQLite is authoritative, vault domain files are
auto-generated from SQLite (never hand-edited).

---

## 1. Executive Assessment

**Worth adding: yes, urgently.**

The system is 60% built. The patterns table, extract/promote pipeline, hook
chain, and vault destination all exist. What is missing: states with meaning,
provenance with structure, domain routing, and retrieval integration for rules.

**First action required:** quarantine the 10 existing bigram-promoted stubs
(set `human_approved=0`). They are noise and must not be injected as rules.

**Critical prerequisites before enabling rule injection:**
1. Complete Phase 1 schema migration
2. Run `review-observations.py` first pass on 35 existing patterns
3. Manually approve 3–5 high-signal patterns to `rule` state
4. Only then enable `rules_retrieval` in `retrieval-policy.json`

---

## 2. Model Summary

```
Source layer
  sessions / prompts_used / bug_log / tool_events / handoffs / decisions / archive

Extraction layer
  extract-patterns.py (bigram, structured)
  agent-synthesis.py (weekly, Phase 3)

State machine (SQLite patterns table, extended)
  observation → knowledge → hypothesis → rule → dormant

pattern_events table (provenance — append-only)

build-domain-files.py (weekly, on-demand)
  generates: 06 Knowledge/Domains/<domain>/rules.md
             06 Knowledge/Domains/<domain>/hypotheses.md
             06 Knowledge/Domains/INDEX.md

Hook injection
  hook-session-start.py → top rules for project domain
  hook-prompt-submit.py → domain-matched rules per classification
```

---

## 3. State Machine

| State | Meaning | How entered | How exited |
|---|---|---|---|
| `observation` | Raw extracted signal | extraction, agent synthesis, manual | review → knowledge or discarded |
| `knowledge` | Confirmed fact; not yet a default behavior | manual review | first confirmation → hypothesis |
| `hypothesis` | Being tested; surfaced but not applied by default | first confirmation event | threshold met + human approved → rule; contradiction → knowledge; 90 days stale → dormant |
| `rule` | Default behavior; injected into session context | human_approved=1 + all gates pass | any contradiction → hypothesis |
| `dormant` | Inactive or superseded | 90 days without confirmation | new confirmation → knowledge |

**Transitions that are deterministic (no human required):**
- extraction → observation
- observation → discarded (noise filter)
- knowledge → hypothesis (on first confirmation event)
- rule → hypothesis (on any contradiction event, immediate)
- hypothesis → dormant (weekly cron, 90-day staleness)
- dormant → knowledge (new confirmation event)

**Transitions that require human review:**
- observation → knowledge (weekly review pass)
- hypothesis → rule (always — `human_approved=1` must be set manually)
- discarded (only manual)

---

## 4. Domain Structure

### Vault layout

```
06 Knowledge/
  Domains/
    INDEX.md                    ← auto-generated
    debugging/
      rules.md
      hypotheses.md
      knowledge.md
    prompting/
      rules.md
      hypotheses.md
      knowledge.md
    architecture/
      rules.md
      hypotheses.md
      knowledge.md
    workflow/
      rules.md
      hypotheses.md
      knowledge.md
    system/
      rules.md
      hypotheses.md
      knowledge.md
  Wiki/                         ← human-curated, unchanged
  Claude-Context/               ← unchanged
  Research/                     ← unchanged
```

### Domain classification

| Domain | Pattern classes | Source material |
|---|---|---|
| `debugging` | bug_fix, failure | bug_log, debug prompts |
| `prompting` | prompt | prompts_used, prompt library |
| `architecture` | architecture, refactor | decision notes, plan prompts |
| `workflow` | workflow, assumption | session handoffs, next-action verbs |
| `system` | any (AIOS-specific) | AIOS sessions, hooks, second brain |

Project-specific domains (e.g., `fantasy/debugging`) are added only when
a project accumulates 10+ patterns in a domain. Do not create speculatively.

### Domain file format

```markdown
<!-- AUTO-GENERATED: do not edit above this line -->

---
domain: debugging
generated: 2026-04-03T09:00:00Z
rule_count: 3
---

# Debugging Rules

_Auto-generated from aios.db. Edit via confirm-pattern.py / contradict-pattern.py._

## Nullable relation type errors after Prisma schema change

**When:** TS error after adding optional relation to Prisma schema
**Do:** Check all query sites for non-null assertions; run `prisma generate` first
**Confidence:** 0.87 | **Confirmed:** 4× | **Last:** 2026-03-28

---

<!-- END AUTO-GENERATED -->

## Notes

<!-- Human annotations, exceptions, context — edit freely below this line -->
```

The `build-domain-files.py` script regenerates everything above
`<!-- END AUTO-GENERATED -->` and preserves everything below it.

---

## 5. Schema Design

### Extended `patterns` table

```sql
-- New columns (migration, backward-safe)
ALTER TABLE patterns ADD COLUMN domain TEXT DEFAULT 'unclassified';
ALTER TABLE patterns ADD COLUMN state TEXT DEFAULT 'observation';
ALTER TABLE patterns ADD COLUMN body TEXT;
ALTER TABLE patterns ADD COLUMN source_type TEXT DEFAULT 'bigram';
ALTER TABLE patterns ADD COLUMN confirmation_count INTEGER DEFAULT 0;
ALTER TABLE patterns ADD COLUMN contradiction_count INTEGER DEFAULT 0;
ALTER TABLE patterns ADD COLUMN last_confirmed_at TEXT;
ALTER TABLE patterns ADD COLUMN last_contradicted_at TEXT;
ALTER TABLE patterns ADD COLUMN first_observed_at TEXT;
ALTER TABLE patterns ADD COLUMN human_approved INTEGER DEFAULT 0;
ALTER TABLE patterns ADD COLUMN project_id TEXT REFERENCES projects(id);

-- Migration of existing data
UPDATE patterns SET state = 'rule'        WHERE status = 'promoted';
UPDATE patterns SET state = 'observation' WHERE status = 'candidate';
UPDATE patterns SET state = 'observation' WHERE status = 'discarded';  -- intentional: old bigram noise was never human-reviewed; re-review under new system
UPDATE patterns SET human_approved = 0;   -- quarantine all existing; nothing injects until manually approved
UPDATE patterns SET first_observed_at = created_at WHERE first_observed_at IS NULL;

-- Indexes
CREATE INDEX idx_patterns_domain ON patterns(domain);
CREATE INDEX idx_patterns_state ON patterns(state);
CREATE INDEX idx_patterns_confidence ON patterns(confidence);
```

### New `pattern_events` table

```sql
CREATE TABLE pattern_events (
  id            TEXT PRIMARY KEY,
  pattern_id    TEXT NOT NULL REFERENCES patterns(id),
  event_type    TEXT NOT NULL,  -- observation|confirmation|contradiction|promotion|demotion|manual_review
  session_id    TEXT REFERENCES sessions(id),
  source_type   TEXT NOT NULL DEFAULT 'manual',
  source_id     TEXT,
  source_path   TEXT,
  notes         TEXT,
  event_time    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX idx_pevents_pattern ON pattern_events(pattern_id);
CREATE INDEX idx_pevents_type ON pattern_events(event_type);
CREATE INDEX idx_pevents_time ON pattern_events(event_time);
```

### Useful views

```sql
CREATE VIEW active_rules AS
  SELECT * FROM patterns
  WHERE state = 'rule' AND human_approved = 1
  ORDER BY confidence DESC;

CREATE VIEW active_hypotheses AS
  SELECT *,
    (CASE class
       WHEN 'bug_fix'      THEN 2
       WHEN 'failure'      THEN 2
       WHEN 'architecture' THEN 3
       WHEN 'workflow'     THEN 3
       WHEN 'assumption'   THEN 3
       WHEN 'prompt'       THEN 4
       ELSE 3
     END - confirmation_count) AS confirmations_needed
  FROM patterns
  WHERE state = 'hypothesis'
  ORDER BY confirmations_needed ASC;

CREATE VIEW domain_stats AS
  SELECT
    domain,
    SUM(CASE WHEN state='rule'        THEN 1 ELSE 0 END) AS rule_count,
    SUM(CASE WHEN state='hypothesis'  THEN 1 ELSE 0 END) AS hypothesis_count,
    SUM(CASE WHEN state='knowledge'   THEN 1 ELSE 0 END) AS knowledge_count,
    SUM(CASE WHEN state='observation' THEN 1 ELSE 0 END) AS observation_count,
    MAX(last_confirmed_at) AS last_activity
  FROM patterns GROUP BY domain;
```

---

## 6. Provenance and Evidence Model

All evidence lives in `pattern_events` (append-only). Each event has:

- `source_type`: `session | bug | handoff | archive | prompt | manual | experiment`
- `source_id`: PK in the source table (`bug_log.id`, `sessions.id`, etc.)
- `source_path`: vault path if source is a note

`patterns.confirmation_count` and `contradiction_count` are denormalized counters
updated atomically when events are inserted. Do not recount from events on each
read. Events are the audit trail; counters drive logic.

### Confidence formula

```
On each confirmation:  confidence = min(confidence + 0.05, 0.95)
On each contradiction: confidence = max(confidence - 0.15, 0.10)
```

Confidence is a live signal, not a static extraction artifact. It starts at the
extracted value and evolves with evidence.

### Promotion gates for hypothesis → rule (all four must pass)

1. `confirmation_count >= class_threshold`
2. `first_observed_at` is at least 14 days ago
3. Confirmations span at least 2 distinct session IDs
4. `human_approved = 1` (set manually via `approve-pattern.py`)

---

## 7. Confirmation Thresholds by Class

| Class | Threshold | Rationale |
|---|---|---|
| bug_fix | 2 | Recurring bugs are high signal |
| failure | 2 | Failure patterns are costly; fast promotion is protective |
| architecture | 3 | Design decisions need sufficient evidence |
| workflow | 3 | Workflow patterns need repetition |
| assumption | 3 | Assumptions need testing before hardening |
| prompt | 4 | Prompt bigrams are noisy; require more evidence |

---

## 8. Retrieval Integration

### SessionStart — inject active rules

After the existing session packet (current focus, open actions, open bug),
query `active_rules` filtered by project domain. Inject top 5 by confidence.
Budget: ~200 chars. Format:

```
**Active rules (debugging):**
- [rule title] — [one-line action]
```

Surface at most 1 testable hypothesis:

```
**Testing (debugging):** [hypothesis title] (2/3 confirmations)
```

### UserPromptSubmit — domain-matched retrieval

Add to `retrieval-policy.json`:

```json
"rules_retrieval": {
  "enabled": false,
  "debug":     { "domain": "debugging",    "max_rules": 3, "min_confidence": 0.70 },
  "plan":      { "domain": "architecture", "max_rules": 2, "min_confidence": 0.75 },
  "refactor":  { "domain": "architecture", "max_rules": 2, "min_confidence": 0.75 },
  "implement": { "domain": "workflow",     "max_rules": 2, "min_confidence": 0.70 }
}
```

Start with `enabled: false`. Enable only after Phase 2 review confirms quality.

### When to stay latent

- No approved rules exist for the domain
- All matching rules have `confidence < 0.60`
- Session is classified as `other` or `explain`
- Session packet is already at `MAX_PACKET_CHARS`

---

## 9. Pattern Classes

| Class | Domain | What it captures |
|---|---|---|
| `bug_fix` | debugging | Recurring failure modes + fix chains |
| `failure` | debugging | Repeated failure modes across sessions |
| `prompt` | prompting | Prompt structures that reliably work |
| `architecture` | architecture | Design decisions that recur across projects |
| `workflow` | workflow | Recurring task decomposition patterns |
| `assumption` | workflow | Recurring assumptions made without verification |
| `refactor` | architecture | Recurring code quality opportunities |

### Extraction sources

| Source | Method | Output |
|---|---|---|
| `prompts_used` | Bigram frequency by classification | prompt class |
| `bug_log` (symptom) | Bigram frequency | bug_fix class |
| `bug_log` (root_cause + fix both non-null) | Structured pairing | bug_fix class |
| Session handoffs (Next Actions verbs) | Verb frequency | workflow class |
| Agent synthesis over handoffs | Weekly batch (Phase 3) | any class |

All extraction writes `state='observation'`, `source_type` set appropriately,
`human_approved=0`. No extraction auto-promotes past `knowledge`.

---

## 10. Script Inventory

### Create

| Script | Purpose |
|---|---|
| `migrate-patterns.py` | One-time: ALTER TABLE, create pattern_events, migrate data |
| `review-observations.py` | CLI: list observations, approve/discard/annotate |
| `approve-pattern.py` | CLI: set human_approved=1, validate all 4 promotion gates |
| `confirm-pattern.py` | CLI: record confirmation event, update count, flag threshold |
| `contradict-pattern.py` | CLI: record contradiction, demote rule→hypothesis |
| `build-domain-files.py` | Generate Domains/ vault files from SQLite |
| `agent-synthesis.py` | Weekly handoff synthesis → staging JSON (Phase 3) |
| `import-pattern-candidates.py` | Import staging JSON into patterns as observations (Phase 3) |

### Modify

| Script | Change |
|---|---|
| `extract-patterns.py` | Add `domain` field; write `state='observation'`; add bug→fix pairing |
| `promote-patterns.py` | Replace threshold logic with state machine; respect `human_approved` gate |
| `hook-session-start.py` | Add `get_active_rules()` and rules injection block |
| `hook-prompt-submit.py` | Add `rules_retrieval` retrieval step from retrieval-policy.json |
| `hook-stop.py` | Flag sessions with reusable prompts or resolved bugs for review |
| `weekly-maintenance.sh` | Add: `build-domain-files.py`, `agent-synthesis.py`, `age-patterns.py` |
| `vault-lint.py` | Add: approved=0 rules, stale domains, count sync checks |

---

## 11. Migration Plan

### Phase 1 — Foundation (no behavioral change)

1. Run `migrate-patterns.py` — schema extension + data migration
2. Create `06 Knowledge/Domains/` folder structure
3. Write and run `build-domain-files.py` (initial empty/sparse domain files)
4. Update `extract-patterns.py` (domain field, state column)
5. Update `promote-patterns.py` (state machine, human_approved gate)
6. Add `build-domain-files.py` to `weekly-maintenance.sh`
7. Add `rules_retrieval` block to `retrieval-policy.json` (`enabled: false`)

### Phase 2 — Activation (behavioral change)

8. Write `review-observations.py`, run first review pass on 35 existing patterns
9. Write `approve-pattern.py`, approve 3–5 high-signal patterns to rule state
10. Enable `rules_retrieval` in retrieval-policy.json
11. Modify `hook-session-start.py` (rules injection)
12. Modify `hook-prompt-submit.py` (rules retrieval)
13. Write `confirm-pattern.py` and `contradict-pattern.py`

### Phase 3 — Corpus integration (when corpus is large enough to warrant)

14. Write `agent-synthesis.py` and `import-pattern-candidates.py`
15. Add agent synthesis to weekly-maintenance.sh
16. Modify `hook-stop.py` (insight flagging)
17. Add health checks to `vault-lint.py`
18. Add project domains when any project hits 10+ project-specific patterns

---

## 12. Anti-Patterns (Do Not Do These)

- **Do not auto-promote hypothesis → rule.** Human approval gate is mandatory.
- **Do not approve existing bigram stubs.** They must be reviewed and given
  semantic `body` content before any are considered for promotion.
- **Do not let `rules.md` exceed 10 entries per domain.** Max 10 active rules
  per domain. Prune dormant patterns or split the domain.
- **Do not write to `Domains/` files manually.** They are generated output.
  Write annotations only below `<!-- END AUTO-GENERATED -->`.
- **Do not merge `experiments` table into this layer.** They are different
  constructs. An experiment can produce a `pattern_events` row as evidence,
  but they are not the same thing.
- **Do not extract from raw `tool_events` or `prompts_used` in agent synthesis.**
  Use handoffs (already filtered). Raw event data is too noisy.
- **Do not build for the corpus that doesn't exist yet.** Scale extraction
  when the corpus is ingested, not in anticipation of it.
- **Do not make contradictions silent.** Every contradiction must appear in
  vault file provenance summary, weekly maintenance log, and vault-lint output.
- **Do not confuse frequency with usefulness.** A bigram appearing 12 times
  in prompts is a recurring topic, not a rule.
