# Knowledge And Personal Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Knowledge a durable personal/project memory substrate for humans and agents.

**Architecture:** Promote existing `knowledge_topics`, `knowledge_references`, and `knowledge_relationships` into a canonical `KnowledgeObject` contract with source provenance, backlinks, retrieval traces, freshness, and confidence. Search and grounded query must consume the same substrate.

**Tech Stack:** SQLite, Python CLI audits, Next.js knowledge pages, topic graph services, Obsidian vault ingestion.

---

## Files

- Modify: `aios-ui/server/aios/knowledge.ts`
- Modify: `aios-ui/server/aios/topic-graph.ts`
- Modify: `aios-ui/server/routers/knowledge.ts`
- Modify: `aios-ui/components/knowledge/KnowledgePageView.tsx`
- Modify: `aios-ui/app/knowledge/page.tsx`
- Modify: `aios-ui/app/knowledge/[slug]/page.tsx`
- Modify: `services/aios_cli.py`
- Modify: `tests/test_aios_cli.py`
- Add: `docs/architecture/YYYY-MM-DD-knowledge-object-contract.md`
- Modify after each code commit: `PROJECT.md`

## Knowledge Types

Support these first-class kinds:

- `project_memory`
- `decision`
- `rule`
- `hypothesis`
- `workflow`
- `agent_behavior`
- `personal_corpus`
- `external_reference`
- `concept`

### Task 1: Canonical KnowledgeObject Contract

**Files:**
- Modify: `services/aios_cli.py`
- Modify: `aios-ui/server/aios/knowledge.ts`
- Test: `tests/test_aios_cli.py`

- [ ] **Step 1: Extend audit expectations**

`aios knowledge-objects --json` must return:

```json
{
  "stable_id": "topic-...",
  "kind": "project_memory",
  "title": "...",
  "summary": "...",
  "source_refs": [],
  "backlinks": { "count": 0 },
  "freshness": "...",
  "confidence": 0.9,
  "retrieval_trace_count": 0
}
```

- [ ] **Step 2: Enforce valid kinds**

Unknown kinds must be reported as audit findings, not silently rendered as concepts.

- [ ] **Step 3: Verify**

```bash
uv run pytest tests/test_aios_cli.py::test_knowledge_objects_expose_provenance_contract -q
```

### Task 2: Knowledge Search

**Files:**
- Modify: `aios-ui/server/routers/knowledge.ts`
- Modify: `aios-ui/app/knowledge/page.tsx`

- [ ] **Step 1: Add search query**

Search should cover:

- title
- summary
- reference label
- reference excerpt
- tags

Return matched object id, title, kind, summary, confidence, and top matching references.

- [ ] **Step 2: Add UI search box**

The Knowledge page should be search-first, while still allowing browsing by kind.

- [ ] **Step 3: Verify manually**

Run local UI and search a known topic title from `knowledge_topics`.

### Task 3: Personal Corpus Integration

**Files:**
- Modify: `aios-ui/server/aios/topic-graph.ts`
- Modify: relevant importers under `bin/`
- Modify: `services/aios_cli.py`

- [ ] **Step 1: Define source kinds**

Use these source kinds consistently:

- `project_memory`
- `run`
- `prompt`
- `artifact`
- `personal_corpus`
- `external_reference`
- `decision`
- `rule`

- [ ] **Step 2: Add audit coverage**

`knowledge-objects` should report counts by source kind and identify objects with no personal corpus path when expected.

- [ ] **Step 3: Connect importers**

Importers for AI history, docs, PDFs, Apple Notes, iMessage, and Takeout should create or update `knowledge_references` where appropriate.

### Task 4: Retrieval Trace

**Files:**
- Modify: `aios-ui/server/aios/packet-assembly.ts`
- Modify: `aios-ui/server/aios/query.ts`
- Modify: `services/aios_cli.py`

- [ ] **Step 1: Define RetrievalTrace**

Trace fields:

- query
- matched objects
- omitted context
- expansion path
- citations
- token budget
- ranking reason

- [ ] **Step 2: Store trace consistently**

Use `briefing_packets.selection_trace_json` and `packet_expansions.trace_json` until a dedicated retrieval trace table is justified.

- [ ] **Step 3: Expose trace in Grounded Query**

Grounded answers should include cited source records and omitted context counts.

### Tier-One Knowledge Acceptance

- [ ] Knowledge page has search
- [ ] every object has stable identity
- [ ] priority objects have source refs
- [ ] backlinks are real relationship data, not visual decoration
- [ ] Grounded Query can answer project/workflow questions with citations
- [ ] agents can request compact ranked packets and expansion traces from the same substrate
