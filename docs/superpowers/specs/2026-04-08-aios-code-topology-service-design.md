---
type: spec
title: AIOS Code Topology Service — Architecture and Integration Design
date: 2026-04-08
status: draft
author: jakyeamos
donor: tirth8205/code-review-graph
project: Knowledge-Graph
---

# AIOS Code Topology Service

## Executive Summary

AIOS agents currently have no persistent structural understanding of the codebases they operate on. Every session re-discovers file layouts, call relationships, and blast-radius through brute-force file reads. This is expensive, slow, and inconsistent.

`tirth8205/code-review-graph` is a well-built open-source repo that proves the structural primitive works: Tree-sitter parsing, SQLite graph storage, incremental updates, hybrid search, MCP exposure, and impact analysis have been implemented and partially benchmarked. Its headline metric — 8.2x token reduction — is credible, though its F1 of 0.54 and 33% flow recall in some languages reveal that it is a strong foundation with real gaps.

**The recommendation:** fork and integrate selectively. Do not vendor or wrap the repo. Extract five core modules (parser, graph store, incremental updater, hybrid search, blast-radius), augment them with an AIOS-native confidence and provenance model, and expose them through a pluggable backend abstraction that prevents permanent coupling to any single structural source.

The subsystem is named the **Code Topology Service (CTS)** rather than "Code Memory Service" — topology accurately describes what it stores (structural relationships), avoids over-claiming memory semantics, and signals that the service is a map, not an oracle.

**What CTS is not:** it is not an agent reasoning engine, not a code execution environment, not a replacement for direct file reads when confidence is insufficient. It is a shared, persistent, queryable map of code structure that agents can consult before deciding how much direct exploration is necessary.

V1 scope: structural indexing for Python and TypeScript repos, blast-radius queries, hybrid node search, confidence-gated output, and integration with AIOS session/project context. Everything else is explicitly deferred.

**Estimated V1 effort:** 6–8 focused days. The parser and graph primitives require the most care; the MCP layer and session integration are mechanical after the data model is right.

---

## Section 1 — Donor Audit

### Module-by-module classification

---

#### `parser.py` — Multi-language AST extraction
**Classification: Fork and modify**

The Tree-sitter core covering 28 languages is the most valuable artifact in the repo. The node types (File, Class, Function, Type) and edge types (CALLS, IMPORTS_FROM, INHERITS, CONTAINS, TESTED_BY, DEPENDS_ON) are an appropriate vocabulary for AIOS.

**Worth adopting:** the language dispatch table, the node/edge extraction logic for Python, the Jupyter notebook handling, and the test-file detection heuristics.

**Requires modification:** TypeScript/JavaScript parsing has four documented structural gaps that matter for AIOS's primary codebases:
- No dynamic `require()` resolution (only static string literals)
- Complex destructuring imports may be missed
- No type-inference for calls to dynamically-typed functions — call edges become unresolved
- Template literal imports are not tracked

For Next.js codebases these gaps are common patterns, not edge cases. The forked version must add an `unresolved_call_count` field per file so consumers know when a file's call graph is incomplete.

**Do not adopt as-is:** the TypeScript path alias resolution is delegated to `tsconfig_resolver.py` (see below), but the parser itself makes no attempt to surface resolution confidence.

---

#### `tsconfig_resolver.py` — TypeScript path alias resolution
**Classification: Fork and extend**

The core concept (walk up to tsconfig.json, parse path aliases, probe filesystem) is correct. The known gaps:
- Does not process `extends` chains that reference `node_modules/` (e.g., `@tsconfig/strictest`)
- Silently returns `None` on any exception — no diagnostic output
- Does not resolve npm package locations, only local path aliases
- Limited to five file extensions

For AIOS: extend to handle `node_modules` extends chains, add a `resolution_failure_log` output so the indexer can record which imports were unresolvable, and add a `@/*` → `src/` default fallback for projects that forget to specify `baseUrl`.

---

#### `graph.py` — SQLite storage and BFS impact analysis
**Classification: Fork and heavily modify**

The table schema (`nodes`, `edges`, `metadata`), WAL mode setup, and recursive CTE impact analysis are all solid. The CTE-based BFS traversal is preferable to the NetworkX legacy path — use it exclusively.

**Critical gap:** the schema has zero confidence or provenance fields. This is the single biggest architectural difference between what the donor built and what AIOS needs. Every node and edge must carry:
- `confidence REAL DEFAULT 1.0` — how reliable is this structural fact
- `extraction_method TEXT` — `tree_sitter | lsp | inferred | manual`
- `last_verified_at TEXT` — when was this relation last confirmed by a build/test run
- `is_stale INTEGER DEFAULT 0` — set when the source file hash changes but re-parsing has not yet occurred

Every edge additionally needs:
- `resolution_method TEXT` — `static | alias_resolved | lsp | unresolved`

Without these fields, AIOS cannot distinguish "this call edge was verified by the language server" from "this call edge is a best guess based on a name match." Presenting them identically would be worse than having no graph at all.

**Retain:** recursive CTE impact analysis, WAL mode, busy timeout, `_sanitize_name()` for MCP exposure safety.

---

#### `migrations.py` — Schema evolution
**Classification: Adopt pattern, rewrite content**

The idempotent IF NOT EXISTS migration pattern is good practice. The v1–v6 progression demonstrates clean schema evolution without destructive changes. Adopt this as the structural pattern for AIOS CTS's own migration chain. Do not copy the migration SQL content — AIOS CTS starts with its own schema that includes confidence and provenance fields from v1.

---

#### `incremental.py` — Change detection and watch
**Classification: Adopt mostly as-is**

The git diff + watchdog combination is exactly right. SHA-256 hash comparison for skip-on-unchanged is correct and prevents unnecessary re-parsing. Dependent file tracking (2-hop traversal, 500-file cap) is a well-calibrated default.

The only required modification: replace the donor's JSON registry lookups with reads from `aios.db.projects.repo_path`. AIOS has a single-authority SQLite principle; a second JSON registry file violates it.

The 300ms debounce in watch mode is appropriate for local development. Keep it.

---

#### `main.py` + tools — MCP server and 22 tool implementations
**Classification: Reimplement from scratch; use donor as specification**

The donor's MCP layer is directly coupled to its internal Python APIs and ships as a standalone FastMCP server. AIOS CTS cannot adopt this directly because:
1. AIOS needs the MCP layer to route through the backend abstraction, not directly to graph.py
2. Results must be confidence-gated before exposure (callers should not see low-confidence edges without a warning)
3. AIOS session and project context must be respected (which repo is active, what the current branch is)

The 22 tool contracts and 5 prompt templates are the best available specification for what AIOS CTS should expose. Treat them as a design document, not as code to port. The subset worth implementing in V1:

**Priority 1 (MVP):**
- `get_minimal_context(task, changed_files, repo_root)` — ultra-compact structural context
- `get_impact_radius(changed_files, max_depth, repo_root)` — blast-radius analysis
- `semantic_search_nodes(query, kind, limit, repo_root)` — hybrid search
- `query_graph(pattern, target, repo_root)` — structural exploration
- `get_architecture_overview(repo_root)` — high-level structure summary
- `detect_changes(base, changed_files, repo_root)` — risk-scored diff analysis

