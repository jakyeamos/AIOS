# AI History Import/Archive Subsystem — Design Spec

**Date:** 2026-04-01  
**Status:** Implemented in `/Users/jakyeamos/AIOS` main worktree; real ChatGPT import still pending export availability  
**Scope:** Additive module for importing ChatGPT exports, Claude export-bundle conversations, and Codex local session history into the existing hybrid AIOS architecture  
**Scale:** Hundreds of conversations  
**Pipeline approach:** Script-driven batch pipeline with staged review (Approach A)

## Implementation Update (2026-04-02)

- Completed live imports:
  - Claude batch `20260402033854--claude`: 145 total, 59 promoted, 86 deferred
  - Codex batch `20260402034120--codex`: 314 total, 57 promoted, 257 deferred
- ChatGPT real import is still pending because no export is available yet.
- Deferred semantics were refined during implementation: `deferred` means individually thin, not discarded. Deferred notes remain staged, are included in aggregate pattern analysis, and can be promoted later with `promote-imports.sh --include-deferred`.
- The actual execution order diverged from the original plan because ChatGPT data was unavailable: infrastructure first, then review/promote scripts, dedup coverage, Claude import, Codex import, and health check integration.

---

## Architecture Fit

This subsystem adds a **historical knowledge/archive layer** to the existing hybrid architecture:

| Layer | Current role | This module's role |
|---|---|---|
| Obsidian | Active cockpit: prompts, handoffs, decisions, projects | Archive + entity pages (read-mostly) |
| SQLite (`aios.db`) | Machine state: sessions, events, bugs | Import batch metadata + promotion status |
| `~/AIOS/` scripts | Automation: hooks, health check, review | Import pipeline, review, promote, resurface |
| Git repos | Source of truth for code | Unchanged |

Imported AI history is a **third category** — not operational state, not project notes. It must never be treated as either.

---

## Vault Placement

```
09 Archive/
  AI History/
    _Index.md                         ← coverage table + links to batch notes (manually maintained)
    _Batch-20260401104530--chatgpt.md ← batch synthesis note (one per import run)
    ChatGPT/
      2024/
        2024-03-15-context-windows-tradeoffs.md
        2024-07-22-fantasy-draft-strategy.md
      2025/
        ...
    Claude/
      2025/
        2025-01-10-soundscape-architecture.md
      2026/
        ...
    Codex/
      2026/
        2026-04-01-ai-history-import-plan--4f83c2a1.md

06 Knowledge/
  Concepts/
    context-window-management.md      ← entity page (manually created, threshold-gated)
  References/
    anthropic-model-history.md        ← entity page (tool/API/product)
```

**Rules:**
- Conversations: `09 Archive/AI History/{Source}/{YYYY}/YYYY-MM-DD-{slug}--{id8}.md`
- Entity pages: `06 Knowledge/Concepts/` (ideas, patterns) or `06 Knowledge/References/` (tools, APIs, people)
- Entity pages are never created by the pipeline. They are created manually when a concept has appeared in 3+ conversations and you have something personal to say about it.
- `_Index.md` is hand-maintained. `_Batch-{id}.md` notes are scaffolded by the pipeline and filled in by hand.
- Do not create month or week subfolders. Year is the right granularity.

---

## Ingestion Pipeline

```
~/AIOS/staging/ai-history/raw/         ← raw export files / snapshots (permanent, never deleted)
    chatgpt-export-2024-03.json
    claude-export-2026-01/conversations.json
    codex-export-2026-04/session_index.jsonl
    codex-export-2026-04/rollout-2026-04-01T16-54-50-019d4ad3-....jsonl

        │
        ▼  import-ai-history.py --source chatgpt --file raw/... [--dry-run]
        │

~/AIOS/staging/ai-history/ready/       ← transformed markdown (disposable, re-generable)
    ChatGPT/2024/
        2024-03-15-context-windows-tradeoffs.md
    Codex/2026/
        2026-04-01-ai-history-import-plan--4f83c2a1.md

        │
        ▼  review-imports.sh --batch 20260401104530--chatgpt
        │  (read-only: stats, flags, deferred list, aggregate topic candidates)
        │

        ▼  promote-imports.sh --batch 20260401104530--chatgpt [--exclude id1,id2] [--include-deferred]
        │  (copies approved notes to vault, updates SQLite, scaffolds batch synthesis note)
        │

~/Vaults/Command-Center/09 Archive/AI History/
```

