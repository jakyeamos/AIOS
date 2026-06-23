# KV-Cache-Aware Local Runner

KV-cache-level memory is an optimization layer, not the source of truth. AIOS must not make direct KV-cache injection a hard dependency for its memory architecture or for compatibility with closed API models.

## Current Position

AIOS should treat stable prompt structure as the portable cache strategy. The layered memory model remains authoritative:

1. Layer A raw sources preserve provenance.
2. Layer B facts preserve current, superseded, contradicted, uncertain, or archived truth.
3. Layer C relationships preserve graph structure.
4. Layer D memory packets render compact Markdown for model reasoning.

The cache layer may accelerate repeated use of Layer D packets, but it must not replace those layers. If a cache is missing, expired, unavailable, or provider-specific, AIOS should still compile and send a correct packet.

## Closed API Models

For closed API models such as OpenAI and Anthropic, direct client-side KV-cache injection is not a practical core dependency. The provider manages the cache inside its serving stack. Clients can influence cache hits by keeping prompt prefixes stable, but they do not upload arbitrary KV entries or control the provider's internal cache memory.

OpenAI exposes prompt-cache observability through `cached_tokens` in usage details for eligible prompts, which confirms cache hits after a request but does not expose direct cache mutation. Anthropic prompt caching works by checking a prompt prefix up to a cache breakpoint and then caching the processed prefix once a response begins. The client controls structure and breakpoints; the server owns the stored cache.

This means AIOS's API-model path should optimize for deterministic prefix layout, not KV-cache APIs. The future `ContextCompiler` from Plan 12-04 should put stable global rules, project truth, memory packet contract text, and reusable current facts before volatile task details. That maximizes prompt-cache reuse today without binding AIOS to one provider.

## Local Runner Opportunity

Local/open-source model serving can eventually make deeper KV-cache-aware memory useful. vLLM automatic prefix caching reuses KV cache when a new query shares the same prefix as an existing query, avoiding recomputation for the shared part. LMCache-style systems go further by managing KV cache storage, movement, sharing, and offload across vLLM/SGLang-style engines.

Operationally, AIOS could use this only after the memory compiler produces stable, repeatable prefixes. A local runner could pin common stable memory blocks, prewarm project packets, and reuse long project/context prefixes across tasks. That would reduce time-to-first-token and repeated prefill work for long AIOS packets.

The important boundary: the local runner optimizes already-valid packet output. It does not decide what truth is current, what source is authoritative, or which contradiction wins. Those remain Layer B/C/D responsibilities.

## Prerequisites

AIOS should not depend on KV-cache-aware serving until all of these are true:

1. A self-hosted or local model runner is deployed and routinely used for AIOS work.
2. The runner exposes a stable KV-cache or prefix-cache API with observable hit/miss behavior.
3. AIOS has a provider adapter layer that can use the cache path without breaking OpenAI, Anthropic, or other API-model compatibility.
4. The layered memory architecture from Plans 12-02 through 12-04 is stable.
5. Cache operations have privacy controls, tenant/project boundaries, invalidation rules, and failure fallbacks.
6. Evaluation shows meaningful latency or cost improvement without degrading answer quality or provenance.

## Bridge From Today To Later

The stable-prefix ContextCompiler is the bridge. It should produce deterministic ordering and separable sections:

- stable global standards and agent rules
- stable project truth
- stable memory packet contract and current facts
- dynamic task context
- dynamic retrieved evidence

That layout helps API prompt caching now and maps naturally to local KV-cache reuse later. If local serving becomes reliable, AIOS can cache the stable prefix without changing the truth model or packet contract.

## Non-Goals

- This note introduces no code, no schema, and no dependencies.
- Do not store authoritative memories only as KV-cache entries.
- Do not make API-model runs depend on local runner availability.
- Do not introduce model-runner dependencies in Phase 12.
- Do not bypass provenance, staleness, contradiction, or confidence rules because cached tokens are faster.

## Sources

- OpenAI prompt caching: https://platform.openai.com/docs/guides/prompt-caching
- Anthropic prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- vLLM automatic prefix caching: https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/
- LMCache documentation: https://docs.lmcache.ai/
