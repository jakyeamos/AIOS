# M6 Provider Telemetry Contract

This contract is the input needed to clear the M6 provider score/cost gate. The
template is intentionally invalid until it contains real provider-backed data;
the validator rejects pending or estimated values.

Run the validator with:

```text
python3 benchmark/m6_provider_telemetry.py \
  docs/evals/M6_PROVIDER_TELEMETRY_MANIFEST_TEMPLATE.json \
  --ledger /private/tmp/aios-m6-promotion-rerun-ledger-20260715-v6.db
```

Each completed manifest must contain, for every ledger run:

- provider request/response identity and model
- input, output, cached-input, and total token counts
- exact provider-reported `cost_usd` (zero is valid; an estimate is not)
- independent score and score provenance
- SHA-256 links to the provider response and score evidence
- the pair/run condition and ledger run ID

The validator is read-only. It does not write `eval_scores`, alter pair
decisions, or make a pair promotion-ready. After an authoritative manifest is
available, it must be ingested through a separately reviewed ledger update and
the adversarial review must be rerun.