**Pipeline rules:**
- Raw exports or raw local-history snapshots live permanently in `raw/`. They are the ground truth.
- `ready/` is disposable. Delete and re-run if output quality is wrong.
- Nothing enters the vault until `promote-imports.sh` is explicitly invoked.
- Review is per-batch (stats + flags), not per-note. The batch is the unit of approval.
- Aggregate topic analysis should include both `keep` and `deferred` notes so thin conversations can still reveal recurring patterns.
- The pipeline marks conversations as `deferred` (not `rejected`) automatically. Only humans set `rejected`.
- For Claude, the source of truth is the exported `conversations.json` file inside the bundle directory.
- For Codex, the source of truth is the copied JSONL rollout/session snapshot from `~/.codex`, not Chromium cache files.

---

## Note Schemas

### Conversation note

```yaml
---
type: ai-history
source: chatgpt            # chatgpt | claude | codex
model: gpt-4               # from export metadata if available
date: 2024-03-15
title: "Context Windows and Retrieval Tradeoffs"
slug: context-windows-tradeoffs
tags:
  - ai-history/chatgpt
  - topic/context-windows
  - topic/retrieval
import_batch: 20260401104530--chatgpt
quality: keep              # keep | deferred (pipeline judgment; deferred = thin individually, still useful in aggregate)
---

## Summary

2-3 sentence description of what the conversation was about.

## Why This Mattered

Why past-me was asking this. What problem it was connected to. Why future-me might care.
Leave blank at import time if not inferrable — this is the section to fill in during batch review.

## Key Exchanges

<!-- 3-5 most substantive Q&A pairs. Not a full transcript. -->

**Q:** ...

**A:** ...

## Concepts Discussed

- [[context-window-management]]

## Notes

<!-- Manual additions post-import -->
```

**Required frontmatter:** `type`, `source`, `date`, `title`, `slug`, `import_batch`  
**Optional:** `model`, `tags` beyond `ai-history/*`, `quality`  
**Must NOT appear:** `status`, `project`, `priority`, `due`, `context`, `outcome_score`, `reusable_candidate` — any field active dashboards filter on  
**Distinguishing markers:** `type: ai-history` (primary) + path under `09 Archive/AI History/` (secondary). Both must be true.

---

### Batch synthesis note (`_Batch-{id}.md`)

```yaml
---
type: archive-batch
batch_id: 20260401104530--chatgpt
source: chatgpt
date_range: "2023-01 → 2025-12"
conversation_count: 312
promoted_count: 287
deferred_count: 25
---

## What This Archive Taught Me

Freeform. Written by hand after reviewing the batch.

## Recurring Themes

- ...

## Thin Conversation Patterns

- ...

## Repeated Blind Spots

- ...

## Prompts That Kept Reappearing

- ...

## Problems Solved Multiple Times

- ...

## Concepts That Probably Deserve a Page

- [ ] context-window-management (appeared 8 times)
- [ ] rag-vs-full-context (appeared 5 times)
```

This note is scaffolded by `promote-imports.sh` (counts auto-filled from SQLite). The prose sections are filled in by hand. It should synthesize both promoted notes and any repeated thin-conversation patterns that surfaced during review. This is where historical data becomes a brain instead of a library.

---

### Entity/concept page

```yaml
---
type: concept              # concept | reference
title: "Context Window Management"
aliases: [context windows, context length]
first_seen: 2024-03-15
tags:
  - concept
  - topic/context-windows
---

## What It Is

One paragraph. Not a tutorial.

## Why It Matters to Me

Personal relevance — what decisions or work this has touched.

## Appearances in AI History

- [[2024-03-15-context-windows-tradeoffs]]
- [[2025-08-02-rag-vs-full-context]]
```

**Create only when:** concept appears in 3+ conversations AND you have something personal to say about it. Never auto-generated.

---

### Archive index (`_Index.md`)

```yaml
---
type: archive-index
updated: 2026-04-01
---

## Coverage

| Source | Date Range | Count |
|--------|------------|-------|
| Claude | 2025-02 → 2026-03 | 59 |
| Codex | 2026-02 → 2026-04 | 57 |

## Import Batches

- [[_Batch-20260402033854--claude]] — Claude export bundle (59 promoted, 86 deferred)
- [[_Batch-20260402034120--codex]] — Codex local session snapshot (57 promoted, 257 deferred)

## Notes

<!-- Themes, notable clusters, what's missing; ChatGPT real import still pending -->
```

---

## Linking and Entity Strategy

### Design invariant (not a guideline)

**Archive notes do not claim relevance to active work.** The pipeline never creates links from `09 Archive/` notes to `03 Projects/` notes. This is a hard rule.

**Active notes may selectively cite archive.** When you intentionally decide a past conversation is relevant to current work, you add a link in the project note pointing outward to the archive note. The direction is always: active → archive. Never the reverse (automatically).

### Tag vs. link decision

