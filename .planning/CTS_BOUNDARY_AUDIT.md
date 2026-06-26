# CTS Boundary Audit

Date: 2026-06-26
Branch: `codex/cts-boundary-audit`

## Verdict

Keep CTS inside AIOS as a core sidecar / incubator candidate. Do not split it into a standalone repo yet.

CTS is useful enough to preserve and harden, but its current ownership is still AIOS-local: repo discovery reads the AIOS `projects` table, graph stores live under `~/AIOS/data/cts`, CLI and MCP entrypoints resolve the current repo through AIOS registration, and operator/context consumers use CTS as part of the AIOS runtime rather than as an independent product.

The right next extraction shape is not a full repo split. It is a future `cts-contract` style package or fixture bundle for node/edge/query result schemas, graph-store migration expectations, benchmark cases, and portable index/search evidence. That package should come after CTS has external fixtures and a stable query envelope.

## Evidence Inspected

- `services/cts/models.py` defines portable-looking dataclasses and enums for nodes, edges, confidence summaries, query results, minimal context bundles, blast radius, and fallback triggers.
- `services/cts/graph_store.py` and `services/cts/migrations.py` implement a real SQLite graph store with repository status, node/edge tables, FTS, migrations, stale marking, replacement, upsert, and query helpers.
- `services/cts/registry.py` is AIOS-coupled through `~/AIOS/data/aios.db`, the root `projects` table, and `~/AIOS/data/cts` graph-store paths.
- `services/cts/indexer.py` requires a repo registered in AIOS before it can build an index.
- `services/cts/mcp_server.py` exposes useful tools, but the service resolves repos through `CTSRegistry`, so the MCP surface is not portable without AIOS registration and data layout.
- `bin/cts-build.py` and `bin/cts-status.py` are thin wrappers over AIOS-owned CTS services rather than standalone product commands.
- `services/cts/search.py` names `semantic_search_nodes`, but current search is FTS/LIKE fusion with `has_embeddings=False`.
- `services/cts/backends/embedding_backend.py` is a scaffold that returns no items and warns that the semantic index is not built.
- `services/cts/flows.py` currently returns empty lists for flow discovery and affected-flow analysis.
- `services/cts/eval/runner.py` and `services/cts/eval/cases/*.json` provide the start of a benchmark harness, but there are no discovered CTS-specific tests under `tests/`.
- `docs/superpowers/specs/2026-04-08-aios-code-topology-service-design.md` explicitly frames CTS as shared AIOS infrastructure backed by AIOS project registration and `data/cts/<repo-id>/graph.db`.
- `docs/audits/graph-native-memory-audit.md` already records the semantic-search scaffold, empty flow layer, and fragmented retrieval contract as known gaps.

## Why Extraction Is Premature

1. Storage ownership is AIOS-local.
   CTS has no portable repository registry contract yet. The default registry depends on the AIOS SQLite database and AIOS project rows.

2. Runtime consumers are AIOS-integrated.
   Session-start context, operator/project UI, and local AIOS command surfaces expect CTS to enrich AIOS work rather than run as a separately installed repo-intelligence product.

3. Query semantics are not stable enough.
   The result envelope is promising, but "semantic" currently means FTS/LIKE fusion, flow queries are placeholders, and confidence/fallback semantics still need stronger fixture-backed proof.

4. Evaluation coverage is incomplete.
   The eval harness exists, but the audit did not find CTS-specific regression tests in `tests/`. Before extraction, CTS needs isolated fixture repos and query benchmarks that prove behavior outside the live AIOS database.

5. The original design intent still matches sidecar ownership.
   The committed CTS design calls it a shared infrastructure service inside AIOS, not a session-scoped script or independent product.

## Keep Inside AIOS

CTS should stay inside AIOS for:

- repository graph indexing tied to AIOS project inventory
- local graph-store lifecycle under `~/AIOS/data/cts`
- session-start/context enrichment
- operator UI and project-detail intelligence
- AIOS-specific MCP/CLI wrappers
- experimental search, impact, and confidence semantics

## Future Extraction Candidate

The first portable artifact should be a contract/fixture package, not a full CTS runtime. Candidate contents:

- node, edge, confidence, query-result, blast-radius, and fallback schemas
- graph-store migration contract and sample SQLite fixtures
- portable index fixture repo
- semantic/FTS query benchmark cases
- impact-radius benchmark cases
- stale/low-confidence/fallback expected-output fixtures
- CLI/MCP request-response schema examples

That contract becomes package-ready only after non-AIOS tests consume it and AIOS validates live CTS outputs against it.

## Required Before Reconsidering A Repo Split

- Introduce a repository-registry adapter so CTS can run without the AIOS `projects` table.
- Make graph-store root configurable without `~/AIOS` defaults leaking into portable commands.
- Rename or implement semantic search so the command name matches the evidence.
- Implement the flow layer or remove it from product claims.
- Add CTS-specific tests under `tests/` for registry, graph store, search, impact, MCP envelope, and eval runner behavior.
- Add isolated fixture repos and query benchmarks that run without the live AIOS database.
- Define an explicit query-result contract with stale, low-confidence, fallback, coverage, and index-age semantics.
- Decide whether CTS is a `core_aios_sidecar`, `contract_package`, or `standalone_tool` after those fixtures are green.

## Decision

CTS remains an AIOS-owned sidecar. The subsystem extraction plan should treat it as an incubator candidate leaning `core_aios_sidecar`, with the next decision point focused on portable contract fixtures rather than physical repository extraction.
