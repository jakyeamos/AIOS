# Integrations Corpus And Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect personal corpus, code truth, and project records into one retrieval substrate usable by humans and agents.

**Architecture:** Importers should land source records with provenance. CTS should provide code-grounded retrieval. Grounded Query and packet assembly should consume both through explicit retrieval traces.

**Tech Stack:** Python importers, SQLite, CTS modules, Obsidian vault paths, Next.js query/knowledge pages.

---

## Files

- Modify: `bin/import-ai-history.py`
- Modify: `bin/index-docx.py`
- Modify: `bin/index-pdfs.py`
- Modify: `bin/ingest-apple-notes.py`
- Modify: `bin/ingest-imessage.py`
- Modify: `bin/takeout-process.py`
- Modify: `services/cts/search.py`
- Modify: `services/cts/indexer.py`
- Modify: `aios-ui/server/aios/query.ts`
- Modify: `aios-ui/server/aios/packet-assembly.ts`
- Add or modify tests for each importer touched
- Modify after each code commit: `PROJECT.md`

### Task 1: Corpus Source Registry

**Files:**
- Add: `config/corpus-sources.json`
- Modify: importers under `bin/`

- [ ] **Step 1: Define source registry**

Each source:

- key
- kind
- local path
- privacy level
- ingestion command
- output table
- vault target
- last successful ingest

- [ ] **Step 2: Add CLI audit**

Add `aios corpus-audit --json` with source availability, freshness, rows indexed, and missing reasons.

### Task 2: Importer Provenance

**Files:**
- Modify: each importer that writes durable records

- [ ] **Step 1: Add provenance fields**

Importer records should include:

- source key
- source native id
- source path
- imported at
- content hash
- title
- timestamp
- privacy level

- [ ] **Step 2: Emit knowledge references**

Where an imported item is useful for retrieval, create or update `knowledge_references`.

### Task 3: CTS Retrieval Integration

**Files:**
- Modify: `services/cts/search.py`
- Modify: `aios-ui/server/aios/cts.ts`
- Modify: `aios-ui/server/aios/query.ts`

- [ ] **Step 1: Define CTS result contract**

Fields:

- repo id
- file path
- symbol
- snippet
- confidence
- backend
- freshness

- [ ] **Step 2: Add Grounded Query CTS citations**

When code truth is used, answers must cite file path and backend.

### Task 4: Packet Assembly Retrieval Trace

**Files:**
- Modify: `aios-ui/server/aios/packet-assembly.ts`

- [ ] **Step 1: Include corpus and CTS evidence**

Briefing packets should show:

- top knowledge objects
- project memory
- relevant code truth
- omitted context
- expansion handles

- [ ] **Step 2: Keep packet compact**

Respect token budget and log omitted context rather than overloading the agent.

### Tier-One Retrieval Acceptance

- [ ] corpus sources are auditable
- [ ] importers produce provenance
- [ ] knowledge references include personal corpus where relevant
- [ ] CTS results can be cited by Grounded Query
- [ ] packet assembly records retrieval trace and omitted context
