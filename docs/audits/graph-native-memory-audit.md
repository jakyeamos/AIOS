# Graph-Native Memory Architecture Audit

Phase 12 Plan 12-01 audit of the current AIOS memory, retrieval, context-packing, and agent-briefing architecture.

## Current Architecture Summary

### Raw Memory Storage

- `schema.sql` is the primary operational memory contract. It stores projects, sessions, prompt submissions, tool events, artifacts, bugs, orchestration runs, briefing packets, memory updates, knowledge topics, relationships, references, writebacks, learning events, eval records, and second-brain retrieval metrics.
- `sessions`, `tool_events`, `prompts_used`, `artifacts`, `bug_log`, and `ai_history_imports` in `schema.sql` hold raw session, prompt, artifact, bug, and imported transcript metadata.
- `orchestration_runs`, `orchestration_invocations`, `orchestration_run_events`, `workflow_execution_reports`, `tmcp_traversal_receipts`, `briefing_packets`, `packet_expansions`, and `memory_updates` in `schema.sql` hold governed workflow state, packet state, traversal receipts, expansions, and closeout memory.
- `knowledge_topics`, `knowledge_relationships`, `knowledge_references`, `knowledge_markers`, and `knowledge_graph_state` in `schema.sql` define an implemented topic/reference graph for the UI-side knowledge system.
- `services/cts/registry.py` stores CTS graph databases separately under `~/AIOS/data/cts/<repo-hash>/graph.db`, using the root `projects` table as the repo registry.
- `services/cts/migrations.py` defines CTS `repos`, `nodes`, `edges`, and `nodes_fts` tables for code topology storage.
- `bin/ingest-apple-notes.py` writes Apple Notes into an `apple_notes` table and optionally writes Markdown files under `Personal-Corpus/Notes/...` in the Obsidian vault.
- `bin/index-pdfs.py` and `bin/index-docx.py` index only document metadata into `pdf_index` and `docx_index`; they do not extract full text into a reusable context store.
- `bin/import_ai_history.py` normalizes ChatGPT, Claude, Codex, and Claude Code exports into conversation dictionaries and rendered Markdown; `bin/cron-ingest-codex.py` stores Codex imports in `ai_history_imports` and writes staged Markdown under `staging/ai-history/codex`.

### File And Document Ingestion

- `bin/cron-ingest-codex.py` scans `~/.codex/sessions/**/*.jsonl`, uses `bin/import_ai_history.py`, writes staged Markdown, records rows in `ai_history_imports`, and extracts tool-error observations into `patterns`.
- `bin/import_ai_history.py` flattens provider exports into title, summary, topic tags, quality, and selected key exchanges. Topic extraction is deterministic keyword matching through `TOPIC_MAP`.
- `bin/ingest-apple-notes.py` reads Apple Notes via AppleScript, converts HTML to text, upserts `apple_notes`, and writes vault Markdown with source frontmatter.
- `bin/index-pdfs.py` and `bin/index-docx.py` index filenames, paths, sizes, counts, and document properties, but not extracted body chunks, sections, citations, or embeddings.
- `bin/vault-search.py` walks the Obsidian vault filesystem directly, parses simple frontmatter, and returns capped excerpts for note, grep, handoff, and tag modes.

### Note And Context Indexing

- `tools/context-compile.mjs` indexes `aios/context/**/*.md` at compile time by walking Markdown files, parsing frontmatter, scoring files, and writing `aios/context/compiled/latest.*` plus `aios/context/receipts/latest.*`.
- `aios/context/schema.md` defines required frontmatter fields and optional maintenance/provenance fields for context compiler Markdown files.
- `aios/context/domains/knowledge-systems.md` and `aios/context/packets/knowledge.obsidian-routing.md` define intended graph-style Obsidian routing, but both state that current coverage is partial or planned.
- `aios-ui/server/aios/topic-graph.ts` builds a topic catalog from projects, workflow templates, agent profiles, policy seeds, and curated wiki files, then writes `knowledge_topics`, `knowledge_references`, `knowledge_relationships`, and `knowledge_markers`.
- `services/cts/indexer.py` parses code into CTS nodes/edges and writes full or incremental graph indexes through `services/cts/graph_store.py`.

### Semantic Search