**Priority 2 (Phase 3+):**
- `list_flows(sort_by, limit, repo_root)` — execution flows
- `get_affected_flows(changed_files, repo_root)` — flow impact
- `list_communities(sort_by, repo_root)` — community structure
- `cross_repo_search(query, kind)` — multi-repo search

**Defer indefinitely:**
- `apply_refactor_tool` — too risky; requires source modification
- `generate_wiki_tool` — nice-to-have, Phase 5+
- `embed_graph_tool` — invoked only if embeddings adapter is loaded

**5 MCP prompts:** all five (review_changes, architecture_map, debug_issue, onboard_developer, pre_merge_check) are useful as prompt template designs. Reimplement them as AIOS CTS prompts that reference confidence scores in their outputs.

---

#### `search.py` — Hybrid FTS5 + vector + LIKE
**Classification: Fork**

The RRF fusion logic is solid. FTS5 with porter/unicode61 stemming is correct. The graceful degradation chain (vector → FTS5 → LIKE fallback) is the right pattern for a system where embeddings are optional. The kind-boosting heuristics (PascalCase → Class, snake_case → Function, dotted → qualified name) are clever and worth porting.

Known gaps to address in AIOS fork:
- No phrase-aware scoring — add exact phrase boosting before FTS5
- Embedding availability is silent — add a `has_embeddings: bool` field to search result metadata
- Kind filtering happens post-merge, wasting ranked results — move filter upstream

---

#### `embeddings.py` — Optional vector embeddings
**Classification: Adopt mostly as-is (optional module)**

The three-provider design (sentence-transformers, Gemini, MiniMax) with graceful fallback is good. Keep as an optional semantic enrichment adapter in AIOS CTS. Do not make it a required dependency. If no embeddings provider is configured, hybrid search degrades to FTS5 + LIKE, which is acceptable for V1.

---

#### `flows.py` — Execution flow detection
**Classification: Reimplement from scratch**

The Python-framework-centric entry point detection (decorator patterns for `@app.get`, `@celery.task`) does not generalize to TypeScript/Next.js. The 33% recall in some languages is a documented regression. For AIOS, flow detection must be built on top of language server data, not static decorator scanning.

Keep the criticality scoring formula (file spread 30%, external calls 20%, security sensitivity 25%, test coverage gap 15%, depth 10%) as an inspiration for AIOS's own flow criticality model. The formula is reasonable; the entry point detection is the problem.

For V1: do not implement flow detection. For Phase 3: implement via language server adapter (tsserver for TypeScript, pyright LSP for Python). The donor's BFS traversal code can serve as a reference for the traversal logic once real call edges are available.

---

#### `communities.py` — Community detection via Leiden
**Classification: Adopt mostly as-is (Phase 5+)**

Leiden algorithm via igraph is the correct choice for modularity-based community detection. The hierarchical naming strategy, cohesion scoring, and cross-community coupling warnings are all useful. Defer to Phase 5 — not needed for MVP impact analysis or search. igraph is a heavy dependency to add for a deferred feature.

---

#### `changes.py` — Risk scoring for git diffs
**Classification: Fork**

The 6-factor risk formula (flow participation, community crossing, test coverage, security sensitivity, caller count) is a solid heuristic with well-calibrated weights. The git diff → line range → node matching logic is directly useful.

Required modifications for AIOS:
- Risk score reliability must reflect index confidence: a node with `confidence < 0.5` should produce a risk score annotated as `low_confidence_estimate: true`
- Stale nodes (source file changed since last index) must be flagged in output
- Add `index_coverage_pct` to the summary output so agents know what fraction of changed functions were found in the graph vs. not indexed

---

#### `registry.py` — Multi-repo registry
**Classification: Fork and modify significantly**

The LRU connection pool (10 connections, LRU eviction) is directly reusable. The registration and alias-lookup logic is good.

Required change: eliminate the JSON registry file (`~/.code-review-graph/registry.json`). AIOS's single-authority SQLite principle (STORES.md) prohibits parallel truth sources. AIOS CTS reads repo registration from `aios.db.projects` (`id`, `repo_path`, `name`). The connection pool stays; the JSON file goes.

---

#### `refactor.py` — Rename and dead code detection
**Classification: Ignore for V1**

Rename preview and dead code detection are useful but not in scope. Deferred.

---

#### `hints.py` — Review hints
**Classification: Ignore**

Tightly coupled to the code review workflow. Not applicable to AIOS's use cases.

---

#### `wiki.py` — Markdown wiki generation
**Classification: Ignore for V1**

Potential future use in aios-ui as an "architecture snapshot" export. Deferred.

---

#### `visualization.py` — D3.js HTML graph
**Classification: Ignore for V1**

Standalone HTML output does not fit AIOS's server-side data model. Deferred to Phase 5+.

---

#### `skills.py` — Claude Code skill definitions
**Classification: Ignore**

AIOS has its own skill and hook system. Not applicable.

---

#### `eval/` — Benchmarking framework (runner.py, scorer.py, token_benchmark.py)
**Classification: Fork structure, replace content**

The runner + scorer + reporter pattern is exactly what AIOS CTS needs for its own evaluation harness. Use the structural pattern; replace the benchmark cases with AIOS-specific ones (TypeScript, Next.js, monorepo, bug-localization — see Section 6).

---

### Donor audit summary table

| Module | Classification | Rationale |
|---|---|---|
| `parser.py` | Fork and modify | Core is solid; TS/JS gaps require extension; add resolution confidence |
| `tsconfig_resolver.py` | Fork and extend | Add `node_modules` extends, diagnostic mode, `@/*` default |
| `graph.py` | Fork and heavily modify | Add confidence, provenance, extraction_method, staleness fields |
| `migrations.py` | Adopt pattern, rewrite content | Idempotent migration pattern is good; content is wrong for AIOS |
| `incremental.py` | Adopt mostly as-is | Replace JSON registry with aios.db.projects |
| `main.py` + tools | Reimplement (use as spec) | Contracts are valuable; implementation too tightly coupled |
| `search.py` | Fork | RRF logic + kind-boosting worth porting; fix post-merge filter |
| `embeddings.py` | Adopt mostly as-is | Optional enrichment adapter; keep all three providers |
| `flows.py` | Reimplement from scratch | Python-centric; TS/Next.js needs LSP, not static decorators |
| `communities.py` | Adopt mostly as-is (Phase 5+) | Leiden is correct; igraph dep too heavy for V1 |
| `changes.py` | Fork | 6-factor formula solid; add confidence and staleness annotations |
| `registry.py` | Fork and modify | LRU pool reusable; JSON registry → aios.db.projects |
| `refactor.py` | Ignore for V1 | Out of V1 scope |
| `hints.py` | Ignore | Wrong abstraction for AIOS |
| `wiki.py` | Ignore for V1 | Deferred |
| `visualization.py` | Ignore for V1 | Deferred |
| `skills.py` | Ignore | AIOS has its own skill system |
| `eval/` | Fork structure, replace content | Good framework; need AIOS-specific test cases |

