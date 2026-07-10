# Business Memory Privacy

AIOS business memory keeps raw sources, compiled wiki candidates, and optional vault promotions on your machine by default.

## Data flow

1. **Ingest** — connectors copy or receive content into `~/AIOS/staging/raw-sources/`. Immutable JSON snapshots are stored under date-partitioned folders. Metadata lands in `~/AIOS/data/aios.db`.
2. **Compile** — deterministic (and optional LLM) synthesis writes **candidates only** to `~/AIOS/staging/business-wiki-candidates/`. Nothing is promoted to the Obsidian vault automatically.
3. **Query** — FTS retrieval reads SQLite and candidate markdown. Answers include `[src:...]` citations when evidence is available.
4. **Promotion** — humans move reviewed pages into `06 Knowledge/Business/` in Command-Center with explicit `trust` and `sensitivity` frontmatter.

## Secrets and local-only defaults

- API keys and OAuth tokens live in `~/AIOS/.env` (see `.env.example`). Never commit `.env`.
- Raw private exports stay under `staging/` and are excluded from git by default.
- `commit_raw: false` and `commit_wiki: false` in business source config prevent accidental git commits of sensitive material.

## LLM opt-in

By default, **no raw source text is sent to external LLMs**.

LLM use requires an explicit flag:

- `business-compile.py --llm` — optional enrichment during compile
- `business-query.py --llm` — optional narrative answer over retrieved snippets

Provider resolution order when `--provider auto`:

1. OpenAI-compatible API (`OPENAI_API_KEY`)
2. Local subscription CLI (`codex exec`, `claude -p`)
3. Agent queue mode (job files for in-editor processing)

Use `business-compile.py --llm-status` to see which provider would run.

## Redaction

`services/business/privacy/redact.py` strips emails, phone numbers, and common API token patterns from log or LLM payloads when you call it explicitly. Deterministic compile does not require redaction because it does not leave the machine unless you opt into LLM.

## Sensitivity tiers

Business pages carry `sensitivity: public|internal|private|sensitive`. Agents should not load `private` or `sensitive` pages into context unless the user opts in.

## Lint and audit

`business-lint.py` writes:

- `~/AIOS/logs/business-lint-latest.json`
- `staging/business-wiki-candidates/lint-report.md`

Run lint after compile and before vault promotion.
