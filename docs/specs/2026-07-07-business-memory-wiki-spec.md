---
type: spec
title: Business Memory Wiki — Integrated Build Spec
date: 2026-07-07
status: approved-for-implementation
author: jakyeamos
extends:
  - docs/STORES.md
  - docs/specs/2026-04-03-knowledge-layer-design.md
  - Vaults/Command-Center/02 AI OS/kb-architecture-audit-2026-04-05.md
---

# Business Memory Wiki — Integrated Build Spec

## Purpose

Build a **local-first, agent-managed business memory system** inside the existing AIOS +
Command-Center stack. Raw business data (Gmail, Discord, X, manual notes) flows in on a
schedule; deterministic code handles ingest, dedupe, indexing, and file management; LLM calls
handle judgment-heavy synthesis only. Durable output is **Obsidian markdown** with provenance,
optimized for course planning, cohort feedback analysis, launch retros, and business-context Q&A.

This is **not** a generic chatbot over files. It is a compounding wiki with immutable raw
sources, staged compilation, and vault promotion gates.

## Non-Goals

- Do not create a separate repo or second wiki root.
- Do not bypass vault `trust` / `sensitivity` / promotion workflow.
- Do not require hosted vector DB or embeddings in v1.
- Do not auto-promote LLM output to `trust: trusted`.
- Do not scrape Gmail/Discord/X or violate platform ToS.
- Do not merge business student data into default coding-agent retrieval without sensitivity checks.

## Design Principles (merged)

| From external prompt | From current AIOS/vault stack | Integrated rule |
|---|---|---|
| Immutable raw JSON | Staging + SQLite authority | Raw JSON in staging; metadata in SQLite |
| Agent-maintained wiki | Staging gate + human promotion | Compile → staging → review → vault |
| `[src:...]` citations | `source`, `evidence`, `source_ids` | One citation ID scheme across all layers |
| FTS5 search | Tiered retrieval policy | FTS with trust/sensitivity filters |
| Course/business ontology | Engineering wiki (`06 Knowledge/Wiki/`) | Separate `06 Knowledge/Business/` tree |
| `AGENTS.md` workflows | Agent Context packs | `Context for Business Memory.md` + scoped ops doc |
| Scheduled sync daemon | `weekly-maintenance.sh` | New `business-ingest` cron, separate from patterns |

---

## Architecture

```
External sources                AIOS (machine)                    Vault (human-readable)
─────────────────              ──────────────                    ──────────────────────
Gmail ─────┐
Discord ───┼──► staging/raw-sources/  ──► memory_raw_sources ──► staging/business-wiki-candidates/
X ─────────┤         (immutable)              (+ FTS index)              │
Manual ────┘                                    │                        ▼
                                                │              06 Knowledge/Business/  (promoted)
                                                └──► knowledge_topics / knowledge_references
                                                     knowledge_markers (contradictions)
```

### Layer map (aligned with kb-architecture audit)

| Layer | Path | Writer | Reader |
|---|---|---|---|
| 0 — Ops state | `~/AIOS/data/aios.db` | hooks, ingest scripts | `aios-query`, compiler, FTS |
| 1 — Raw staging | `~/AIOS/staging/raw-sources/` | connectors | compiler, human audit |
| 2 — Wiki candidates | `~/AIOS/staging/business-wiki-candidates/` | compiler (LLM optional) | human review, lint |
| 3 — Business wiki | `06 Knowledge/Business/` | human promotion only | FTS, agents (scoped) |
| 3 — Engineering wiki | `06 Knowledge/Wiki/` | human (existing) | default coding retrieval |
| 4 — Archive | `Personal-Corpus/`, `09 Archive/` | ingest after review | opt-in search |

**Authority:** See `docs/STORES.md`. Extend that document when this module ships.

---

## Directory Layout

### AIOS (new / extended)