- `services/cts/search.py` exposes `HybridSearcher.semantic_search_nodes`, but it currently fuses FTS and LIKE hits and returns `has_embeddings=False`.
- `services/cts/backends/embedding_backend.py` is a scaffold: it calls `adapter.embed(query)` but returns no search items and warns that the semantic index is not built.
- `services/cts/adapters/embeddings.py` contains a placeholder embedding adapter boundary rather than a configured semantic index.
- `services/second_brain_eval.py` can record and score second-brain retrievals, but it measures retrieval quality after the fact; it is not itself a retrieval engine.

### Keyword And Grep Search

- `bin/vault-search.py` implements vault note retrieval with direct filesystem scans, term containment, H2 section extraction, filename matching for project notes, filename matching for handoffs, and tag filtering.
- `services/operator_search.py` searches operational entities by querying many SQLite tables and doing substring matching in Python, with recency and exact-key boosts.
- `aios-ui/server/aios/operator-search.ts` mirrors the Python operator search with bounded per-kind SQL reads and in-memory substring scoring.
- `services/cts/graph_store.py` provides `search_fts` over `nodes_fts` and `search_like` over node names, qualified names, and paths.
- `services/cts/backends/file_backend.py` shells out to `rg` as a file fallback for code search.

### Project-Specific Context Retrieval

- `bin/hook-session-start.py` builds a compact session packet using the current project, recent handoffs, open bugs, active rules, success criteria, standards, CTS context, RTK compression rules, and resume snapshots.
- `bin/hook-prompt-submit.py` classifies each prompt and retrieves prompt templates, open bugs, archive notes, handoff decisions, handoff next actions, active rules, curated wiki snippets, GitNexus hints, and similar reusable prompts according to `config/retrieval-policy.json`.
- `services/agentize.py` builds an `AgentizedTaskPacket` with required context based on keyword classification, prompt registry metadata, success criteria, standards, relevant skills, and verification steps.
- `aios-ui/server/aios/packet-assembly.ts` assembles ranked briefing packets from project dossiers, topic graph matches, recent runs, recent memory updates, workflow/agent policy, improvement writebacks, and CTS context.
- `services/daily_flow.py` previews or replays the goal -> route -> packet -> run -> evaluation -> writeback -> unresolved delta -> next action flow.

### Agent Prompt Construction

- `bin/hook-session-start.py` injects `<!-- AIOS session context -->` with a compact packet into new sessions.
- `bin/hook-prompt-submit.py` injects `<!-- AIOS retrieval (...) -->` prompt-time context when retrieval fires.
- `services/agentize.py` constructs `AgentizedTaskPacket` objects and persists packet evaluations into `agentize_evaluations`.
- `aios-ui/server/aios/packet-assembly.ts` constructs packet Markdown with sections for objective, workflow stages, handoff contract, topics, stable truths, related runs, policies, likely files, checks, closeout, and expansion hints.
- `schema.sql` stores final packet Markdown and section JSON in `briefing_packets`, with `selection_trace_json`, `omitted_context_json`, `selected_criteria_json`, and `selected_standards_json`.

### Context Packet Generation

- `tools/context-compile.mjs` generates file-backed briefing packets and receipts for `aios/context`.
- `services/portable_context_packet_generator.py` generates privacy-filtered portable packets in `config/context-packets/`, but it selects at most 20 repo files from `git ls-files` and stores high-level file lists, conventions, scripts, success criteria refs, and constraints.
- `aios-ui/server/aios/packet-assembly.ts` generates runtime ranked packets and stores targeted expansions in `packet_expansions`.
- `services/cts/mcp_server.py` generates compact CTS minimal context bundles for code topology with architecture summary, relevant nodes, blast radius, confidence note, and suggested next tools.

### User Preference Retrieval

- `config/retrieval-policy.json` and `config/retrieval-policy.baseline.json` encode prompt retrieval and session packet behavior, including handoff decision retrieval, reusable prompt hints, rule retrieval, and wiki retrieval.
- `bin/hook-session-start.py` reads active rules from an `active_rules` table and standards/success criteria through `services.success_criteria`.
- `services/agentize.py` uses prompt registry metadata and optional asset recommendations from `services.asset_recommendation`.
- `aios-ui/server/routers/prompts.ts` exposes prompt templates only when their body hash is linked in `prompt_library_links`.
- There is no single user-preference memory module in `services/`; preference-like behavior is spread across retrieval policy JSON, active rules, prompt registry links, workflow/skill registries, writebacks, and context Markdown.

