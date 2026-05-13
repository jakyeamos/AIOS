# AIOS Research Summary

Date: 2026-05-13

## Planning Takeaway

AIOS should be built as a local-first agent control plane, not as a chat shell and not as a hosted automation platform. The near-term goal is to tighten deterministic context selection, workflow routing, durable run state, evaluation, and governed writeback into one inspectable operating loop. The product advantage is not more tools; it is stronger context, stronger governance, and better evidence.

## Recommended Stack Direction

- Control plane: Python `3.13`, `uv`, `Pydantic v2`, `asyncio`, and `FastAPI` only for explicit local service boundaries.
- Operator UI: Next.js `16.x`, React `19.2`, strict TypeScript, App Router, and Server Components by default.
- Persistence: files as canonical project/context truth; SQLite as the operational spine with `WAL`, `STRICT` tables, JSON fields/functions, and `FTS5`.
- Retrieval: explicit file/path authority first, then compiled context packets and structured filters, then `FTS5`, with embeddings/vector search only as an optional rerank layer.
- Observability: OpenTelemetry for cross-runtime traces plus AIOS-native audit/evaluation tables for domain truth.
- Model runtime: keep orchestration ownership in AIOS, use direct model APIs for core loops, and treat higher-level agent frameworks as bounded helpers rather than the system spine.

## Table-Stakes Capabilities

These should drive requirements before broader UX or autonomy work:

1. Deterministic task classification and context compilation with loaded/skipped receipts.
2. Workflow routing that chooses the smallest sufficient governed workflow and explains why.
3. Durable run, invocation, artifact, and lifecycle state with explicit linkage and resumability.
4. Truth-file and project-memory maintenance as mandatory completion work, not optional docs follow-up.
5. Standards and success-criteria evaluation tied to concrete evidence and remediation.
6. Governed writeback proposals for truth, prompts, skills, workflows, and packets.
7. Execution-first verification for stateful, cross-system, or core-logic changes.
8. Approval-aware automation for destructive, policy-changing, or high-blast-radius actions.
9. Searchable operator surfaces over runs, truth, criteria, deltas, and pending approvals.

## Differentiators To Sequence Later

After the table stakes are reliable, AIOS should deepen the capabilities that are genuinely distinctive:

- Context compiler as the default entrypoint for non-trivial work.
- Delta-from-expectation scoring across architecture, testing, security, observability, and agent-readiness.
- Governed self-improvement loops that promote reviewed evidence into reusable assets.
- Workflow selection as the main unit of reuse, rather than tool selection.
- Cross-run memory that improves routing and packet selection while preserving provenance and reversibility.
- Operator-visible compounding that shows how each run improved future execution quality.

## Architectural Implications

- Preserve split responsibilities: Python owns orchestration and authoritative writes; the Next.js UI is primarily a read/inspection layer with carefully scoped control actions.
- Keep file-backed context and truth authoritative. SQLite should store operational facts, receipts, audits, and queryable state, not replace source knowledge.
- Separate canonical knowledge, operational evidence, ephemeral staging, and learned proposals pending approval.
- Centralize routing, standards selection, execution strategy, and approval policy in registries and control-plane services rather than scattering them across prompts, scripts, and UI code.
- Treat evaluation as a first-class subsystem that consumes runtime evidence, not final text alone.

## Top Pitfalls To Avoid

- Context overload and packet sprawl that replace deterministic selection with broad semantic trawling.
- Stale truth and weak writeback discipline that let future runs inherit bad assumptions.
- Heuristic lifecycle linkage that creates orphaned or misleading run state.
- Standards drift and fragmented rule sources that silently weaken governance.
- Uncontrolled autonomy or silent policy promotion into truth, prompts, or workflows.
- Health scores that collapse unknown, inferred, and confirmed states into false confidence.
- Fake verification that produces artifacts without exercising the exact changed runtime path.
- Divergence between files, database state, receipts, and UI surfaces.
- Learning loops that amplify weak priors because provenance and review were too loose.

## Roadmap Bias

Recommended sequencing for requirements and planning:

1. Harden task classification, context compilation, workflow routing, and lifecycle linkage.
2. Make truth freshness, writeback governance, and evidence capture mandatory and durable.
3. Expand standards evaluation and delta scoring across key quality domains.
4. Add conservative learning loops that improve routing and packets only from reviewed outcomes.
5. Invest in richer operator UX after the control-plane, governance, and evidence model are trustworthy.
