# Phase 12: Graph-Native Memory Architecture And Cache-Aware Context Compilation — Research

**Gathered:** 2026-05-23
**Status:** Ready for planning

<source_spec>
## Source Architecture

Phase 12 is fully specified in the AIOS Graph-Native, Cache-Aware Memory Layer Audit + Implement Prompt (ingested 2026-05-23). The spec defines a four-layer memory model (raw source, normalized facts, graph relationships, model-facing briefing packets), a cache-aware context compiler, a memory packet contract, retrieval quality checks, a memory backfill plan, and a future design note on KV-cache-aware local serving.

The source prompt is the authoritative design for this phase. This research document distills the implementation-ready constraints so plans can be written without re-deriving them from the prompt.
</source_spec>

<domain>
## Phase Boundary

Phase 12 is a structural upgrade to the AIOS memory layer. It does not replace Phases 2 and 4 — it builds on top of them. Phase 2 established context packet compilation; Phase 4 established project truth and knowledge objects. Phase 12 makes those systems richer by introducing:

1. **Four-layer memory model** — raw source, normalized facts, graph relationships, and model-facing compiled briefing packets
2. **Memory Compiler** — translates retrieved raw/fact/graph memory into readable Layer D packets instead of dumping raw JSON
3. **Cache-Aware Context Compiler** — arranges prompt content so stable sections appear early (cache-friendly) and dynamic content appears late
4. **Memory Packet Contract** — a formal spec governing what every model-facing packet must contain
5. **Retrieval Quality Checks** — tests and validation scripts preventing regression to naive semantic-search-only behavior
6. **Memory Backfill Plan** — identifies existing hotspots (truth files, PRDs, agent rules, skills, prompt libraries) to be upgraded into structured facts and relationships
7. **KV-Cache Future Design Note** — documents why direct KV-cache injection is not a core dependency for API models and what would need to be true before AIOS depends on it

Phase 12 does not implement a graph database from scratch. It extends the existing SQLite operational spine with graph-edge-style relationship records. It does not remove existing memory/retrieval behavior unless replacing it with tested equivalent behavior.
</domain>

<key_questions>
## Key Questions Resolved from Design Spec

### Q1: Does Phase 12 require a graph database?
No. The spec is explicit: implement Layer C (graph relationships) using the existing database/storage layer. AIOS uses SQLite. Graph edges are represented as relationship rows (subject_id, predicate, object_id, project_scope, confidence, created_at, source_pointer) in a new `memory_relationships` table. No graph database dependency is introduced.

### Q2: What are the four memory layers?
- **Layer A (Raw Source Memory):** Original source material with provenance. Each row stores source_type, source_path, created_at, updated_at, project_id, author, confidence, original_content, and extraction_status.
- **Layer B (Normalized Fact Memory):** Durable facts extracted from raw memory. Each row stores fact_text, entity, predicate, object_value, project_scope, validity_status (active/superseded/uncertain/contradicted/archived), source_pointer, first_seen, last_confirmed, confidence, and optional expiry.
- **Layer C (Graph Relationship Memory):** Typed relationships between entities. Predicates include: caused_by, depends_on, blocks, supersedes, contradicts, supports, evidence_for, belongs_to_project, decided_in, implemented_by, requested_by_user, derived_from, related_to, has_open_question, has_constraint, has_risk, has_owner, has_status.
- **Layer D (Model-Facing Briefing Packets):** Compiled readable packets. Never raw JSON to the model. Organized into: Current Truth, Relevant Prior Decisions, Constraints, Causal/Dependency Chain, Contradictions or Stale Information, Open Questions, Sources/Provenance.

### Q3: How does the cache-aware context compiler arrange prompts?
The ContextCompiler produces content in this order:
1. Stable system/developer instructions
2. Stable AIOS operating rules
3. Stable user preferences
4. Stable project memory summary
5. Stable project truth packet
6. Dynamic task-specific retrieved memory
7. Dynamic current user request
8. Dynamic scratchpad/tool results