### Long-Term Memory Updates

- `bin/hook-stop.py` writes session summary candidates, closes sessions, inserts `memory_updates`, links runs, inserts project and workflow improvement writebacks, records success criteria evaluations, records standards health snapshots, and emits closeout learning signals.
- `services/workflow_promotion.py` emits approval-gated improvement writebacks and promotion lifecycle items.
- `services/learning_analysis.py` detects recurring patterns such as repeated failures, ignored rules, bloated packets, weak prompts, weak workflows, route misroutes, and standards regressions from existing tables.
- `services/second_brain_eval.py` records retrievals, computes precision/recall/staleness, registers gold-set context, and computes second-brain lift for eval runs.
- `memory_writeback_proposals` in `schema.sql` captures divergent-run memory proposals, while `improvement_writebacks` captures broader governed project/workflow/asset writebacks.

### Conflict And Staleness Handling

- `tools/context-compile.mjs` detects context conflicts via frontmatter `conflicts`, resolves immutable global precedence, detects stale selected context when `last_reviewed` is older than 180 days, and emits writeback candidates.
- `aios/context/standards/global.observability.md` requires receipts to expose loaded context, skipped context, conflicts, stale files, and missing context.
- `services/cts/graph_store.py` marks files and nodes stale, while CTS query envelopes in `services/cts/mcp_server.py` warn when stale or low-confidence nodes are present.
- `schema.sql` stores freshness strings and confidence scores in `knowledge_topics` and `knowledge_references`, but not canonical conflict-resolution state for topic graph entries.
- `bin/hook-stop.py` records risks and open questions in `memory_updates`, but does not reconcile them against older memory updates.

### Source And Provenance Tracking

- `schema.sql` stores provenance-like fields in `context_trace_json`, `selection_trace_json`, `omitted_context_json`, `route_result_json`, `reason_json`, `metadata_json`, `evidence_json`, `proposed_change_json`, `provenance_json`, and `source_json`.
- `knowledge_relationships` stores `provenance_kind` and `provenance_id`; `knowledge_references` stores source kind, source id, href, excerpt, freshness, confidence, and metadata.
- `services/notebooklm_synthesis.py` defines `SourceBundle`, `ExcludedSource`, and `NotebookLMProvenance` with source counts, bundle ids, output destinations, and promotion flags.
- `aios-ui/server/aios/packet-assembly.ts` records packet selection traces and expansion traces, but the traces are section/candidate-level rather than source-span-level.
- `bin/vault-search.py` returns path, title, excerpt, and tags for vault results; it does not return stable note IDs, backlink paths, source section offsets, or freshness metadata.

### Prompt Caching Or Stable-Prefix Prompting

- `aios-ui/server/aios/packet-assembly.ts` uses stable section names and a governed handoff contract version, which is cache-friendly at the prompt-shape level.
- `bin/hook-session-start.py` and `bin/hook-prompt-submit.py` construct packets dynamically as plain Markdown strings with changing snippets, timestamps, and selected context.
- `tools/context-compile.mjs` writes deterministic latest files for the same context tree and task text, but it does not split stable invariant prefix content from volatile run-specific suffix content.
- `services/portable_context_packet_generator.py` produces stable JSON-ish packet fields, but package ids are UUID-based by default and included file order depends on repo file order.
- There is no explicit KV-cache-aware local runner or stable-prefix prompt cache implementation in the audited code paths.

### Existing Graph, Entity, Relationship, Or Metadata Storage

- `schema.sql` includes a UI knowledge graph via `knowledge_topics`, `knowledge_relationships`, `knowledge_references`, `knowledge_markers`, and `knowledge_graph_state`.
- `services/cts/migrations.py` includes a code graph via per-repo `nodes`, `edges`, and `nodes_fts` tables.
- `services/cts/graph_store.py`, `services/cts/impact.py`, and `services/cts/mcp_server.py` provide graph queries, impact radius, architecture overview, change detection, and minimal code context.
- `aios-ui/server/aios/topic-graph.ts` materializes knowledge graph nodes and relationships from seed sources, recent runs, packets, memory updates, projects, workflow templates, agent profiles, and curated wiki files.
- `services/cts/flows.py` is currently empty for flow-level graph retrieval: `list_flows` and `get_affected_flows` return empty lists.