---

## Section 2 — AIOS Placement

### Where CTS lives

CTS is a **shared infrastructure service** within AIOS. It is not a hook, not a bin script, and not a session-scoped ephemeral. It is a persistent, repo-scoped index that any AIOS component can query.

```
AIOS/
├── services/
│   └── cts/                        ← Code Topology Service
│       ├── __init__.py
│       ├── indexer.py              ← Orchestrates full and incremental builds
│       ├── graph_store.py          ← AIOS-native SQLite schema + queries (forked from graph.py)
│       ├── parser.py               ← Multi-language AST extraction (forked)
│       ├── tsconfig_resolver.py    ← TS path alias resolution (forked + extended)
│       ├── incremental.py          ← Git diff + watchdog change detection (forked)
│       ├── search.py               ← Hybrid FTS5 + RRF (forked)
│       ├── impact.py               ← Blast-radius and risk scoring (forked from changes.py)
│       ├── registry.py             ← LRU connection pool, reads from aios.db (forked)
│       ├── confidence.py           ← Confidence model and staleness scoring (new)
│       ├── migrations.py           ← AIOS CTS schema migrations (new, v1+)
│       ├── mcp_server.py           ← FastMCP server exposing CTS tools (reimplemented)
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── base.py             ← Backend protocol (ABC)
│       │   ├── graph_backend.py    ← Structural graph backend (primary)
│       │   ├── fts_backend.py      ← FTS5 text/keyword backend
│       │   ├── embedding_backend.py← Optional vector backend
│       │   ├── lsp_backend.py      ← Language server adapter (Phase 3+)
│       │   └── file_backend.py     ← Direct file exploration fallback
│       ├── adapters/
│       │   ├── embeddings.py       ← Provider adapter (forked from embeddings.py)
│       │   └── lsp_client.py       ← LSP protocol adapter (new, Phase 3+)
│       └── eval/
│           ├── runner.py           ← Benchmark runner (forked structure)
│           ├── scorer.py           ← Metrics (forked structure)
│           ├── token_benchmark.py  ← Token usage measurement (forked)
│           └── cases/              ← AIOS-specific benchmark cases (new)
├── bin/
│   ├── cts-build.py               ← CLI: full index build for a repo
│   ├── cts-update.py              ← CLI: incremental update
│   ├── cts-watch.py               ← CLI: start file watcher
│   ├── cts-status.py              ← CLI: index health and coverage report
│   └── cts-eval.py                ← CLI: run benchmark suite
└── data/
    └── cts/                        ← Per-repo graph databases
        └── <repo_hash>/
            └── graph.db            ← CTS graph store for that repo
```

### What CTS owns

- All code structural facts (nodes, edges, flows, communities) for indexed repos
- The confidence and provenance model for those structural facts
- The per-repo graph.db files under `~/AIOS/data/cts/`
- The incremental indexing pipeline (watcher, diff detection, re-parse)
- The multi-repo connection registry (backed by aios.db.projects)
- The MCP tool surface for agent queries

### What CTS does not own

- Source files — AIOS observes code, never modifies it
- aios.db — CTS reads from `projects` but does not write to it
- Vault content — no structural facts go into the Vault
- Session context — CTS provides data; session hooks decide what to inject
- Language server processes — CTS may invoke an LSP client but does not manage LSP lifecycle

### How other AIOS components call CTS

**Session hooks** call CTS via its Python API (not MCP) during session start and prompt submit:
```python
# hook-session-start.py: get compact structural context for the active repo
from services.cts import get_minimal_context
ctx = get_minimal_context(repo_path=cwd, task=objective, max_tokens=300)
```

**Agents and MCP clients** call CTS via its MCP server (FastMCP, stdio transport), the same mechanism used by other MCP tools in Claude Code.

**AIOS UI** (future) calls CTS via tRPC endpoints that wrap the Python CTS API, consistent with the aios-ui architecture.

### Data persistence scoping

| Data | Scope | Location |
|---|---|---|
| Node and edge graph | Per-repo, per-commit-hash | `~/AIOS/data/cts/<repo_hash>/graph.db` |
| FTS5 virtual table | Per-repo (in graph.db) | Same as above |
| Flow and community tables | Per-repo (in graph.db) | Same as above |
| Risk index | Per-repo, rebuilt on update | Same as above |
| Embedding vectors | Per-repo (optional) | `~/AIOS/data/cts/<repo_hash>/embeddings.db` |
| Registry | Global (reads aios.db) | `~/AIOS/data/aios.db` projects table |
| Benchmark results | Global | `~/AIOS/data/cts/eval_results.json` |

**Branch awareness:** CTS does not maintain separate databases per branch. Instead, it tracks `current_commit_hash` in the graph.db `metadata` table and marks nodes as `is_stale = 1` when the source file hash changes after a branch switch. A branch switch triggers an incremental update automatically if `cts-watch` is running, or marks the index as `needs_update` if it is not.

---

## Section 3 — Data Model and Contracts

### Canonical node model

```python
@dataclass
class CTSNode:
    # Identity
    id: str                         # SHA256(qualified_name + repo_id)
    repo_id: str                    # FK → aios.db.projects.id
    kind: NodeKind                  # File | Class | Function | Type | Test
    name: str
    qualified_name: str             # unique within repo

    # Location
    file_path: str
    line_start: int
    line_end: int
    language: str

    # Structure
    parent_qualified: str | None
    params: str | None
    return_type: str | None
    modifiers: list[str]
    is_test: bool
    file_hash: str                  # SHA256 of source file at index time

    # Confidence and provenance (AIOS additions)
    confidence: float               # 0.0–1.0; starts at method-specific default
    extraction_method: ExtractionMethod  # tree_sitter | lsp | inferred | manual
    last_verified_at: str | None    # ISO8601; when this node was last confirmed valid
    is_stale: bool                  # True if source file changed since last index
    unresolved_call_count: int      # number of call edges that could not be resolved
    extra: dict                     # JSON bag for future extension

    updated_at: str
```

### Canonical edge model

```python
@dataclass
class CTSEdge:
    id: str
    repo_id: str
    kind: EdgeKind          # CALLS | IMPORTS_FROM | INHERITS | IMPLEMENTS
                            # CONTAINS | TESTED_BY | DEPENDS_ON
    source_qualified: str
    target_qualified: str
    file_path: str
    line: int               # supports multiple call sites (list packed into JSON)

    # Confidence and provenance (AIOS additions)
    confidence: float               # 0.0–1.0
    resolution_method: ResolutionMethod  # static | alias_resolved | lsp | unresolved | inferred
    is_stale: bool

    extra: dict
    updated_at: str
```

### Confidence defaults by extraction method

| Method | Default node confidence | Default edge confidence | Notes |
|---|---|---|---|
| `lsp` | 0.95 | 0.90 | Language server verification |
| `tree_sitter` (resolved) | 0.75 | 0.70 | Static parse, alias resolved |
| `tree_sitter` (unresolved) | 0.75 | 0.40 | Static parse, call target not found |
| `inferred` | 0.50 | 0.40 | Heuristic / pattern match |
| `manual` | 1.00 | 1.00 | Human-confirmed |

