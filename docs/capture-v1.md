# `capture.v1` source capture

AIOS exposes a deterministic, review-first boundary for source adapters. It
normalizes one adapter payload into a `capture.v1` envelope without network
access, enrichment, or Obsidian vault writes.

## Input

The CLI accepts a JSON object with:

- `source`: `provider`, `input_format`, `source_uri`, and raw `content`;
- `metadata`: source metadata kept separate from the body;
- `adapter`: name, version, trigger, and canonical field expressions;
- `provenance`: extractor, selector, options, retry count, profile, and prior
  removal records.

Supported input formats are `URL`, `HTML`, `Markdown`, `JSON`, and `CSV`.

## Run

```bash
jq '.[0]' tests/fixtures/capture-v1-input-fixtures.json > /tmp/capture-v1-input.json
uv run python bin/capture-v1.py \
  --input /tmp/capture-v1-input.json \
  --output /tmp/capture-v1.json
```

The fixture file contains an array for test coverage; the CLI consumes one
object at a time. A source adapter can select one object before invoking the
CLI. The output is validated before it is printed or written.

The canonical schema is [`config/contracts/capture.v1.schema.json`](../config/contracts/capture.v1.schema.json).
The runtime is intentionally downstream of extraction and upstream of any
optional enrichment or governed vault writeback.

## Business-memory adapter

The manual business-memory inbox consumes this boundary through
`services.business.normalize.normalize_manual_file`. Markdown, JSON, HTML, and
CSV files become the existing `SourceRecord` shape; the raw JSON sidecar also
retains the `capture.v1` adapter, validation, and provenance/removal metadata.
This adapter does not fetch, enrich, write to the vault, or create a second
database authority. To roll back this slice, restore the prior
`normalize_manual_file` implementation and remove the `capture` field from
new raw sidecars; no database migration is required.
