# AIOS 2026 Stack Research

Date: 2026-05-13
Scope: recommended standard stack for a local-first, knowledge-aware AI orchestration system / agent operating system shaped like AIOS.

## Executive Position

AIOS should stay a split-runtime system:

- Python control plane for orchestration, hooks, evaluation, writebacks, and durable run state.
- Next.js operator UI for inspection, intervention, and thin local API surfaces.
- SQLite plus files as the default persistence spine.

That is still the right product shape in 2026.

The strongest default stack is boring, local, inspectable, and auditable:

- Python `3.13` for the control plane.
- `uv` for Python runtime and dependency management.
- `FastAPI` plus `Pydantic v2` for any explicit local HTTP surfaces.
- direct SQLite access, not an ORM-heavy core.
- Next.js `16.x` App Router plus React `19.2` for the UI.
- TypeScript strict mode.
- OpenTelemetry for cross-runtime tracing.
- SQLite `WAL` + `STRICT` tables + `JSON` functions + `FTS5` as the retrieval baseline.

## Prescriptive Recommendations

| Area | Recommendation | Rationale | Confidence |
|---|---|---|---|
| Control plane runtime | Standardize on Python `3.13` now; defer `3.14` adoption until repo tooling and wheels are uniformly stable | Python 3.13 is stable and modern without taking unnecessary upgrade risk in the orchestration core | High |
| Python package/runtime manager | Use `uv` as the only Python environment/package tool | It already fits AIOS and is now the most pragmatic standard for fast, repeatable local Python workflows | High |
| Control plane API surface | Use `FastAPI` only for explicit local service boundaries; keep most orchestration code as plain Python modules and CLIs | AIOS is not primarily an HTTP product. Local orchestration should stay callable without network indirection | High |
| Validation and schemas | Use `Pydantic v2` for run inputs, tool contracts, evaluation payloads, and writeback proposals | Strong typing and fast validation matter for agent-facing boundaries and audit artifacts | High |
| Primary datastore | Keep SQLite as the default operational store | It matches local-first, single-operator, inspectable workflows better than adding service dependencies | High |
| SQLite mode | Default new operational DBs to `WAL`; use `STRICT` tables for authoritative runtime state | Better concurrency and better type discipline with low operational overhead | High |
| Retrieval baseline | Use file authority + SQLite metadata + `FTS5` first; add vectors only where recall demonstrably benefits | AIOS truth is file-backed and auditable. Lexical and structural retrieval should remain first-class | High |
| Vector search | Treat vector search as optional and local. Prefer `sqlite-vec` only behind an internal abstraction and not as the sole retrieval path | It fits local-first well, but it is still pre-v1 and should not become schema-critical | Medium |
| UI runtime | Standardize on Next.js `16.x` App Router with React `19.2` | This is the current stable React/Next path and matches the existing UI | High |
| UI data boundary | Prefer Server Components, Route Handlers, and server-side reads. Keep client components thin | AIOS is an operator console, not a client-heavy SaaS dashboard | High |
| Cross-runtime observability | Adopt OpenTelemetry traces/metrics across Python and Node, then persist AIOS-specific audit facts separately in SQLite/files | OTel solves correlation; AIOS should still own domain audits and evidence | High |
| Model access | Prefer direct model SDK/API usage from the Python control plane. Use higher-level agent SDKs only where they reduce code without owning system truth | AIOS already has orchestration concepts and should not outsource its core loop | High |
| Local model path | Support Ollama for local embeddings and optional local models; treat remote frontier models as pluggable, not mandatory | This preserves local-first identity while allowing quality-sensitive remote execution | Medium |
| Job execution | Use Python `asyncio` / `TaskGroup`, subprocesses, and SQLite-backed run state instead of distributed queue infrastructure | AIOS is a local orchestration OS, not a horizontally scaled event platform | High |

## Recommended Default Stack

### 1. Control Plane

- Python `3.13`
- `uv`
- `Pydantic v2`
- `FastAPI` for explicit local APIs only
- stdlib `sqlite3` or a very thin query layer for the core runtime
- `httpx` for outbound HTTP if needed
- `asyncio` and `TaskGroup` for concurrent orchestration
- `OpenTelemetry` SDK for traces/metrics

Why this stack:

- It keeps the orchestration core importable, scriptable, and easy to run from hooks.
- It avoids hiding AIOS state transitions behind framework magic.
- It fits the brownfield reality: Python already owns the control plane.

