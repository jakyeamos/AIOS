# M6 OpenRouter benchmark lane

This is a separate API-completion lane. It does not replace Codex, instrument
Codex, or write the existing v6 M6 ledger.

## What it does

`benchmark/m6_openrouter_runner.py` sends one prompt to OpenRouter and freezes:

- the request body without authorization headers
- the raw provider response and generation lookup when available
- actual response model and provider generation ID
- provider-reported token counts, cached tokens, and cost
- SHA-256 links for every receipt artifact

It requires `--allow-network` and `OPENROUTER_API_KEY` before making a live
request. The key is never written to the repository. It refuses to overwrite an
existing evidence directory and records `ledger_write: none`.

## Safe invocation

Pin a concrete free model and provider. Do not use `openrouter/free` for a
paired benchmark because that router can select different models between runs.

```text
OPENROUTER_API_KEY=... \
python3 benchmark/m6_openrouter_runner.py \
  --allow-network \
  --model '<publisher>/<model>:free' \
  --provider-only '<provider-slug>' \
  --prompt /path/to/prompt.txt \
  --pair-id openrouter-pair-001 \
  --run-id openrouter-run-001 \
  --condition baseline_repo_only \
  --output-dir /private/tmp/aios-m6-openrouter/openrouter-run-001
```

The treatment run uses the same model, provider, task, and budget but a
different `--run-id` and `--condition aios_portable_context_packet`.

## Scope limits

This runner is not a Codex-like agent harness. If the response contains tool
calls, it writes the receipt but exits non-zero because tool calls require a
separate local execution harness. Do not interpret a completion-only receipt
as evidence for the existing six Codex filesystem/browser tasks.

The current M6 ledger is pinned to `gpt-5.6-luna` and its tasks prohibit
network access. OpenRouter results therefore require a new benchmark scope,
new run/pair IDs, independent score evidence, and a separately reviewed
promotion decision. They must not be joined to or used to fill
`/private/tmp/aios-m6-promotion-rerun-ledger-20260715-v6.db`.

The existing [provider telemetry contract](M6_PROVIDER_TELEMETRY_CONTRACT.md)
can validate a completed, independently scored manifest later, but this runner
does not create score rows or write any ledger.