### Repo identity model

```python
@dataclass
class CTSRepo:
    repo_id: str            # FK → aios.db.projects.id
    repo_path: str          # absolute path to repo root
    name: str               # from aios.db.projects.name
    current_commit: str     # git rev-parse HEAD at last full build
    last_full_build_at: str
    last_incremental_at: str
    index_status: IndexStatus   # current | needs_update | building | failed
    node_count: int
    edge_count: int
    coverage_pct: float         # fraction of files successfully parsed
    language_breakdown: dict    # {"typescript": 0.6, "python": 0.3, ...}
```

### Query result schema

All CTS query results carry an index quality envelope:

```python
@dataclass
class CTSQueryResult:
    query_type: str
    repo_id: str
    index_age_seconds: int
    index_status: IndexStatus
    coverage_pct: float
    has_low_confidence_results: bool
    has_stale_results: bool
    fallback_used: FallbackType | None  # None | fts | file_exploration
    results: list[CTSNode | CTSEdge | ...]
    confidence_summary: ConfidenceSummary
    warnings: list[str]                 # human-readable caveats
```

### Minimal context bundle schema

Returned by `get_minimal_context()`. Target: ≤300 tokens.

```python
@dataclass
class MinimalContextBundle:
    repo_name: str
    index_status: IndexStatus
    architecture_summary: str           # 1–3 sentences from community structure
    directly_relevant_nodes: list[str]  # qualified names, ≤10
    estimated_blast_radius: int         # count of potentially affected files
    confidence_note: str | None         # e.g., "TS call graph 40% unresolved"
    suggested_next_tools: list[str]     # what to call next
```

### Blast-radius result schema

```python
@dataclass
class BlastRadiusResult:
    changed_nodes: list[CTSNode]
    impacted_nodes: list[CTSNode]
    impacted_files: list[str]
    edges: list[CTSEdge]
    truncated: bool
    total_impacted: int
    risk_summary: RiskSummary
    low_confidence_count: int       # impacted nodes with confidence < 0.6
    stale_count: int                # nodes that need re-indexing
    unindexed_changed_files: list[str]  # files not in the graph at all
```

### Fallback trigger schema

```python
@dataclass
class FallbackTrigger:
    reason: FallbackReason  # stale_index | low_confidence | not_indexed
                            # lsp_unavailable | graph_error | no_results
    affected_files: list[str]
    recommended_action: FallbackAction  # use_fts | use_file_exploration
                                        # rebuild_index | escalate_to_agent
    confidence_at_trigger: float
```

### Trust hierarchy

CTS results are never presented as uniformly reliable. The system distinguishes four trust levels:

| Trust level | Condition | Agent guidance |
|---|---|---|
| **Structural fact** | `extraction_method = lsp`, `confidence >= 0.85`, `is_stale = false` | Trust; use directly |
| **Inferred relation** | `extraction_method = tree_sitter`, `confidence >= 0.60` | Use with awareness; spot-verify critical paths |
| **Semantically degraded** | `confidence < 0.60` OR `unresolved_call_count > threshold` | Use for orientation only; verify with file reads |
| **Stale / unreliable** | `is_stale = true` | Do not trust; trigger incremental update first |

These levels are surfaced in `CTSQueryResult.warnings` and in the `confidence_summary` block. Agents are never left to infer trust from raw numbers.

---

## Section 4 — Backend Strategy

### The problem with graph-only

The donor's evaluation numbers tell the story: F1 = 0.54 average, 33% recall in some languages for flow detection, and documented gaps in TypeScript dynamic patterns. A system that routes all agent queries through a single structural backend will confidently produce wrong answers for a material fraction of queries.

AIOS CTS solves this with a pluggable backend model. The graph backend is the primary source for structural facts, but it is never the only source, and callers always know which backend answered a query.

### Backend protocol

```python
class CTSBackend(Protocol):
    name: str
    supported_query_types: set[QueryType]
    confidence_floor: float         # minimum confidence this backend can produce

    def is_available(self, repo_id: str) -> bool: ...
    def search(self, query: SearchQuery) -> BackendResult: ...
    def get_node(self, qualified_name: str, repo_id: str) -> CTSNode | None: ...
    def get_impact_radius(self, changed_files: list[str], repo_id: str) -> BlastRadiusResult: ...
    def health(self) -> BackendHealth: ...
```

### Backends in V1

**`graph_backend.py`** (primary, always loaded)
- Source: tree-sitter parsed nodes/edges in `graph.db`
- Confidence range: 0.40–0.95 depending on resolution method
- Strength: fast structural queries, BFS impact analysis, community structure
- Weakness: TS/JS dynamic patterns, unresolved calls, no runtime behavior

**`fts_backend.py`** (always loaded, lightweight fallback)
- Source: FTS5 virtual table in `graph.db`
- Confidence range: 0.30–0.70 (keyword match, no structural verification)
- Strength: finds code by name/keyword when graph has no result
- Weakness: no structural relationships, no impact analysis

**`embedding_backend.py`** (optional, loaded if provider configured)
- Source: vector embeddings per node in `embeddings.db`
- Confidence range: 0.50–0.80 (semantic similarity, not structural)
- Strength: "find similar code to this concept" queries
- Weakness: expensive to build, no structural relationships

**`lsp_backend.py`** (optional, Phase 3+)
- Source: TypeScript Language Server or pyright via LSP protocol
- Confidence: 0.90–0.98 for TypeScript; 0.85–0.95 for Python
- Strength: exact call resolution, type-aware edges, no parse gaps
- Weakness: requires language server to be running, per-query latency ~50–200ms

**`file_backend.py`** (always loaded, last resort)
- Source: direct filesystem reads (grep, glob, read)
- Confidence: 0.20–0.50 (heuristic matching, no AST)
- Strength: always available, never stale
- Weakness: expensive (token usage), no structural graph

### Backend selection logic

```python
class CTSRouter:
    def route(self, query: CTSQuery) -> list[BackendResult]:
        results = []

        # Primary: graph backend if index is current
        if self.graph.is_available(query.repo_id) and not self.graph.is_stale(query):
            result = self.graph.execute(query)
            if result.confidence_summary.mean >= CONFIDENCE_THRESHOLD:
                return self._fuse([result])
            results.append(result)

        # Supplement: FTS for low-confidence node lookups
        if query.type in (SEARCH, LOOKUP) and result.has_low_confidence_results:
            results.append(self.fts.execute(query))

        # Supplement: embeddings for semantic queries
        if self.embeddings.is_available() and query.type == SEMANTIC_SEARCH:
            results.append(self.embeddings.execute(query))

        # Escalate: LSP for unresolved calls if available
        if self.lsp.is_available() and result.unresolved_call_count > 0:
            results.append(self.lsp.resolve_calls(result.unresolved_edges))

        # Last resort: file exploration for completely unindexed files
        unindexed = query.changed_files - result.indexed_files
        if unindexed:
            results.append(self.file.explore(unindexed))

        return self._fuse(results)
```