```
~/AIOS/
  bin/
    business-ingest.py          # CLI: sync, status (wraps connectors)
    business-compile.py         # CLI: compile staged raw → wiki candidates
    business-query.py           # CLI: FTS + optional LLM answer
    business-lint.py            # CLI: business-specific lint (or extend vault-lint.py)
  services/
    business/
      connectors/
        base.py
        manual.py
        gmail.py                # OAuth-ready; disabled without creds
        discord.py
        x_twitter.py
      ingest/
        normalize.py
        dedupe.py
        scheduler.py
        pipeline.py
      wiki/
        compiler.py
        templates.py
        linker.py
        citations.py
      llm/
        client.py
        prompts.py
      search/
        fts.py                  # FTS5 over sources + vault business pages
        retrieve.py             # tiered retrieval
      privacy/
        redact.py
  config/
    business-sources.yaml
    business-taxonomy.yaml
  staging/
    raw-sources/
      manual/inbox/             # drop zone — works without API keys
      gmail/YYYY/MM/DD/
      discord/YYYY/MM/DD/
      x/YYYY/MM/DD/
    business-wiki-candidates/
      summaries/
      concepts/
      entities/
      courses/
      questions/
      decisions/
      contradictions/
  tests/
    business/
      test_dedupe.py
      test_citations.py
      test_frontmatter.py
      test_fts.py
      test_manual_connector.py
```

### Vault (new)

```
06 Knowledge/
  Business/
    _INDEX.md                   # auto-maintained table of business pages
    log.md                      # append-only compile/ingest timeline
    AGENTS.md                   # scoped ops manual for business wiki agents
    summaries/
    concepts/
    entities/
    courses/
    students/
    launches/
    questions/
    decisions/
    contradictions/
  Agent Context/
    Context for Business Memory.md   # retrieval entry point for agents
07 Templates/
  Business Summary.md
  Business Concept.md
  Business Course.md
  Business Question.md
  Business Decision.md
  Business Contradiction.md
config/                           # vault-local pointers (optional)
  business-memory.yaml            # links to AIOS config paths
```

Engineering wiki stays at `06 Knowledge/Wiki/`. Never mix business student PII pages into
engineering retrieval defaults.

---

## Data Model

### Extend `memory_raw_sources` (do not create parallel `sources` table)

Add columns via migration if missing:

| Column | Type | Notes |
|---|---|---|
| `external_id` | TEXT | Provider message/post ID |
| `author_name` | TEXT | |
| `author_handle` | TEXT | email or @handle |
| `occurred_at` | TEXT ISO | source timestamp |
| `channel_or_thread` | TEXT | |
| `subject_or_title` | TEXT | |
| `body_text` | TEXT | normalized plain text |
| `url` | TEXT | |
| `attachments_json` | TEXT | metadata only |
| `tags_json` | TEXT | |
| `content_hash` | TEXT UNIQUE | dedupe key |
| `privacy_level` | TEXT | `public` \| `internal` \| `private` \| `sensitive` |
| `raw_path` | TEXT | path to immutable JSON file |
| `normalized_json_path` | TEXT | optional duplicate for audit |
| `ingest_run_id` | TEXT | FK to ingest_runs |
| `compiled_at` | TEXT | null until wiki compile processes it |

`source_type` values: `manual` | `gmail` | `discord` | `x` | `apple_notes` (future).

Immutable raw file shape (JSON, one record per file or JSONL batch):

```json
{
  "source_id": "src_manual_2026_07_07_a1b2c3",
  "source_type": "manual",
  "external_id": null,
  "author_name": "Student A",
  "author_handle": null,
  "timestamp": "2026-07-05T14:22:00Z",
  "fetched_at": "2026-07-07T12:00:00Z",
  "channel_or_thread": "cohort-3-discord",
  "subject_or_title": "autocompact confusion",
  "body_text": "...",
  "url": null,
  "attachments": [],
  "tags": ["student-feedback", "autocompact"],
  "hash": "sha256:...",
  "privacy_level": "internal"
}
```

**Rule:** Never mutate files under `staging/raw-sources/` after write. Updates create a new
versioned record with a new `source_id` and `content_hash`.

### New table: `business_ingest_runs`

