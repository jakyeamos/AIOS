# NotebookLM MCP Second-Brain Add-On Audit

Date: 2026-06-13

## Current Second-Brain Architecture

AIOS already has layered local memory rather than one generic retrieval system:

- Obsidian/vault state is represented by project inventory fields, vault root helpers, context packets, and future graph-routing policy.
- SQLite is the local operational store for sessions, tool events, prompts, orchestration runs, receipts, learning events, writebacks, and promotion lifecycle records.
- TMCP is implemented as a compiled skills/context graph under `skills-library/skills.tmcp/`, with traversal receipts in `services/tmcp_runtime.py`.
- Context compiler receipts live under `aios/context/compiled/` and `aios/context/receipts/`.
- Promotion/writeback governance exists in `services/workflow_promotion.py`, `services/divergent_strategy.py`, and lifecycle tables.
- Operator search spans run, packet, writeback, route, learning, and promotion objects in `services/operator_search.py`.

## Existing Memory Layers

Obsidian remains the durable human-readable second brain. SQLite remains the operational memory layer and must keep raw logs, traces, and telemetry local. TMCP remains the agent-facing compiled skill/context layer. AIOS context packets are the governed briefing layer.

## Existing Routing Behavior

Routing currently favors local deterministic sources: context compiler packet selection, workflow registry selection, project inventory resolution, operator search, and TMCP traversal. The Obsidian graph routing packet says vault search should begin from MOC/routing nodes and produce receipts rather than broad unbounded search.

## Where NotebookLM MCP Fits

NotebookLM MCP fits after AIOS has selected a bounded source bundle. It is a synthesis backend for selected documents, not a source of truth. It can help with:

- Bounded source synthesis
- Cross-note connection discovery
- TMCP module candidate discovery
- Learning opportunity detection
- Contradiction and drift reports
- Project resurfacing
- Briefings and digests

## Where NotebookLM MCP Should Not Fit

NotebookLM should not handle repo/code search, command execution, raw session recovery, unbounded vault organization, source-of-truth lookups, private operational logs, secrets, credentials, or automatic note promotion.

## Current Gaps

AIOS had local retrieval and promotion primitives, but no explicit route for higher-order synthesis over curated source bundles. It also lacked an executable policy for learning opportunity detection, cross-note relationship synthesis, TMCP module discovery, and drift detection as second-pass synthesis tasks.

## Risks

- Dumping too much private context into a cloud-backed synthesis appliance.
- Treating NotebookLM output as canonical memory.
- Skipping local retrieval and losing source-of-truth ordering.
- Logging raw source contents instead of references and hashes.
- Promoting uncertain synthesis into Obsidian/TMCP without review.
- Making AIOS boot depend on external MCP availability.

## Minimal Implementation Path

The smallest safe integration is:

1. Add a deterministic route classifier and source-bundle metadata builder.
2. Add an optional NotebookLM MCP adapter boundary that fails safely when unavailable.
3. Add the `jacob-bd/notebooklm-mcp-cli` backend as an experimental contract, not an official Google API.
4. Add provenance and staging templates.
5. Add human/agent routing policy documentation.
6. Validate the required routing scenarios and backend contract in tests.

## Files Modified Or Added

- `services/notebooklm_synthesis.py`
- `tests/test_notebooklm_synthesis.py`
- `aios/policies/notebooklm-routing.md`
- `docs/architecture/notebooklm-mcp-addon.md`
- `docs/audits/2026-06-13-notebooklm-mcp-second-brain-addon-audit.md`
- `aios/context/packets/knowledge.notebooklm-routing.md`
- `aios/context/domains/knowledge-systems.md`
- `config/agent-rules.md`
- `config/notebooklm/backends.json`
- `docs/contracts/notebooklm-mcp-cli-contract.md`
- `.planning/quick/260612-wyv-audit-and-implement-notebooklm-mcp-optio/SUMMARY.md`

## Missing Abstractions

AIOS now has an experimental backend contract for `jacob-bd/notebooklm-mcp-cli`. Live MCP invocation is still intentionally not implemented because it requires operator-approved install/auth, MCP tool probing, and a reviewed decision to send a bounded source bundle to a third-party/internal-API backend.