### Fusion strategy

Results from multiple backends are fused via RRF (reciprocal rank fusion), the same algorithm used in `search.py`. The key difference: each backend result carries its confidence floor, which weights the RRF score. A graph backend result at confidence 0.80 outranks an embedding result at confidence 0.60 for the same node, even if the embedding ranked it higher.

### Graph-only answer policy

Graph-only answers (no verification from other backends) are permitted when:
- `index_status = current` (commit hash matches last full build)
- `mean_confidence >= 0.75` for the result set
- `stale_count = 0`
- `unresolved_call_count = 0` for the relevant nodes

Graph-only answers are **not** permitted when:
- The query involves TypeScript files with dynamic patterns (detected by `unresolved_call_count > 0`)
- Any node in the result set is marked `is_stale = true`
- The query is a blast-radius analysis for a production deploy decision

### Source verification requirement

Direct source file verification (reading actual files) is mandatory when:
- An agent is about to make a write to a file (code edit, refactor)
- The blast-radius result contains stale nodes for any of the changed files
- The query asks "does X call Y" and the edge confidence is < 0.6
- The risk score for a changed node is > 0.7 and it has low-confidence edges

In these cases, CTS returns `recommended_action: verify_source_before_acting` in the query result.

### Escalation to broader exploration

CTS triggers a `FallbackTrigger` with `recommended_action: escalate_to_agent` when:
- More than 30% of changed files are unindexed
- The graph backend fails (database locked, corrupted, etc.)
- The query requires cross-file type resolution that the graph cannot satisfy
- Any critical-path node has `is_stale = true` and an incremental update has not completed

---

## Section 5 — Integration Plan

### Phase 0 — Audit and benchmark harness
**Goal:** establish a factual baseline before writing any production code

**Deliverables:**
- `services/cts/eval/cases/` — 20 benchmark queries across 5 repos (TypeScript, Python, Go, monorepo, Next.js)
- `services/cts/eval/runner.py` — runner that executes queries against both the donor and a fresh AIOS CTS
- `bin/cts-eval.py` — CLI entry point
- Baseline numbers: token usage, tool calls, recall, precision, F1 per language per query type

**Risks:** donor repo may behave differently on AIOS's actual repos vs. its own test cases
**Dependencies:** none; this is pure measurement
**Exit criteria:** baseline numbers recorded; at least one TS/Next.js repo shows F1 < 0.60, confirming the gaps documented in the donor's README are real in AIOS's context

---

### Phase 1 — Minimal code topology backend
**Goal:** AIOS CTS indexes one Python and one TypeScript repo with confidence-annotated output

**Deliverables:**
- `services/cts/graph_store.py` — AIOS-native schema with confidence/provenance fields (v1 migration)
- `services/cts/migrations.py` — migration chain starting from v1
- `services/cts/parser.py` — forked from donor, extended for TS gaps
- `services/cts/tsconfig_resolver.py` — forked and extended
- `services/cts/confidence.py` — confidence defaults, trust level classification
- `bin/cts-build.py` — full index build CLI
- `bin/cts-status.py` — index health report

**Files NOT created:** mcp_server.py (deferred to Phase 2), backends/ (deferred), flows/communities (deferred)

**Risks:** TS import resolution gaps may produce lower coverage than expected; acceptable at this stage
**Dependencies:** Python 3.10+, tree-sitter, sqlite3
**Exit criteria:** AIOS repo and one TypeScript project indexed with node counts, edge counts, coverage_pct, and confidence distribution logged; no exceptions on a full build

---

### Phase 2 — Incremental indexing and repo registry
**Goal:** CTS stays current with file changes without manual rebuilds

**Deliverables:**
- `services/cts/incremental.py` — forked, using aios.db.projects instead of JSON registry
- `services/cts/registry.py` — LRU connection pool, reads from aios.db
- `bin/cts-update.py` — incremental update CLI
- `bin/cts-watch.py` — file watcher daemon
- Staleness tracking: `is_stale` flag propagated to dependent nodes after any file change

**Risks:** watchdog dependency; macOS FSEvents integration may miss rapid file saves
**Dependencies:** Phase 1 complete; watchdog package
**Exit criteria:** file save triggers re-index of changed file + dependents within 2 seconds; staleness flags correct; aios.db.projects is the sole source of repo registration

---

### Phase 3 — Agent query APIs and context planner
**Goal:** agents can query CTS through a formal MCP surface

**Deliverables:**
- `services/cts/mcp_server.py` — FastMCP server with Priority 1 tools
- `services/cts/backends/graph_backend.py` — wraps graph_store.py
- `services/cts/backends/fts_backend.py` — wraps search.py FTS5
- `services/cts/backends/file_backend.py` — direct file exploration fallback
- `services/cts/search.py` — forked hybrid search with RRF
- `services/cts/impact.py` — blast-radius + risk scoring (forked from changes.py)
- Updated `hook-session-start.py` — calls `get_minimal_context()` if CTS available for the repo

**MCP tools in scope:** `get_minimal_context`, `get_impact_radius`, `semantic_search_nodes`, `query_graph`, `get_architecture_overview`, `detect_changes`

**Risks:** MCP server process lifecycle management; session hook dependency on CTS availability
**Dependencies:** Phase 2 complete; FastMCP
**Exit criteria:** all 6 Priority 1 MCP tools pass integration tests; `get_minimal_context` returns a bundle ≤300 tokens; hook-session-start uses CTS when available and degrades gracefully when not

---

### Phase 4 — Confidence gating and fallback explorer
**Goal:** agents never receive untrusted graph output without a warning; low-confidence queries route to verified fallbacks

**Deliverables:**
- Full backend routing logic in `services/cts/mcp_server.py` (or `router.py`)
- `FallbackTrigger` and `CTSQueryResult` envelope implemented in all 6 MVP tools
- `has_low_confidence_results` and `has_stale_results` surfaced in every response
- `file_backend.py` completing the fallback chain
- Phase 0 benchmark re-run with new numbers

**Risks:** routing logic complexity; need to verify that fallback triggering is not too aggressive (every query escalating kills the token savings)
**Dependencies:** Phase 3 complete; benchmark harness from Phase 0
**Exit criteria:** benchmark shows <10% wrong-confidence rate; fallback frequency < 20% on current indexes; Phase 0 baseline comparison shows improvement in F1 and token usage

---

### Phase 5 — Observability, admin tooling, and visualization
**Goal:** CTS is operationally visible; AIOS UI can display index health

**Deliverables:**
- `services/cts/communities.py` — Leiden community detection (from donor)
- `bin/cts-eval.py` — full benchmark suite CLI
- AIOS UI route `/projects/[id]` CTS health card (index status, coverage, confidence distribution)
- `vault-lint.py` extension: check for stale CTS indexes

**Risks:** igraph dependency weight; Leiden algorithm on large repos may be slow
**Dependencies:** Phase 4 complete; igraph
**Exit criteria:** communities detected for any indexed repo with >100 nodes; UI card shows live index status

---