Stable content appears earlier so identical prefixes hit the API provider's prompt cache. Dynamic content appears later.

### Q4: Where do the deliverable docs go?
The spec names exact paths:
- `docs/audits/graph-native-memory-audit.md`
- `docs/specs/memory-packet-contract.md`
- `docs/backfills/graph-native-memory-backfill.md`
- `docs/future/kv-cache-aware-local-runner.md`

These directories may not yet exist in the AIOS repo and will need to be created.

### Q5: What new SQLite tables does Phase 12 require?
- `memory_raw_sources` — Layer A
- `memory_facts` — Layer B
- `memory_relationships` — Layer C (graph edges)
- `memory_packet_receipts` — Layer D compiled packet provenance log

### Q6: What does a good vs bad packet look like?
Good: clear natural language, source/provenance preserved, uncertainty marked, stale/superseded information marked, current truth separated from history, causal chains included when relevant, project-specific constraints included, user preference constraints included only when relevant, token-budgeted, no unrelated memories.
Bad: raw graph JSON dumped into context, no staleness markers, no provenance, conflated current truth with historical notes, missing contradictions, bloated with tangentially related memories.

### Q7: What retrieval quality checks are required?
- Retrieved context includes provenance
- Superseded memories not presented as current truth
- Contradictions surfaced when relevant
- Project-specific constraints included for project-specific tasks
- Stable memory separated from dynamic task memory
- Raw graph/JSON not dumped into prompts
- Token budgets respected
- Repeated context sections are deterministic enough for caching
- "Just in case" memory bloat avoided

### Q8: What is the KV-cache design note's position?
KV-cache-level memory is an optimization layer, not the source of truth. Direct KV-cache injection is not practical for closed API models (Anthropic, OpenAI). It may eventually be viable for local/open-source model runners (vLLM, LMCache-style serving). AIOS should remain provider-agnostic and not hard-depend on it.

### Q9: Where should the AIOS Memory Rule live?
In `config/agent-rules.md` as a permanent behavioral rule (Rule 9), alongside the existing 8 rules. The rule text is: AIOS must not treat memory as only search. Memory should preserve source, time, provenance, project scope, current validity, and relationships between ideas. Internal memory may use structured facts, graph edges, embeddings, and raw source text, but model-facing memory must be compiled into clear briefing packets that the LLM can actually reason over. For API models, AIOS should optimize for stable-prefix prompt caching. Direct KV-cache injection is allowed only as a future/local-runner optimization and must never become the source of truth.
</key_questions>

<pitfalls>
## Pitfalls

**P1: Removing existing retrieval behavior before replacement is tested.** Do not deprecate the existing semantic search or grep-based retrieval until the new layered model produces equivalent or better coverage, verified by tests.

**P2: Dumping graph JSON into prompts.** The Layer D compiler must always translate to readable markdown packets. The raw relationship rows must never appear in model context directly.

**P3: Over-engineering Layer C as a graph database.** Use SQLite rows with (subject_id, predicate, object_id) triples. A graph DB is a future option, not a requirement.

**P4: Treating the audit (Plan 01) as optional.** The audit is required before schema or compiler work begins. It identifies what currently exists, what is broken, and where memory is lost — all of which inform Plans 02–08.

**P5: Building a monolithic MemoryManager.** The spec explicitly says "prefer small, composable modules over one giant memory manager." Layer A, B, C, D should each have their own module boundary.

**P6: Making the cache-aware compiler provider-specific.** The ContextCompiler should be provider-agnostic. Stable-prefix ordering is provider-neutral. Do not add Anthropic-specific or OpenAI-specific hacks unless the architecture already cleanly supports adapters.

**P7: Skipping provenance in Layer D packets.** Every compiled packet must include a Sources/Provenance section. This is a hard requirement per the memory packet contract, not optional.
</pitfalls>