## Strengths

- The system has durable operational provenance in `schema.sql`: `orchestration_runs`, `orchestration_run_events`, `workflow_execution_reports`, `briefing_packets`, `packet_expansions`, `success_criteria_evaluations`, and `standards_health_snapshots` support run-level reconstruction.
- Context compilation is deterministic and auditable in `tools/context-compile.mjs`; receipts include selected files, skipped context, conflicts, stale context, missing context, writeback candidates, retrieval trace, and packet contract.
- Code topology has the strongest graph-native implementation today. `services/cts/migrations.py` defines nodes, edges, FTS, confidence, extraction method, stale flags, and repo status, while `services/cts/mcp_server.py` exposes impact radius, graph query, semantic-search envelope, architecture overview, and minimal context.
- The UI knowledge graph has concrete topic/reference/relationship tables in `schema.sql` and a materializer in `aios-ui/server/aios/topic-graph.ts`.
- Prompt-time retrieval is governed by explicit policy in `config/retrieval-policy.json`, making current behavior inspectable and adjustable without code changes.
- Long-term learning is approval-oriented. `bin/hook-stop.py`, `services/workflow_promotion.py`, `services/learning_analysis.py`, and `improvement_writebacks` avoid silently promoting most workflow/prompt/skill changes.
- Retrieval quality can be evaluated after the fact through `services/second_brain_eval.py` and eval tables in `schema.sql`.
- NotebookLM is correctly bounded as an optional synthesis route in `services/notebooklm_synthesis.py`, with source bundles, excluded sources, sensitivity filters, and provenance.

## Weaknesses

- Memory retrieval is fragmented across `bin/hook-prompt-submit.py`, `bin/hook-session-start.py`, `services/agentize.py`, `tools/context-compile.mjs`, `aios-ui/server/aios/packet-assembly.ts`, `aios-ui/server/aios/topic-graph.ts`, `services/operator_search.py`, and CTS. There is no single memory compiler or retrieval contract that arbitrates among them.
- Several retrieval paths are keyword or substring based. `bin/vault-search.py`, `services/operator_search.py`, `aios-ui/server/aios/operator-search.ts`, `services/cts/search.py`, and `tools/context-compile.mjs` all rely on simple term overlap, LIKE, FTS, or frontmatter signal matches.
- The semantic-search surface is named but not implemented with embeddings. `services/cts/search.py` returns `has_embeddings=False`, and `services/cts/backends/embedding_backend.py` returns an empty result set with a scaffold warning.
- Imported documents are not model-ready. `bin/index-pdfs.py` and `bin/index-docx.py` store metadata only; `bin/import_ai_history.py` stores summaries/key exchanges; `bin/ingest-apple-notes.py` stores previews and markdown.
- Context packets flatten structured evidence into text. `services/agentize.py` and `aios-ui/server/aios/packet-assembly.ts` produce strong Markdown packets but lose stable typed edges among source, claim, reason, freshness, conflict, and downstream task section.
- Topic graph data is rebuilt from seeds in `aios-ui/server/aios/topic-graph.ts`; it is graph-shaped but not yet the authoritative memory substrate used by hooks and runtime packets.
- User preference retrieval lacks a unified model. Preferences are spread across `config/retrieval-policy.json`, `active_rules` queries in hooks, prompt registry links, context files, workflow registries, and writebacks.
- Prompt caching is implicit. Stable packet structure exists in `aios-ui/server/aios/packet-assembly.ts`, but volatile data is mixed directly into generated Markdown in hooks and packets.

## Memory Loss Hotspots