| Situation | Action |
|---|---|
| Topic appears in 1-2 conversations | Tag only (`topic/context-windows`) |
| Topic appears in 3+ conversations, personal relevance | Tag + create entity page manually |
| Person/tool mentioned in passing | Tag only |
| Concept you actively use across projects | Entity page in `06 Knowledge/Concepts/` |
| Active project references a past conversation | Link in project note → archive note |

### Entity creation process

The review step flags entity candidates from repeated topic tags derived from the title plus the first substantive exchange. It does not create the page. You create the page when you find it useful, not when the threshold fires.

---

## SQLite Schema Addition

```sql
CREATE TABLE ai_history_imports (
  id                TEXT PRIMARY KEY,   -- SHA256[:12] of source+source_id+date+title
  batch_id          TEXT NOT NULL,      -- e.g. "20260401104530--chatgpt"
  source            TEXT NOT NULL,      -- chatgpt | claude | codex
  source_id         TEXT,               -- source-native conversation/session id
  model             TEXT,
  conversation_date TEXT NOT NULL,
  title             TEXT NOT NULL,
  slug              TEXT NOT NULL,
  topic_tags        TEXT NOT NULL DEFAULT '[]',
  vault_path        TEXT,               -- NULL until promoted
  quality           TEXT DEFAULT 'keep',  -- keep | deferred (pipeline judgment; deferred = flagged low-value)
  status            TEXT DEFAULT 'staged',   -- staged | promoted | rejected (workflow state)
  promoted_at       TEXT,
  created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX idx_imports_batch  ON ai_history_imports(batch_id);
CREATE INDEX idx_imports_status ON ai_history_imports(status);
CREATE INDEX idx_imports_source ON ai_history_imports(source);
CREATE INDEX idx_imports_date   ON ai_history_imports(conversation_date);
```

**Status vocabulary (`status` column — workflow state):**
- `staged` — in ready/, not yet reviewed
- `promoted` — in vault
- `rejected` — human explicitly decided to discard (rare)

**Quality vocabulary (`quality` column — pipeline judgment):**
- `keep` — pipeline judged substantive; default for conversations above length/exchange threshold
- `deferred` — pipeline flagged as individually thin (short, single exchange, or low assistant word count); not promoted by default but retained in SQLite and raw export, included in pattern analysis, and promotable later

**What stays in SQLite only:** batch metadata, promotion status, date/source/title, quality flag, vault path.  
**What stays in markdown only:** conversation content, summaries, key exchanges, why it mattered.

---

## Dashboard and Search Integration

### Search

Imported notes are fully searchable in Obsidian native search. This is the primary retrieval mechanism. No special configuration needed.

### Active dashboard protection

**Required change before first import:**

`01 Dashboard/Open Actions.md` — change:
```dataview
FROM ""
WHERE type = "next-action" AND status != "done"
```
to:
```dataview
FROM "" AND -"09 Archive"
WHERE type = "next-action" AND status != "done"
```

All other active dashboards are already safe:
- `Active Projects.md` queries `FROM "03 Projects"` — scoped
- `Prompt Library.md` queries `FROM "02 AI OS/01 Prompt Library"` — scoped
- All Bases configs filter by specific `type:` values — `type: ai-history` is automatically excluded

### Health check addition

Add to `health_check.sh`:
```bash
IMPORTED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE status='promoted';")
STAGED=$(sqlite3 "$DB"   "SELECT COUNT(*) FROM ai_history_imports WHERE status='staged';")
DEFERRED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM ai_history_imports WHERE quality='deferred';")
```

Include in report table.

### Resurfacing (Phase 3)

A read-only `resurface.sh` script with three modes. Output goes to terminal or a temp note in `00 Inbox/` that is deleted after reading. Never embedded in active dashboards.

```
resurface.sh --month         # conversations from this month in prior years
resurface.sh --concepts      # most-repeated topic/* tags across last 90 days of imports
resurface.sh --project <name># conversations whose tags overlap with a project's tags
```

This script does not write to the vault. It surfaces candidates for you to decide whether they're relevant.

---

## Implementation Plan

### Phase 1 — Infrastructure (completed 2026-04-02)
1. Fix Open Actions dashboard (`FROM "" AND -"09 Archive"`) [done]
2. Create vault folder structure (`09 Archive/AI History/ChatGPT/`, `Claude/`, `Codex/`, `_Index.md`) [done]
3. Create staging directories (`~/AIOS/staging/ai-history/raw/`, `ready/`) [done]
4. Add `ai_history_imports` table to `aios.db` via migration script [done]
5. Write `import-ai-history.py` with `--dry-run` mode [done]
6. Write `review-imports.sh` — read-only batch stats from SQLite [done]
7. Write `promote-imports.sh` — vault promotion + batch synthesis note scaffold [done]