### Phase 6 — Semantic enrichment and language server integration
**Goal:** TypeScript/Next.js call graph gaps are closed via LSP verification

**Deliverables:**
- `services/cts/backends/lsp_backend.py` — TypeScript Language Server adapter via LSP protocol
- `services/cts/adapters/lsp_client.py` — JSON-RPC LSP client
- `services/cts/adapters/embeddings.py` — provider adapter from donor
- `services/cts/backends/embedding_backend.py`
- Re-run Phase 0 benchmark: expect TS/Next.js F1 to reach >= 0.75

**Risks:** LSP process lifecycle is complex; tsserver startup time per repo may be 2–5 seconds; embeddings cost
**Dependencies:** Phase 5 complete; tsserver or pyright available in PATH
**Exit criteria:** TS repos show >80% call edge resolution rate; Phase 0 benchmark TS F1 >= 0.75; LSP backend is optional (graceful degradation when unavailable)

---

## Section 6 — Benchmarking and Evaluation

### Why AIOS needs its own benchmarks

The donor's benchmarks test the donor's use case: code review context for PR review. AIOS's use cases are different: blast-radius for planning, node search for onboarding, bug localization, refactor impact, architecture orientation. The donor's F1 = 0.54 average hides per-use-case variance that matters for AIOS.

### Benchmark suite design

Each benchmark case is a tuple: `(repo, query, ground_truth, task_type)`.

**Ground truth** must be established by direct human inspection of each repo, not inferred from graph output. This is the most expensive part of building the benchmark suite and must not be shortcut.

#### Repo corpus

| Repo | Language profile | Size | Why included |
|---|---|---|---|
| AIOS itself | Python, shell | Small | Always available; known structure |
| `aios-ui` | TypeScript, Next.js | Medium | Primary TS/Next.js target |
| A public Next.js app (e.g., cal.com/cal.com) | TS, Next.js, monorepo | Large | Stresses monorepo + alias resolution |
| A public Python FastAPI project | Python | Medium | Tests Python flow detection |
| A public Go project | Go | Medium | Non-TS/Python baseline |
| A refactor-heavy git history | Any | Medium | Tests staleness + incremental accuracy |

#### Query types and measurement

| Query type | Metric primary | Metric secondary | Red-line threshold |
|---|---|---|---|
| Blast-radius (file → impacted files) | Recall | F1 | Recall < 0.70 blocks rollout |
| Node search (name → node) | Precision@10 | F1 | F1 < 0.60 blocks rollout |
| Bug localization ("where is X bug") | Task success | Tool calls | Success < 0.50 blocks rollout |
| Architecture summary | Human rating 1–5 | Token usage | Mean rating < 3.0 blocks rollout |
| Onboarding discovery | Token usage | Recall | Token usage > 2000 blocks rollout |
| Refactor impact (function rename) | Precision (affected set) | False positive rate | False positive > 0.15 blocks rollout |
| Wrong-confidence rate | Wrong-confidence rate | — | > 10% blocks rollout |
| Fallback frequency | Fallback rate | — | > 30% blocks rollout |
| Stale-index failure | Failure rate after branch switch | — | > 5% blocks rollout |

#### Metrics definitions

| Metric | Definition |
|---|---|
| Token usage | Total tokens consumed in context (graph output + any fallback file reads) |
| Tool calls | Number of MCP tool invocations per task |
| Latency | Time from query submission to result delivery (ms) |
| Recall | fraction of true positive items returned / total true positives |
| Precision | fraction of returned items that are true positives |
| F1 | harmonic mean of precision and recall |
| Task success | binary: did the agent complete the task using graph context alone (no raw file reads for graph-covered content) |
| Wrong-confidence rate | fraction of cases where CTS returned high-confidence output that was factually wrong |
| Fallback frequency | fraction of queries that triggered any fallback backend |
| Stale-index failure rate | fraction of post-branch-switch queries where stale index caused incorrect results |

### Red-line thresholds (blocks rollout)

These are hard gates. If any threshold is violated at end of Phase 4, deployment is blocked until it is fixed.

| Threshold | Value |
|---|---|
| Blast-radius recall (TypeScript) | < 0.70 |
| Node search F1 (TypeScript) | < 0.60 |
| Wrong-confidence rate (any language) | > 10% |
| Stale-index failure rate | > 5% |
| Fallback frequency (current index) | > 30% |
| Token usage for minimal_context | > 800 tokens |
| Architecture summary human rating | < 3.0 / 5.0 |

---

## Section 7 — Risks and Non-Goals

### Major risks

**False confidence from structural graphs**
The donor's own numbers show F1 = 0.54 for impact analysis. For TypeScript dynamic patterns, precision drops further. The risk is not that the graph is wrong — it is that the graph is confidently wrong, and an agent acts on a blast-radius result that missed half the affected files. Mitigation: the confidence model (Section 3), the trust level classification, and mandatory warnings in all query results. The confidence gating in Phase 4 is the primary mitigation.

**Stale indexes after branch switches**
A developer switches from `main` to a feature branch. The graph still reflects `main`. If `cts-watch` is not running, the index silently serves stale data. Mitigation: `is_stale` propagation, `index_status = needs_update` in metadata, and hook-session-start checking index freshness before injecting graph context.

**Weak JS/TS call graph precision**
TypeScript's dynamic patterns (higher-order functions, runtime method additions, re-exports, module augmentation) are systematically underrepresented in Tree-sitter graphs. For a Next.js codebase, this means a material fraction of CALLS edges are missing or unresolved. This is a fundamental limitation of static analysis without type inference. Mitigation: `unresolved_call_count` per node, LSP backend in Phase 6, and explicit caller guidance to verify TS call paths above a complexity threshold.

**Dynamic behavior blind spots**
Static analysis cannot represent: conditional imports, dynamic `require()`, plugin systems, decorator factories, dependency injection containers. All are common in production TypeScript. Mitigation: explicit `extraction_method = tree_sitter` flag; never claim these structures are fully represented.

**Alias and path resolution failures**
TypeScript `@/*` aliases, Next.js module aliases, barrel files (`index.ts`), and `paths` in `tsconfig.json` all require resolution to produce accurate import edges. The donor's `tsconfig_resolver.py` handles the common case but silently fails on edge cases. Mitigation: extended `tsconfig_resolver.py` with diagnostic logging; unresolved imports become unresolved edges with `resolution_method = unresolved`.

**Framework-specific flow failures**
Next.js Server Components, Route Handlers, Server Actions, and middleware have different call semantics than plain TypeScript functions. The donor's flow detection does not understand Next.js conventions. Mitigation: do not use flow detection for Next.js codebases until Phase 6 (LSP integration). V1 flow detection is Python-only.

**Operational complexity of watchers and registries**
Running `cts-watch` as a daemon adds process management complexity. If the watcher crashes, indexes go stale silently. Mitigation: `cts-status.py` reports watcher health; hook-session-start checks `index_age_seconds` before using graph context; the watcher is optional (manual `cts-update.py` is always available).

