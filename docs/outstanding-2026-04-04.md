---
type: task-list
title: Outstanding Tasks — Second Brain + Knowledge Layer
created: 2026-04-04
sources:
  - Vaults/Command-Center/02 AI OS/second-brain-implementation-plan-2026-04-03.md
  - AIOS/docs/specs/2026-04-03-knowledge-layer-design.md
---

# Outstanding Tasks — Second Brain + Knowledge Layer

## Phase 0 — Project Consolidation (Cleanup Residuals)

- [x] **0.7** Update CLAUDE.md registry entries with `~/Projects/` canonical paths
- [x] **0.8** Update `~/AIOS/bin/sync-claude-md.sh` path references
- [x] **0.9** Remove `~/projects/` (lowercase) — content is identical to `~/Projects/`

## Phase 1 — Vault Boundary Hardening

- [x] **1.5** Audit `~/ai-os/` vs `~/AIOS/` — `ai-os/` has `config/`, `db/`, `scripts/`; confirm superseded, move to `~/AIOS/archive/legacy-ai-os/`, document the decision in the vault

## Knowledge Layer Phase 2 — Activation

> Prerequisites must complete before enabling rules injection (steps marked †).

- [~] Run `review-observations.py` first pass on 35 existing patterns †
- [~] Use `approve-pattern.py` to manually approve 3–5 high-signal patterns to `rule` state †
- [x] Enable `rules_retrieval` in `~/AIOS/config/retrieval-policy.json` (currently `false`) — after above
- [x] Modify `hook-session-start.py` — add `get_active_rules()` and rules injection block
- [x] Modify `hook-prompt-submit.py` — add `rules_retrieval` retrieval step

## Phase 2 — AI Conversation Corpus Ingestion

- [x] **2.1** Inspect `conversations.json` structure, document schema
- [x] **2.2** Write/adapt import script for `conversations.json` → `ai_history_imports` table
- [x] **2.3** Run import, run promote pass, review deferred list before discarding
- [x] **2.4** Inspect one Codex JSONL file, document event schema, build/fix Codex importer
- [x] **2.5** Cross-reference AI history by project; document findings in `09 Archive/AI History/_Index.md`

## Phase 3 — High-Value Documents

- [x] **3.1** Ingest 5 product docs from `~/Downloads/` → `03 Projects/Soundscape/Product/`
- [x] **3.2** Create `06 Knowledge/Research/Dsci-Capstone-2026.md`
- [x] **3.3** Move 4 Computer Network Notes → `05 Areas/Learning/Computer-Networks-UC3M-2025/` with provenance frontmatter
- [x] **3.4** Create `06 Knowledge/Wiki/Dynasty-Trade-Framework.md`
- [x] **3.5** Create `06 Knowledge/Research/R-Statistics-Methods.md`

## Phase 4 — Personal Corpus

- [x] **4.2** Create `Personal-Corpus/Creative/Music/music-catalog.md` — full demo tracklist, beats inventory, recording sessions, Book songs
- [x] **4.3** Add date-context note on Dec 2025 recording sessions (148 files, shoe1 project)
- [x] **4.4** Create `Personal-Corpus/Creative/interactive-book.md`
- [x] **4.5** Create `Personal-Corpus/Writing/` folder structure
- [x] **4.6** Move `A cold sweat clings, a tribute to restless dreams.docx` → `Personal-Corpus/Writing/`
- [x] **4.7** Create `Personal-Corpus/Admin/documents-index.md` — medical, financial, career, academic
- [x] **4.8** Audit `~/iCloud Drive (Archive)/Documents/` for unique content
- [x] **4.9** Create `Personal-Corpus/Archive/icloud-legacy.md` based on audit findings
- [x] **4.10** Create `Personal-Corpus/Life/Study-Abroad-Madrid-2025.md` — courses, timeline, cross-reference AI chat history Sep–Dec 2025

## Phase 5 — Downloads Corpus Management

- [x] **5.1** Create `09 Archive/Downloads-Map-2026-04.md`
- [x] **5.2** Delete duplicate installers to recover ~12GB (keep FL Studio 25.2.3, delete 5 older; delete all Anaconda; keep RStudio 2025.09)

## Phase 6 — PDF and Document Index Pipeline

- [x] **6.1** Write `~/AIOS/bin/index-pdfs.py` — walk `~/Downloads/`, extract metadata, write to `pdf_index` table in `aios.db`
- [x] **6.2** Run indexer, review output for high-value candidates not yet in vault
- [x] **6.3** Write DOCX indexer using `python-docx` → `docx_index` table in `aios.db`

## Phase 7 — Pattern Pipeline Expansion

- [x] **7.1** Create `06 Knowledge/Wiki/Project-Restart-Pattern.md` — synthesize from 30 session handoffs
- [x] **7.2** Create `06 Knowledge/Wiki/GSD-Execution-Breakdown-Patterns.md`
- [x] **7.3** Add bug motif extraction pass to pattern pipeline; seed with 3 known motifs (Prisma Decimal, TS null propagation, monorepo build order)

## Knowledge Layer Phase 3 — Corpus Integration (Deferred)

> Defer until Phase 2 corpus ingestion is complete.

- [x] Write `agent-synthesis.py` and `import-pattern-candidates.py`
- [x] Add agent synthesis to `weekly-maintenance.sh`
- [x] Modify `hook-stop.py` — add insight flagging
- [x] Add health checks to `vault-lint.py`
- [x] Add project-specific domains when any project hits 10+ project-specific patterns

---

## Suggested Execution Order

1. **Phase 0 cleanup** (0.7 → 0.8 → 0.9) — 30 min
2. **Phase 1.5** `ai-os/` audit — 15 min
3. **Knowledge Layer Phase 2** review pass + approve patterns → enable rules injection — unblocks hook injection
4. **Phase 2** AI corpus ingestion — largest effort, unblocks Phase 7
5. **Phase 3 + 4** in parallel — document and personal corpus work
6. **Phase 5** Downloads map + installer cleanup — quick wins
7. **Phase 6** PDF/DOCX indexer — infrastructure
8. **Phase 7 + Knowledge Layer Phase 3** — pattern expansion, deferred until corpus exists