### Phase 2 — Claude + Codex format + quality (completed 2026-04-02 except real ChatGPT import)
8. Add Claude `conversations.json` export support to `import-ai-history.py` [done]
9. Add Codex local JSONL rollout/session support to `import-ai-history.py` [done]
10. Add quality scoring (flag single-exchange, <200 word conversations as `deferred`) [done]
11. Add deduplication check (source-native ID collision in SQLite before staging) [done at unit level and live for Claude; ChatGPT rerun still pending export]
12. Update `health_check.sh` with import stats block [done]
13. Add `New AI History Import` QuickAdd choice (optional — for single manual imports) [not implemented; still optional]

### Phase 3 — Resurfacing and enrichment (later)
- `resurface.sh` with `--month`, `--concepts`, `--project` modes
- Entity candidate reporting in batch metadata
- Tag clustering report across all promoted imports
- Auto-update coverage table in `_Index.md` after each promotion

---

## First 10 Concrete Steps

1. **Fix Open Actions dashboard.** Add `AND -"09 Archive"` to the `FROM` clause. One line. Do this before anything else.

2. **Create vault structure.** `mkdir -p` for `09 Archive/AI History/ChatGPT`, `Claude`, and `Codex`. Create `_Index.md` with coverage table and batch links sections, empty.

3. **Create staging directories.** `mkdir -p ~/AIOS/staging/ai-history/raw ~/AIOS/staging/ai-history/ready`.

4. **Write and run migration.** `~/AIOS/bin/migrate-add-ai-history.sh` — runs the `CREATE TABLE ai_history_imports` DDL against `aios.db`. Run once.

5. **Copy the first available raw export to staging.** Use the real export or snapshot that actually exists first. In practice, Claude and Codex were completed before ChatGPT because the ChatGPT export was not available.

6. **Write parser skeleton with `--dry-run`.** `import-ai-history.py --source chatgpt --file raw/... --dry-run` prints what it would generate (title, slug, date, quality) without writing. Validate on 10 conversations.

7. **Add markdown writer.** Extend parser to write conversation notes to `ready/{Source}/{YYYY}/`. Check frontmatter on 5 sample notes manually — especially `type: ai-history` and no forbidden fields.

8. **Write `review-imports.sh`.** Queries `ai_history_imports` for a batch. Prints: total, date range, deferred count, deferred examples, keep IDs, aggregate topic candidates across keep and deferred, and deferred-only clusters. Read-only.

9. **Write `promote-imports.sh`.** Copies approved notes from `ready/` to vault. Updates SQLite `status` to `promoted`. Scaffolds `_Batch-{id}.md` with auto-filled counts. Supports `--include-deferred` when thin conversations should be preserved in the vault as part of a broader pattern layer.

10. **Run the full pipeline on the first available source.** Run parse → stage → review → promote on the real source data you actually have. Verify: notes land in `09 Archive/AI History/`, Open Actions dashboard shows nothing from archive, Obsidian search finds the imported notes, and `aios.db` reflects promoted status.

---

## Risks and Anti-Patterns

**Do not promote without review.** Running export → vault with no staging gate means hundreds of notes land at once. You cannot easily undo that. Stage first, review batch stats, then promote.

**Do not auto-create entity pages.** Pipeline-generated entity stubs are noise. Flag candidates in batch metadata, create pages manually when genuinely useful.

**Do not link archive → active.** The pipeline never creates links from `09 Archive/` to `03 Projects/`. This is a hard constraint, not a preference. The linking asymmetry (active → archive) is intentional and must be preserved.

**Do not use active-reserved `type:` values.** `type: session`, `type: project`, `type: next-action`, `type: prompt`, `type: decision`, `type: bug` must never appear on imported notes. One mistake and the note surfaces in a dashboard it has no business in.

**Do not import raw transcripts.** Full 40-exchange transcripts have low retrieval density. The vault note is a curated extract. The raw JSON is the full record — keep it in `raw/` permanently.

**Do not use `rejected` for pipeline quality judgments.** The pipeline sets `deferred`. Only humans set `rejected`. Deferred conversations may have value later (prompt patterns, framing evolution, blind spots). Preserve optionality.

**Do not embed archive content in active dashboards.** A "Recent AI History" block on Active Projects sounds useful but creates active/archive bleed. Resurfacing belongs in `resurface.sh` — pull-based, not push-based.

**How this weakens the system if done wrong:** The hybrid architecture works because boundaries are clear. If imported history gets classified as project notes, sessions, or decisions, those boundaries collapse and dashboards become untrustworthy. The `type: ai-history` convention and the `09 Archive/` path restriction are the two enforcement points. Both must hold.