**Privacy risks from storing repo structure locally**
Graph databases contain qualified names, file paths, and structural facts about all indexed repos. For proprietary codebases, this is sensitive information stored in `~/AIOS/data/cts/`. Mitigation: graph.db files are local-only, never synced; add `.gitignore` entries; STORES.md documents this as a local-only store. No cloud dependency (consistent with donor's design).

**Index size for large repos**
A large monorepo (cal.com, 300k LOC) may produce a graph.db of several hundred MB. The LRU connection pool with 10-connection limit is appropriate, but disk usage should be monitored. Mitigation: `cts-status.py` reports index size; nodes for node_modules and generated files are excluded by default.

### Explicit non-goals for V1

- **No source file modification** — CTS never writes to project source files
- **No cross-machine sync** — graph.db is local only
- **No real-time collaboration** — CTS is single-user
- **No TypeScript flow detection** — deferred to Phase 6 (LSP)
- **No community detection** — deferred to Phase 5
- **No refactoring operations** — `apply_refactor_tool` is not in V1
- **No wiki/visualization generation** — deferred
- **No semantic embeddings** — optional, not required for V1
- **No language server integration** — deferred to Phase 6
- **No cross-repo search** — deferred to Phase 4
- **No agent autonomy** — CTS is a read-only map; it does not make decisions

---

## Section 8 — Final Recommendation

### Should AIOS vendor this repo?

**No.** Vendoring means importing the upstream code as-is with minimal modification. The donor's architecture has a fundamental gap (no confidence or provenance model) that makes vendoring worse than reimplementing the relevant parts. A vendored version would need constant patches that diverge from upstream.

### Should AIOS fork it?

**Partially.** Five modules (`graph_store.py`, `incremental.py`, `search.py`, `impact.py`, `registry.py`) are worth forking and modifying. They represent real engineering value that would take weeks to rebuild from scratch. The other modules are either too tightly coupled to the donor's standalone architecture, inadequate for AIOS's requirements, or out of V1 scope.

### Should AIOS reimplement the useful parts?

**Yes, for the MCP layer, confidence model, and flows detection.** These are either too tightly coupled to reuse directly (`mcp_server.py`), fundamentally absent from the donor (`confidence.py`), or wrong for AIOS's primary use case (`flows.py`). The effort to reimplement them is lower than the effort to adapt the donor's versions.

### Should AIOS wrap it behind an adapter first?

**No.** The adapter-first approach (`CTSBackend` wrapping the donor's Python API) sounds conservative but is a false economy. The donor lacks confidence fields at the data layer, which means any adapter would be producing schema-level lies (fabricating confidence values for a system that has none). The adapter approach only makes sense when the underlying system's data model is compatible. This one is not.

### Which parts deserve immediate implementation (Phase 0–2)?

1. `services/cts/graph_store.py` — AIOS-native schema with confidence fields (fork + modify graph.py)
2. `services/cts/migrations.py` — AIOS CTS migration chain (new, inspired by donor pattern)
3. `services/cts/parser.py` — multi-language AST extraction (fork + modify)
4. `services/cts/tsconfig_resolver.py` — TS path alias resolution (fork + extend)
5. `services/cts/confidence.py` — confidence model (new; the most critical AIOS addition)
6. `services/cts/incremental.py` — change detection (fork, minimal modification)
7. `bin/cts-build.py`, `bin/cts-status.py` — indexing CLI
8. `services/cts/eval/` — benchmark harness (fork structure, new content)

### Which parts should be deferred?

- Flow detection (Phase 3/6 — needs LSP for TS)
- Community detection (Phase 5 — igraph dependency, not V1 priority)
- Embeddings (Phase 6 — optional enrichment)
- Wiki and visualization (Phase 5+)
- Cross-repo search (Phase 4)
- Language server adapter (Phase 6)
- `apply_refactor_tool` (indefinitely deferred — too risky)

### The decisive judgment

Build CTS. Start now. The structural primitive is proven — the donor demonstrates that Tree-sitter + SQLite + MCP can produce real token savings (8.2x) with acceptable accuracy (F1 0.54 baseline that AIOS can improve). The confidence model is the critical addition that makes this safe for AIOS. Without it, the system misleads agents. With it, the system becomes a reliable orientation tool that gracefully acknowledges what it does not know.

The V1 boundary is intentionally narrow: indexing, blast-radius, hybrid search, confidence gating, and fallback to direct file exploration. This is enough to deliver measurable value (fewer blind file reads, faster orientation, correct blast-radius for planning tasks) without over-trusting a system that will have real gaps, especially in TypeScript.

Phase 6 (LSP integration) is where CTS becomes genuinely high-confidence for TypeScript codebases. That is the long-term objective. V1 is the path that gets there without betting on unproven precision.

---

## Appendix A — Proposed AIOS Folder/Service Structure

```
~/AIOS/
├── services/
│   └── cts/
│       ├── __init__.py
│       ├── confidence.py           ← NEW: trust levels, confidence defaults, staleness
│       ├── graph_store.py          ← FORKED from graph.py + heavily modified
│       ├── migrations.py           ← NEW: v1+ migration chain (AIOS schema)
│       ├── parser.py               ← FORKED from parser.py + modified
│       ├── tsconfig_resolver.py    ← FORKED from tsconfig_resolver.py + extended
│       ├── incremental.py          ← FORKED from incremental.py + minor mod
│       ├── search.py               ← FORKED from search.py + RRF fix
│       ├── impact.py               ← FORKED from changes.py + confidence annotations
│       ├── registry.py             ← FORKED from registry.py + aios.db integration
│       ├── indexer.py              ← NEW: orchestrates full + incremental builds
│       ├── mcp_server.py           ← NEW: FastMCP, reimplemented (not ported)
│       ├── backends/
│       │   ├── base.py             ← NEW: Backend protocol
│       │   ├── graph_backend.py    ← NEW: wraps graph_store.py
│       │   ├── fts_backend.py      ← NEW: wraps FTS5 in graph.db
│       │   ├── file_backend.py     ← NEW: direct file exploration fallback
│       │   ├── embedding_backend.py← PHASE 6: optional
│       │   └── lsp_backend.py      ← PHASE 6: optional
│       ├── adapters/
│       │   ├── embeddings.py       ← PHASE 6: forked from donor
│       │   └── lsp_client.py       ← PHASE 6: new
│       └── eval/
│           ├── runner.py           ← FORKED structure, new content
│           ├── scorer.py           ← FORKED structure, new content
│           ├── token_benchmark.py  ← FORKED
│           └── cases/
│               ├── typescript_impact.py
│               ├── nextjs_search.py
│               ├── python_blast_radius.py
│               ├── monorepo_navigation.py
│               └── bug_localization.py
├── bin/
│   ├── cts-build.py               ← NEW
│   ├── cts-update.py              ← NEW
│   ├── cts-watch.py               ← NEW
│   ├── cts-status.py              ← NEW
│   └── cts-eval.py                ← NEW
└── data/
    └── cts/
        └── <repo_hash>/
            ├── graph.db
            └── embeddings.db       ← Phase 6, optional
```

---

## Appendix B — Prioritized Task List

### Must-have (V1 blocker)
1. Define AIOS CTS SQL schema (nodes + edges + confidence fields) — `graph_store.py` v1
2. Write migration chain v1 — `migrations.py`
3. Fork and extend `parser.py` for AIOS; add `unresolved_call_count` per file
4. Fork and extend `tsconfig_resolver.py` with extends chain and diagnostics
5. Implement `confidence.py` — trust levels, defaults by extraction method, staleness
6. Fork `incremental.py` — replace JSON registry with `aios.db.projects`
7. Fork `registry.py` — LRU pool reading from `aios.db.projects`
8. Write `indexer.py` — full and incremental build orchestration
9. Write `bin/cts-build.py` and `bin/cts-status.py`
10. Fork `search.py` — RRF fix, upstream kind-filter, confidence metadata
11. Fork `impact.py` — confidence annotations, stale flag, unindexed file list
12. Write `backends/graph_backend.py`, `fts_backend.py`, `file_backend.py`
13. Write `mcp_server.py` with 6 Priority 1 tools
14. Build benchmark cases for TypeScript and Python (Phase 0 prerequisite)
15. Run Phase 4 confidence gating; verify wrong-confidence rate < 10%

### Should-have (Phase 3–4)
16. Integrate CTS check into `hook-session-start.py`
17. `bin/cts-update.py` and `bin/cts-watch.py`
18. Full benchmark suite run with red-line checks
19. AIOS UI integration point for CTS health card

### Nice-to-have (Phase 5–6)
20. `communities.py` from donor (Leiden)
21. `lsp_backend.py` — TypeScript Language Server adapter
22. `embedding_backend.py` — optional semantic enrichment
23. Cross-repo search (multi-repo query)
24. Visualization (D3.js or AIOS UI graph view)
25. Wiki generation

---

## Appendix C — Architecture Decision Record (ADR-001)

**Title:** Code Topology Service architecture and donor integration strategy

**Status:** Proposed

**Context:**
AIOS agents repeatedly re-discover code structure through brute-force file reads. `tirth8205/code-review-graph` demonstrates that a persistent structural graph can reduce token usage 8.2x, but its schema lacks confidence and provenance fields, its TypeScript call graph has documented gaps, and its architecture is designed as a standalone tool rather than an AIOS subsystem.

**Decision:**
AIOS will build a Code Topology Service (CTS) by:
1. Forking five modules from the donor (`graph.py`, `incremental.py`, `search.py`, `changes.py`, `registry.py`) and modifying them to add confidence and provenance fields
2. Reimplementing the MCP layer and flow detection from scratch
3. Building a pluggable backend model so the donor's structural graph is one backend among several, not the only source
4. Storing per-repo graph databases under `~/AIOS/data/cts/<repo_hash>/graph.db`
5. Reading repo registration from `aios.db.projects`, not a separate JSON registry

**Alternatives considered:**
- **Vendor as-is:** rejected — schema incompatibility with AIOS confidence model; no provenance tracking
- **Adapter wrapper:** rejected — confidence fields cannot be fabricated at the adapter layer; requires correct data model at the storage layer
- **Full reimplement from scratch:** rejected — five modules have real engineering value; forking saves weeks
- **Defer indefinitely:** rejected — token waste from repeated file reads is a real cost; this is a high-value infrastructure investment

**Consequences:**
- AIOS owns and maintains a fork of five donor modules; upstream changes require manual merge
- CTS adds a new service process (`mcp_server.py`) to the AIOS process model
- Data directory `~/AIOS/data/cts/` is added; STORES.md must be updated
- `hook-session-start.py` gains a CTS availability check
- Phase 6 (LSP integration) is required to reach high-confidence TS/Next.js accuracy

---

## Appendix D — V1 Acceptance Criteria

All criteria must pass before CTS is considered production-ready for AIOS use:

1. **Indexing:** `cts-build.py` successfully indexes the AIOS repo and `aios-ui/` without exceptions; `coverage_pct >= 0.85` for both
2. **Incrementality:** saving a single file triggers re-index within 2 seconds when `cts-watch` is running; `is_stale` propagates to dependent nodes
3. **Schema:** every node and edge in `graph.db` has non-null `confidence`, `extraction_method`, `last_verified_at` (or explicit null with reason)
4. **Confidence gating:** `CTSQueryResult.warnings` includes a stale or low-confidence warning when any result node has `is_stale = true` or `confidence < 0.6`; no high-confidence result is returned for a stale node
5. **Blast-radius recall:** benchmark shows recall >= 0.70 for Python repos; >= 0.60 for TypeScript repos (lower TS threshold acknowledged until Phase 6)
6. **Wrong-confidence rate:** < 10% across all benchmark cases
7. **Fallback rate:** < 30% of queries trigger a fallback backend on current (non-stale) indexes
8. **Token budget:** `get_minimal_context()` returns <= 800 tokens
9. **Session integration:** `hook-session-start.py` uses CTS when index is current; degrades gracefully when CTS is unavailable or index is stale
10. **Registry:** no second JSON registry file exists; all repo registration reads from `aios.db.projects`
11. **STORES.md updated:** `~/AIOS/data/cts/` documented as a new local-only store
12. **Benchmark harness:** `cts-eval.py` runs without errors; produces a report with all red-line metrics

---

## Appendix E — Build Order for Engineers

This is the sequence a single engineer should follow. Each step has a clear output and does not require the next step to compile.

1. **Schema first.** Write `graph_store.py` with the AIOS-native schema. Write `migrations.py` v1. Verify with `sqlite3` directly — no other code needed.
2. **Confidence model.** Write `confidence.py`. Unit-test the defaults, trust level classification, and staleness scoring in isolation.
3. **Parser.** Fork `parser.py`. Add `unresolved_call_count`. Write one fixture test per language (Python, TypeScript). Fix TS alias resolution in `tsconfig_resolver.py`.
4. **Indexer.** Write `indexer.py` and `bin/cts-build.py`. Index the AIOS repo itself. Verify node counts, edge counts, coverage_pct in `cts-status.py`.
5. **Benchmarks (Phase 0).** Write 5 benchmark cases before touching any query layer. Establish baseline. This is non-negotiable — you need a number to improve against.
6. **Incremental + registry.** Fork `incremental.py` and `registry.py`. Wire to aios.db. Write `bin/cts-watch.py`.
7. **Search.** Fork `search.py` with RRF fixes. Wire to FTS5 in graph.db.
8. **Impact analysis.** Fork `changes.py` as `impact.py`. Add confidence annotations. Test blast-radius on a known change in the AIOS repo.
9. **Backends.** Write `graph_backend.py`, `fts_backend.py`, `file_backend.py`. Write the router.
10. **MCP server.** Write `mcp_server.py` with 6 Priority 1 tools. Test end-to-end against Claude Code.
11. **Hook integration.** Update `hook-session-start.py`. Test with and without CTS running — verify graceful degradation.
12. **Phase 4 confidence gating.** Verify wrong-confidence rate and fallback frequency against red-line thresholds.
13. **STORES.md update.** Document `~/AIOS/data/cts/` as a new store.
14. **Acceptance criteria pass.** Run all 12 V1 acceptance criteria. Ship.