- `bin/hook-stop.py` reduces a session to `memory_summary`, `change_items`, `risk_items`, and `open_questions` before inserting `memory_updates`; detailed reasoning, alternatives, failed retrievals, and exact source spans are not preserved there.
- `bin/hook-prompt-submit.py` records only `retrieval_fired` and `retrieval_source` in `prompts_used`; it does not persist the actual retrieved context, selected source ids, rejected candidates, scores, or stale/conflict warnings.
- `bin/hook-session-start.py` writes session packet Markdown to `~/AIOS/logs/session_packet_<session_id>.md` but does not persist that full packet into the root schema unless the session is linked to a governed run through a separate packet path.
- `bin/vault-search.py` returns capped excerpts with a maximum of five results and roughly 300-character snippets; source section offsets, backlinks, note IDs, and skipped candidate lists are lost.
- `bin/import_ai_history.py` selects up to five key exchanges and deterministic summaries; non-selected exchanges remain in rendered markdown but are not represented as retrievable structured turns in `schema.sql`.
- `bin/index-pdfs.py` and `bin/index-docx.py` discard body text entirely after metadata extraction.
- `services/portable_context_packet_generator.py` caps included repo files at 20 and records file paths rather than source excerpts or ranked rationale per file.
- `aios-ui/server/aios/packet-assembly.ts` omits candidates once the token budget is exceeded, but `omitted_context_json` records labels and reasons rather than enough structured source material to learn whether omissions were harmful.
- `services/cts/flows.py` returns no flows, so flow-level memory is currently lost even though CTS nodes and edges exist.

## Flat Retrieval / Semantic-Search-Only Areas

- `bin/vault-search.py` treats the Obsidian vault as flat files for grep, tag, handoff, and project-note lookup. This conflicts with the intended MOC/backlink traversal in `aios/context/packets/knowledge.obsidian-routing.md`.
- `bin/hook-prompt-submit.py` retrieves wiki entries by matching prompt terms against filenames in a configured wiki directory, not by MOC nodes, backlinks, or topic relationships.
- `services/operator_search.py` and `aios-ui/server/aios/operator-search.ts` scan operational tables independently and return mixed-entity hits without graph expansion across run -> packet -> memory_update -> writeback -> finding links.
- `tools/context-compile.mjs` scores context files independently with frontmatter signals, tag matches, title matches, recency, authority, and token cost; only `load_if_matched` and conflict metadata create shallow edges.
- `services/cts/search.py` labels the search method `semantic_search_nodes`, but current ranking is FTS plus LIKE plus confidence/kind boosts.
- `aios-ui/server/aios/topic-graph.ts` creates topic relationships from wiki links and co-mentions, but `searchTopicGraph` is token overlap over catalog entries rather than graph traversal by task intent, relationship type, or evidence path.
- `services/second_brain_eval.py` records retrieval metrics but does not feed missed-source or stale-source signals back into retrieval selection.

## Raw Structured Data That Is Hard For Models To Use

- `schema.sql` stores many high-value fields as JSON text columns: `context_trace_json`, `route_result_json`, `selection_trace_json`, `omitted_context_json`, `sections_json`, `changes_json`, `risks_json`, `open_questions_json`, `evidence_json`, `proposed_change_json`, `source_json`, and `metadata_json`. These are durable but require each retrieval path to know table-specific JSON shapes.
- `memory_updates` in `schema.sql` stores `changes_json`, `risks_json`, and `open_questions_json` as independent lists, but does not link each item to a source artifact, prompt, packet section, criterion, or confidence.
- `ai_history_imports` stores imported conversation metadata, file paths, tags, and quality score, but not normalized per-turn records in the main schema.
- `apple_notes` from `bin/ingest-apple-notes.py` stores `body_preview` and vault path; models must reopen vault Markdown to use the actual note body.
- `pdf_index` and `docx_index` from `bin/index-pdfs.py` and `bin/index-docx.py` store metadata only, so models cannot answer from document contents without separate file reads.
- `briefing_packets.packet_markdown` and `briefing_packets.sections_json` contain model-ready text, but not claim-level citations to specific rows/files/sections.
- `workflow_execution_reports.report_json` is rich but table-specific; `services/operator_search.py` indexes only selected summary fields and does not expose report internals in search hits.
- `services/cts/graph_store.py` stores strong code nodes and edges, but flow-level abstractions are absent in `services/cts/flows.py`.

## Missing Provenance, Staleness, And Conflict Handling