```sql
CREATE TABLE business_ingest_runs (
  id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,  -- running | success | partial | failed | skipped
  records_fetched INTEGER DEFAULT 0,
  records_new INTEGER DEFAULT 0,
  records_duplicate INTEGER DEFAULT 0,
  error_summary TEXT,
  config_snapshot_json TEXT
);
```

### New table: `business_compile_runs`

```sql
CREATE TABLE business_compile_runs (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  since_cursor TEXT,
  sources_processed INTEGER DEFAULT 0,
  pages_created INTEGER DEFAULT 0,
  pages_updated INTEGER DEFAULT 0,
  llm_enabled INTEGER DEFAULT 0,
  lint_findings INTEGER DEFAULT 0,
  status TEXT NOT NULL
);
```

### Reuse existing graph tables

| Business concept | SQLite table | Vault surface |
|---|---|---|
| Concept / entity / course | `knowledge_topics` (`kind` = concept \| entity \| course \| launch) | `06 Knowledge/Business/{concepts,entities,courses}/` |
| Evidence link | `knowledge_references` (`source_kind` = business_raw) | inline `[src:...]` + frontmatter `source_ids` |
| Contradiction | `knowledge_markers` (`marker_kind` = contradiction) | `06 Knowledge/Business/contradictions/` |
| Lint finding | new `business_lint_findings` or extend vault-lint JSON | `06 Knowledge/Business/lint-report.md` |

### FTS5 (new)

```sql
CREATE VIRTUAL TABLE business_sources_fts USING fts5(
  source_id UNINDEXED,
  body_text,
  subject_or_title,
  author_name,
  channel_or_thread,
  tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE business_wiki_fts USING fts5(
  vault_path UNINDEXED,
  title,
  body,
  tags,
  tokenize='porter unicode61'
);
```

Indexer runs after ingest and after vault promotion.

---

## Citation Standard

**Format:** `[src:{source_type}_{YYYY}_{MM}_{DD}_{short_hash}]`

Example: `[src:manual_2026_07_05_a1b2c3]`

**Required on every synthesized claim** in business wiki bodies and LLM query answers.

**Frontmatter** (all business pages):

```yaml
---
type: business-summary | business-concept | business-course | business-question | business-decision | business-contradiction | business-entity
status: draft | current | stale | superseded
quality: agent-generated | agent-reviewed | human-curated
trust: working | trusted
sensitivity: safe | internal | private | sensitive
retrieval: default | scoped | opt-in | blocked
area: business
project:
created: 2026-07-07
updated: 2026-07-07
last_reviewed:
source: business-compiler
source_type: generated
source_ids:
  - src_manual_2026_07_05_a1b2c3
evidence:
  - "06 Knowledge/Business/summaries/autocompact-thread-2026-07-05.md"
confidence: 0.0-1.0
source_count: 3
tags: []
related: []
review-status: pending | reviewed | canonical
---
```

Pages with student PII default to `sensitivity: private` and `retrieval: scoped`.

---

## Connectors

Common interface:

```python
class Connector:
    name: str

    def is_configured(self) -> bool: ...

    def sync(self, since: datetime | None) -> list[SourceRecord]: ...
```

### Manual (Phase 1 — must work day one)

- Watches `~/AIOS/staging/raw-sources/manual/inbox/`
- Accepts `.md`, `.txt`, `.json`
- No API credentials required
- Ship demo files simulating Discord feedback, Gmail student question, X learning-interest post, launch feedback

### Gmail (Phase 6 — skeleton first)

- OAuth-ready; skip cleanly if `GMAIL_*` creds absent
- Configurable queries in `business-sources.yaml`
- Exclude spam/trash by default
- Preserve thread_id, message_id

### Discord (Phase 6)

- Bot token or exported data adapter
- Incremental fetch by channel/guild
- Rate-limit aware; skip if unconfigured

### X/Twitter (Phase 6)

- Official API only
- Modes: own_posts, mentions, bookmarks (as plan permits)
- Clear `not_configured` status — no scraping

---

## Compiler Behavior

`business-compile.py --since last-run | beginning | ISO8601`