### 2. Operator UI

- Next.js `16.x`
- React `19.2`
- TypeScript strict mode
- App Router
- Server Components by default
- Route Handlers for local UI-owned endpoints
- Client components only for interaction-heavy panels

Why this stack:

- Next.js 16 is already the repo direction.
- React 19.2 improves modern concurrent UI patterns without forcing a UI rewrite.
- Server-first rendering matches AIOS better than a thick SPA because most operator views are read-heavy.

### 3. Persistence and Knowledge

- authoritative truth in files
- operational state in SQLite
- `WAL` mode
- `STRICT` tables for runtime-critical tables
- SQLite JSON functions for structured payload storage
- `FTS5` for lexical search over notes, packets, audits, and receipts
- content-addressed or stable-path file storage for artifacts

Why this stack:

- AIOS needs inspectability more than abstract data portability.
- SQLite plus files keeps debugging simple and supports local backups, diffs, and repair.
- `FTS5` handles a large share of knowledge retrieval without introducing external services.

### 4. Retrieval Strategy

Default retrieval order should be:

1. explicit file/path references
2. context compiler packet selection
3. structured SQLite filters
4. `FTS5` search
5. optional embedding/vector rerank

Prescriptive rule:

- Do not let embeddings replace authoritative packet selection.
- Do not let semantic search become the default answer for governed project truth.

This is especially important for AIOS because standards, packets, and truth files are policy surfaces, not just fuzzy knowledge blobs.

### 5. Model and Agent Runtime

Recommended default:

- keep the AIOS control loop owned by AIOS
- call model APIs directly from Python for core orchestration
- use structured outputs, tool/function calling, and explicit run records
- add an agent SDK only where it clearly removes boilerplate without taking over run state or routing logic

Practical recommendation for AIOS:

- Use direct OpenAI `Responses` API style integrations for core orchestration.
- If a higher-level runtime is useful, constrain it to leaf workflows, experiments, or tool bundles.
- Do not make an external agent framework the system spine.

### 6. Local Model / Embedding Support

Recommended local-first path:

- Ollama for optional local embeddings and optional local model execution
- remote models for quality-critical planning/reasoning paths

Prescriptive rule:

- local capability is a product strength
- local-only purity is not worth degrading operator value on high-stakes tasks

So the right stance is hybrid by design, local by default where quality holds.

## What To Keep, What To Change

### Keep

- Python as the control-plane owner
- Next.js as the operator UI
- SQLite and file-backed truth
- local hooks and CLI entrypoints
- explicit evaluation and audit surfaces

### Change or tighten

- Make Python `3.13` the explicit standard target rather than a loose `>=3.12` posture
- Use `Pydantic` systematically at agent/tool boundaries if that is not already consistent
- Normalize SQLite `STRICT` + `WAL` usage for runtime-critical stores
- Make `FTS5` the explicit baseline retrieval engine if not already formalized everywhere
- Treat vector retrieval as an optional augmentation, not the center of knowledge access
- Converge on one observability story with OpenTelemetry plus AIOS-native audit tables

## What Not To Use As The Default

### 1. Do not move the core runtime to a distributed cloud stack

Avoid making the default architecture:

- Postgres
- Redis
- Kafka
- Temporal
- hosted vector DBs

Why:

- That stack is right for team-scale, multi-machine, always-on orchestration.
- It is wrong for AIOS’s current product identity: local-first, inspectable, single-operator, file-aware execution.

Confidence: High

### 2. Do not make a heavyweight agent framework the system spine

Avoid making frameworks like LangGraph-style runtimes, multi-agent abstractions, or CrewAI-style orchestration the primary source of truth for:

- routing
- run state
- approvals
- writebacks
- evaluation evidence

Why:

- AIOS already has those concepts.
- A framework-owned runtime would create split authority and reduce inspectability.

Use them, if at all, as bounded implementation helpers, not the operating system.

Confidence: High

### 3. Do not introduce an ORM-heavy core around SQLite

Avoid making the runtime depend on a large ORM abstraction for the central control plane.

Why:

- SQLite is already easy to inspect directly.
- AIOS benefits more from obvious SQL and stable schemas than from generalized ORM indirection.
- Cross-runtime SQLite access is easier to reason about when schema and queries are explicit.

Confidence: High

### 4. Do not make vector search the authoritative retrieval path

Avoid designs where:

- every lookup requires embeddings
- standards/truth files are retrieved primarily through semantic similarity
- lexical and path-based retrieval are treated as legacy fallback

Why:

- AIOS needs provenance and explainability.
- Vector retrieval is useful, but it is not a trustworthy replacement for explicit source selection.

Confidence: High

### 5. Do not deepen tRPC as the long-term cross-runtime contract

For this brownfield repo, tRPC is acceptable inside the Next.js app.
It is not the right long-term contract between the Python control plane and the operator UI.

Prefer:

- Python-owned durable state
- explicit local APIs where needed
- UI reads that map cleanly onto runtime tables, files, and audits

Why:

- tRPC is strongest inside a TypeScript-only boundary.
- AIOS is intentionally split between Python and TypeScript.

Confidence: Medium

### 6. Do not default to Electron or Tauri right now

Avoid wrapping the UI as a desktop shell unless packaging and offline desktop distribution become product requirements.

Why:

- AIOS already runs locally.
- A desktop wrapper adds another runtime surface before the current control-plane/operator split is fully unified.

Confidence: Medium

## Concrete Library Suggestions

### Strong recommendations

- Python: `uv`, `pydantic`, `fastapi`, `httpx`, `opentelemetry-sdk`
- UI: `next`, `react`, `typescript`, `zod`
- Storage: built-in SQLite features first

### Conditional recommendations

- `sqlite-vec` only behind an abstraction and only for optional local vector search
- Ollama for local embeddings and optional local inference
- OpenAI Agents SDK only for bounded workflows where AIOS still owns the outer loop

### Avoid unless requirements change materially

- Redis/Celery stacks
- distributed workflow engines
- external vector DBs as the default local path
- graph databases for core truth storage
- document databases as primary runtime state

## Recommended 12-Month Standard For AIOS

If AIOS were being normalized today, the standard stack should be:

- Control plane: Python `3.13` + `uv` + `Pydantic v2` + thin `FastAPI` surfaces
- UI: Next.js `16.x` + React `19.2` + TypeScript strict
- Persistence: SQLite + files
- Search: file routing + SQLite filters + `FTS5`, with vectors optional
- Observability: OpenTelemetry plus AIOS-native audits
- Model access: direct model APIs from Python, with optional local Ollama support

This is the highest-confidence stack because it matches both the 2026 ecosystem and AIOS’s actual product shape.

## Sources

- Python 3.13 docs: <https://docs.python.org/3.13/>
- Python version index: <https://www.python.org/doc/versions/>
- Node.js release policy: <https://nodejs.org/en/about/previous-releases>
- Next.js 16 release: <https://nextjs.org/blog/next-16>
- Next.js App Router docs: <https://nextjs.org/docs/app>
- Next.js Server and Client Components: <https://nextjs.org/docs/app/getting-started/server-and-client-components>
- Next.js Route Handlers: <https://nextjs.org/docs/app/getting-started/route-handlers>
- React 19.2 release: <https://react.dev/blog/2025/10/01/react-19-2>
- SQLite `STRICT` tables: <https://www.sqlite.org/stricttables.html>
- SQLite `FTS5`: <https://www.sqlite.org/fts5.html>
- SQLite `WAL`: <https://www.sqlite.org/wal.html>
- SQLite JSON functions: <https://www.sqlite.org/json1.html>
- Pydantic why/use cases: <https://docs.pydantic.dev/latest/why/>
- FastAPI features: <https://fastapi.tiangolo.com/features/>
- OpenTelemetry docs: <https://opentelemetry.io/docs/>
- OpenTelemetry Python: <https://opentelemetry.io/docs/languages/python/>
- OpenTelemetry JavaScript: <https://opentelemetry.io/docs/languages/js/>
- uv project docs/repo: <https://github.com/astral-sh/uv>
- OpenAI Responses API: <https://platform.openai.com/docs/api-reference/responses/retrieve>
- OpenAI Agents SDK: <https://openai.github.io/openai-agents-python/>
- Ollama embeddings: <https://docs.ollama.com/capabilities/embeddings>
- sqlite-vec repo: <https://github.com/asg017/sqlite-vec>

## Notes On Confidence

- High: recommendation is strongly supported by current official docs and AIOS’s brownfield constraints.
- Medium: recommendation is directionally strong, but depends on local workload shape or maturity tradeoffs.
- Low: not used here; this research does not support low-confidence stack bets for AIOS’s default path.