- `bin/hook-prompt-submit.py` does not persist retrieval candidate provenance beyond `retrieval_source`; a later audit cannot see which vault notes, bug rows, handoff rows, wiki files, or prompt templates were injected.
- `bin/vault-search.py` returns paths and excerpts but no freshness labels, source confidence, section offset, backlinks traversed, or skipped results.
- `bin/ingest-apple-notes.py` records source and timestamps in generated Markdown frontmatter, but `apple_notes` has no conflict state for duplicate note titles, moved folders, or divergent vault/Apple Notes copies.
- `bin/index-pdfs.py` and `bin/index-docx.py` record indexed timestamps and file metadata, but no content hash, staleness check against modified time after indexing, or extraction confidence.
- `tools/context-compile.mjs` has conflict and stale-context detection for `aios/context` Markdown only; it does not evaluate conflicts between SQLite memory updates, writebacks, topic graph references, imported notes, and prompt registry hints.
- `aios-ui/server/aios/topic-graph.ts` stores freshness and confidence labels, but relationships do not have conflict status, last-verified timestamps, or invalidation policy beyond `knowledge_graph_state`.
- `schema.sql` includes `consistency_evaluations` and `consistency_findings`, but those findings are not currently part of prompt-time retrieval in `bin/hook-prompt-submit.py`.
- `services/cts/mcp_server.py` exposes stale/low-confidence warnings for CTS, but `bin/hook-session-start.py` drops CTS context entirely unless `index_status == "current"`, losing a chance to explain stale but relevant code topology.

## Prompt Caching Opportunities

- `aios-ui/server/aios/packet-assembly.ts` has stable section titles and a `GOVERNED_HANDOFF_CONTRACT_VERSION`; these sections could be separated into a stable prefix and a volatile evidence suffix.
- `bin/hook-session-start.py` repeatedly injects agent rules, success criteria labels, standards labels, RTK rules, and user-story verification guidance. These stable blocks are mixed with volatile project/handoff/bug/run data.
- `bin/hook-prompt-submit.py` dynamically injects retrieval snippets and prompt template hints. Template instructions from `prompts/registry.json` and policy text from `config/retrieval-policy.json` are stable relative to retrieved evidence.
- `tools/context-compile.mjs` always writes `latest.*` and includes selected rules, risks, acceptance criteria, and receipts together. Immutable global standards and schema/router bootloader content are stable cache-prefix candidates.
- `services/agentize.py` includes stable classification enums, execution mode rules, constraints, non-goals, verification-step shapes, and output contracts alongside volatile request-specific details.
- `services/portable_context_packet_generator.py` generates UUID packet ids by default, which makes otherwise similar portable packets less cache-stable.
- `aios/context/standards/*.md`, `aios/context/schema.md`, `aios/context/router.md`, and `config/agent-rules.md` are stable authority sources that currently flow into generated packets as ordinary selected context.

## Implementation Recommendations

Ranked by impact x effort, with impact and effort rated High, Medium, or Low.