1. Select uncompiled rows from `memory_raw_sources` (by `compiled_at IS NULL`).
2. Group into threads/conversations where possible (thread_id, channel, subject).
3. **Deterministic pre-pass:** dedupe, tag, privacy classification, taxonomy keyword match.
4. **LLM pass (optional):** if `OPENAI_API_KEY` set and `--llm` flag (or config default):
   - `summarize_source(record)`
   - `extract_entities_and_concepts(record)`
   - `propose_wiki_updates(summary, existing_pages)`
   If no key: write candidate pages with placeholders + `quality: agent-generated`, `llm_status: skipped`.
5. Write candidate markdown to `staging/business-wiki-candidates/` with atomic writes.
6. Upsert `knowledge_topics` / `knowledge_references` for graph layer.
7. Append entry to `06 Knowledge/Business/log.md` (via staging copy first).
8. Regenerate `06 Knowledge/Business/_INDEX.md` in staging; promote index with pages.
9. Run business lint pass.
10. Set `compiled_at` on processed sources.

**Anti-overwrite rules:**

- Load existing promoted page before update.
- Add `## New evidence (YYYY-MM-DD)` sections; do not delete prior claims.
- Mark stale claims; do not erase.
- Uncertain claims → `confidence` < 0.6 and/or contradiction candidate.

---

## CLI Commands

```bash
# Setup
python -m services.business.cli init          # create dirs, migrate schema, seed FTS

# Ingest
python -m services.business.cli sync --source manual
python -m services.business.cli sync --source gmail|discord|x
python -m services.business.cli sync --all

# Compile
python -m services.business.cli compile --since last-run [--llm]

# Query
python -m services.business.cli query "What are students excited to learn right now?" [--llm] [--save-question]

# Maintenance
python -m services.business.cli lint
python -m services.business.cli status
python -m services.business.cli daemon --interval-hours 3   # sync → compile → lint → log
```

Wrap in `~/AIOS/bin/` shell entrypoints for consistency with existing scripts.

---

## Search and Query

### Retrieval tiers (extends Vault Retrieval Policy)

| Tier | Scope | When |
|---|---|---|
| 1 | Agent Context pack + Business `_INDEX.md` summary | Always for business tasks |
| 2 | `business_wiki_fts` over `trust in (working, trusted)` + sensitivity filter | Question/query |
| 3 | `business_sources_fts` over raw sources | Citation verification, deep dive |
| 4 | Personal-Corpus / Archive | Explicit opt-in only |

### `business-query.py` workflow

1. Read `06 Knowledge/Business/_INDEX.md` (or staging index if no promoted pages).
2. FTS search wiki then sources.
3. Load top wiki pages; pull raw JSON only when citations need verification.
4. If `--llm`: synthesize answer with `[src:...]` citations.
5. If `--save-question` and high value: write candidate to `staging/.../questions/`.

Replace `vault-search.py` caps for business mode: ranked FTS, max 10 results, 800-char excerpts.

---

## Linter

Extend `vault-lint.py` or add `business-lint.py`. Checks:

**Critical**
- Broken `[[wikilinks]]` in Business tree
- Missing required frontmatter on business pages
- Synthesized claims without `[src:...]` near evidence sections
- `source_ids` in frontmatter not found in SQLite
- Raw sources with `compiled_at IS NULL` older than 7 days
- Open contradiction pages (`review-status: pending`) older than 30 days
- Duplicate concept slugs

**Warning**
- Orphan business pages (no backlinks from `_INDEX.md` or related pages)
- Stale pages (`last_reviewed` > 90 days)
- Index entries pointing to missing files
- Pages missing from index

**Output**
- stdout summary
- `~/AIOS/logs/business-lint-latest.json`
- `staging/business-wiki-candidates/lint-report.md` (never write directly to vault)

---

## Agent Operating Manual

Create two surfaces (do not duplicate global `~/AGENTS.md`):

### `06 Knowledge/Business/AGENTS.md`

Scoped rules:

- This is compounding business memory, not a transient RAG cache.
- Read `_INDEX.md` first.
- Raw sources are immutable — never edit `staging/raw-sources/`.
- Write candidates to staging only; never set `trust: trusted` without review.
- Preserve `[src:...]` citations on every factual claim.
- Prefer updating existing concept/course pages over creating duplicates.
- Append to `log.md` after ingest/compile/promotion.
- Do not delete pages; mark `status: superseded` and explain in log.
- Do not invent facts; mark uncertainty explicitly.
- Do not load `sensitivity: private|sensitive` into context unless user opts in.

Workflows (ingest, answer question, course planning) — copy from external prompt verbatim but
replace paths with this spec's paths and insert promotion gate before vault writes.

### `06 Knowledge/Agent Context/Context for Business Memory.md`

Retrieval entry point listing:

- Load first: Business `_INDEX.md`, taxonomy, active course pages
- Policies: Vault Retrieval Policy, Vault Promotion Workflow
- Commands: `business-query.py`, `business-lint.py`, `aios-query.py --status`

---

## Privacy and Security

- Secrets in `~/AIOS/.env` only; ship `~/AIOS/.env.example`
- `.gitignore`: `.env`, OAuth tokens, raw private data (configurable)
- `PRIVACY.md` in `~/AIOS/docs/` describing data flow and LLM opt-in
- `redact.py` helper for emails, phones, tokens in logs and optional LLM payloads
- **Default:** do not send raw source text to LLM unless `compile --llm` or `query --llm`
- Config flag `commit_raw: false` / `commit_wiki: false` for git safety

---

## Configuration

### `~/AIOS/config/business-sources.yaml`

```yaml
manual:
  enabled: true
  inbox_path: staging/raw-sources/manual/inbox

gmail:
  enabled: false
  queries:
    - "label:students newer_than:30d"
  exclude:
    - in:trash
    - in:spam

discord:
  enabled: false
  guild_ids: []
  channel_ids: []

x:
  enabled: false
  modes: [own_posts, mentions, bookmarks]
```

### `~/AIOS/config/business-taxonomy.yaml`

```yaml
business_concepts:
  - student pain point
  - course section
  - objection
  - excitement signal
  - testimonial
  - feature request
  - bug/confusion
  - launch feedback
  - pricing concern
  - content gap

course_analysis_fields:
  - missing talking points
  - repeated questions
  - misunderstood concepts
  - requested examples
  - exercises students want
  - objections
  - positive reactions
```

---

## Promotion Workflow (required)

Business wiki candidates follow the same trust ladder as `Vault Promotion Workflow.md`:

```
raw → candidate (staging) → working (promoted, agent-reviewed) → trusted (human-reviewed)
```

**Promotion checklist** before `trust: trusted`:

- [ ] `source_ids` validate in SQLite
- [ ] `sensitivity` assigned correctly
- [ ] No unresolved critical lint findings
- [ ] `last_reviewed` set
- [ ] `related` links to real pages
- [ ] Student PII redacted or scoped

Use `07 Templates/Promotion Review.md` for non-trivial promotions.

---

## Demo Data

Ship under `~/AIOS/tests/business/fixtures/demo-sources/` (not real PII):

1. Manual note — Discord-style student feedback on "autocompact"
2. Manual note — Gmail-style question about a course section
3. Manual note — X-style post on what people want to learn
4. Manual note — launch feedback snippet

Demo command:

```bash
cp -r ~/AIOS/tests/business/fixtures/demo-sources/* \
  ~/AIOS/staging/raw-sources/manual/inbox/
python ~/AIOS/bin/business-ingest.py sync --source manual
python ~/AIOS/bin/business-compile.py --since beginning --llm  # optional
```

---

## Implementation Phases

### Phase 0 — Prereqs (from kb-architecture audit; blocking)

1. Disable bigram pattern extraction in `weekly-maintenance.sh` if still enabled.
2. Purge or discard noise patterns (`personal`, `observation` classes).
3. Confirm `staging/business-wiki-candidates/` and `staging/raw-sources/` exist.
4. Update `docs/STORES.md` with new staging paths.

### Phase 1 — Scaffold + manual ingest (MVP core)

- Schema migration for `memory_raw_sources` extensions + ingest/compile run tables + FTS
- `manual` connector + normalize + dedupe
- `business-ingest.py` init/sync/status
- Tests: dedupe, path generation, hash, manual connector

