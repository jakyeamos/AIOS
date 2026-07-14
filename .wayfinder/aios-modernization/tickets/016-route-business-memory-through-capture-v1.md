---
title: Route Manual Business Sources Through the Capture V1 Boundary
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by: []
---

# Route Manual Business Sources Through the Capture V1 Boundary

## Question

Can the first business-memory source adapter consume the pinned `capture.v1`
envelope without creating a second source authority or changing governed
writeback behavior?

## Scope

Route the manual source adapter through the deterministic `capture.v1`
normalizer for supported Markdown, JSON, HTML, and CSV inputs. Preserve the
existing `SourceRecord` and raw-source contracts, metadata, provenance, and
immutable raw payload behavior. This is an adapter-only slice: no network
fetches, enrichment, vault writes, database schema changes, or satellite
promotion are in scope.

## Completion Evidence

- The manual adapter emits the existing `SourceRecord` shape from a validated
  `capture.v1` envelope.
- Fixture coverage proves deterministic normalization, source metadata,
  content hashing, and provenance/removal records.
- The business ingest path remains Python-owned and does not write during
  normalization; existing ingest tests remain green.
- A rollback/deletion note identifies the adapter entry point and the prior
  normalization path that can be restored without data migration.

## Resolution

Resolved as an adapter-only slice. `ManualConnector` now accepts Markdown,
JSON, HTML, and CSV inbox files and routes normalization through the pinned
`capture.v1` runtime. The existing `SourceRecord` contract remains the
business-memory ingest shape; capture schema, adapter, validation, and
provenance/removal metadata are retained in the immutable raw JSON sidecar.
No network fetch, enrichment, vault write, schema migration, or promotion path
was added. The prior normalization behavior remains the rollback target and
requires no data migration.

Evidence:

- `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=. uv run pytest -q tests/test_business_capture_adapter.py tests/test_capture_v1.py` — 11 passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check services/business/normalize.py services/business/models.py services/business/connectors/manual.py services/business/pipeline.py tests/test_business_capture_adapter.py` — passed.
- `UV_CACHE_DIR=/tmp/uv-cache uv run basedpyright services/business/normalize.py services/business/models.py services/business/connectors/manual.py services/business/pipeline.py tests/test_business_capture_adapter.py` — 0 errors.