| Rank | Impact | Effort | Recommendation | Evidence |
| --- | --- | --- | --- | --- |
| 1 | High | Medium | Define a single memory retrieval contract that returns source id, source path/table, excerpt/body, score, freshness, confidence, conflict status, and trace reason for prompt-time hooks, runtime packets, UI topic graph, operator search, and CTS. | Current retrieval surfaces are split across `bin/hook-prompt-submit.py`, `bin/hook-session-start.py`, `services/agentize.py`, `aios-ui/server/aios/packet-assembly.ts`, `services/operator_search.py`, and `services/cts/mcp_server.py`. |
| 2 | High | Medium | Persist prompt-time retrieval traces from `bin/hook-prompt-submit.py`, including selected source rows/files, skipped candidates, scores, injected text hash, and stale/conflict warnings. | `prompts_used` in `schema.sql` records only `retrieval_fired` and `retrieval_source`, while `bin/hook-prompt-submit.py` can inject context without durable candidate evidence. |
| 3 | High | Medium | Convert `memory_updates` from flat closeout summaries into typed memory items linked to artifacts, prompts, packet sections, criteria findings, run events, and writebacks. | `bin/hook-stop.py` inserts compact `memory_summary`, `changes_json`, `risks_json`, and `open_questions_json`; `schema.sql` has adjacent linkable tables but no item-level memory edges. |
| 4 | High | High | Make the UI `knowledge_topics` graph an authoritative service-level memory graph instead of a UI-side materialization path. | `schema.sql` has graph tables and `aios-ui/server/aios/topic-graph.ts` populates them, but hooks and `services/agentize.py` do not retrieve through that graph. |
| 5 | High | Medium | Implement MOC/backlink/tag traversal for Obsidian retrieval and route prompt-time wiki retrieval through it. | `aios/context/packets/knowledge.obsidian-routing.md` says MOC-first graph traversal is planned; `bin/vault-search.py` and `bin/hook-prompt-submit.py` still use flat grep, filename, and term matching. |
| 6 | High | Medium | Add document content chunking and source-span storage for PDF, DOCX, Apple Notes, and AI history imports. | `bin/index-pdfs.py` and `bin/index-docx.py` store metadata only; `bin/ingest-apple-notes.py` stores preview plus vault Markdown; `bin/import_ai_history.py` stores summaries/key exchanges and staged Markdown. |
| 7 | Medium | Low | Promote CTS stale/low-confidence warnings into session packets rather than suppressing CTS context when the index is stale. | `services/cts/mcp_server.py` produces warnings, but `bin/hook-session-start.py` returns CTS context only when `payload.get("index_status") == "current"`. |
| 8 | Medium | Medium | Replace misleading `semantic_search_nodes` naming or wire a real embedding index for CTS. | `services/cts/search.py` returns FTS/LIKE results with `has_embeddings=False`; `services/cts/backends/embedding_backend.py` returns no items. |
| 9 | Medium | Medium | Normalize JSON blob fields that are used for retrieval into queryable item tables or typed projections. | Retrieval-relevant data is stored in JSON columns throughout `schema.sql`, including packet sections, traces, writeback evidence, workflow reports, memory changes, and route results. |
| 10 | Medium | Medium | Add conflict/staleness reconciliation for memory updates, writebacks, knowledge references, prompt hints, and imported corpus entries. | `tools/context-compile.mjs` handles conflicts/staleness only for `aios/context` Markdown; `schema.sql` has no equivalent conflict state for `memory_updates`, `knowledge_references`, `improvement_writebacks`, or `ai_history_imports`. |
| 11 | Medium | Low | Feed `services/second_brain_eval.py` missed-source and stale-source metrics back into retrieval policy or packet assembly decisions. | Eval retrieval metrics are durable in `eval_second_brain_retrievals`, but `bin/hook-prompt-submit.py`, `services/agentize.py`, and `aios-ui/server/aios/packet-assembly.ts` do not use them. |
| 12 | Medium | Low | Split stable prompt prefixes from volatile evidence in hooks and packet assembly. | Stable sections exist in `aios-ui/server/aios/packet-assembly.ts`, `services/agentize.py`, `tools/context-compile.mjs`, and `bin/hook-session-start.py`, but all current outputs mix stable and volatile content. |
| 13 | Medium | Low | Record enough omitted-context detail to learn from packet misses. | `briefing_packets.omitted_context_json` and `aios-ui/server/aios/packet-assembly.ts` record omitted labels and reasons, but not source snippets, source ids, or expected usefulness signals. |
| 14 | Low | Low | Implement or remove flow-level CTS placeholders. | `services/cts/flows.py` currently returns empty lists for `list_flows` and `get_affected_flows`. |
| 15 | Low | Low | Make portable context packet ids optionally deterministic for repeated equivalent packet inputs. | `services/portable_context_packet_generator.py` uses UUID packet ids even when task, repo, and selected content are otherwise stable. |

## Plan 12-01 Contract Coverage Check

- Current architecture summary covers raw storage, ingestion, indexing, semantic search, keyword search, project context retrieval, prompt construction, context packet generation, user preference retrieval, long-term memory updates, conflict/staleness handling, provenance tracking, prompt caching, and graph/entity/relationship storage.
- Required findings sections are present: strengths, weaknesses, memory loss hotspots, flat retrieval areas, raw structured data issues, missing provenance/staleness/conflict handling, prompt caching opportunities, and ranked implementation recommendations.
- Findings cite concrete repo files and modules, including `schema.sql`, `bin/*`, `services/*`, `services/cts/*`, `tools/context-compile.mjs`, `aios/context/*`, `config/*`, and `aios-ui/server/aios/*`.
- Recommendations are written as Plan 12-02 through 12-08 inputs and cite the files or services where follow-up work can start.