### Phase 2 — Compiler + templates (no LLM)

- Jinja2/markdown templates for summary, concept, course pages
- Deterministic compile: metadata + taxonomy tags + candidate files
- `_INDEX.md` and `log.md` generation in staging
- Demo data end-to-end

### Phase 3 — LLM layer

- OpenAI-compatible client (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`)
- Prompts: summarize, extract, propose updates
- `--llm` flag with graceful skip
- Tests: mock LLM client

### Phase 4 — Search + query

- FTS indexer
- `business-query.py` with tiered retrieval
- `--save-question` for durable question pages
- Course-planning query template (missing talking points, objections, excitement signals)

### Phase 5 — Lint + scheduler + docs

- Business lint checks
- `daemon --interval-hours 3`
- `PRIVACY.md`, README section in `~/AIOS/README.md`
- Vault templates + `Context for Business Memory.md` + `Business/AGENTS.md`

### Phase 6 — External connector skeletons

- Gmail, Discord, X adapters with `is_configured()` + clean skip
- OAuth/token docs in README; no full integration required for MVP done

---

## Acceptance Criteria

MVP is complete when:

```bash
cd ~/AIOS
cp .env.example .env          # OPENAI_API_KEY optional
python ~/AIOS/bin/business-ingest.py init
cp -r tests/business/fixtures/demo-sources/* staging/raw-sources/manual/inbox/
python ~/AIOS/bin/business-ingest.py sync --source manual
python ~/AIOS/bin/business-compile.py --since beginning
python ~/AIOS/bin/business-query.py "What do students think about autocompact?"
python ~/AIOS/bin/business-lint.py
pytest tests/business/
```

**Must produce:**

- [ ] Immutable raw JSON under `staging/raw-sources/manual/`
- [ ] SQLite rows in `memory_raw_sources` with `content_hash`
- [ ] Candidate pages in `staging/business-wiki-candidates/` (summary + concept + course if demo mentions course)
- [ ] `[src:...]` citations in candidate bodies
- [ ] FTS indexes populated
- [ ] Query output cites source IDs and candidate wiki paths
- [ ] Lint reports zero critical issues on demo data
- [ ] Tests pass

**Human step (not automated):** promote at least one concept page to
`06 Knowledge/Business/` with `trust: working` and verify vault lint + retrieval policy.

---

## What to Reuse vs Build

| Reuse as-is | Extend | Build new |
|---|---|---|
| `memory_raw_sources`, `knowledge_topics`, `knowledge_references`, `knowledge_markers` | `memory_raw_sources` columns, FTS tables | Connectors, compiler, business CLI |
| `vault-lint.py`, `aios-query.py`, `aios_paths.py` | Add business scope flags | `business-ingest.py`, `business-compile.py`, `business-query.py` |
| Vault Promotion Workflow, Retrieval Policy | Business sensitivity defaults | `06 Knowledge/Business/` tree |
| `weekly-maintenance.sh` | Optional hook to call business daemon | `business-sources.yaml`, taxonomy |
| Engineering `06 Knowledge/Wiki/` | — | Do not merge trees |

---

## Known Limitations (v1)

- No embeddings; FTS only (interface stub ok for future)
- Gmail/Discord/X likely stubbed at MVP ship
- No automatic promotion to vault — human or scripted review required
- No real-time sync; polling every N hours
- Contradiction detection is LLM-assisted + lint-flagged, not fully automatic resolution

---

## Recommended First Codex Task

> **Phase 1 only:** Schema migration + manual connector + `business-ingest.py init/sync/status` +
> demo fixtures + tests. No LLM, no external APIs. Verify immutable raw JSON and SQLite dedupe.

After Phase 1 passes acceptance subset, proceed to Phase 2 compiler without LLM.

---

## Document Maintenance

When implementation lands:

1. Update `~/AIOS/docs/STORES.md` staging table.
2. Add row to `06 Knowledge/Business/log.md` with spec adoption date.
3. Link this spec from `00 Maps/Knowledge.md` and `00 Maps/AIOS.md`.
