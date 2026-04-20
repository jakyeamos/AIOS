# Topic Graph, Ranked Packets, and Taski Operating Surface

Date: 2026-04-19

## Topic Graph Model

AIOS now has a persisted topic graph layer in SQLite rather than relying only on read-time wiki derivation.

Core tables:

- `knowledge_topics`
- `knowledge_relationships`
- `knowledge_references`
- `knowledge_markers`
- `knowledge_graph_state`

The graph is built from:

- curated vault wiki pages
- project state
- orchestration runs
- briefing packets
- memory updates
- workflow and agent registry entries
- locked policy/task-type topics

Design intent:

- topics are the durable cross-cutting linkage surface
- references carry provenance back to concrete sources
- relationships carry cross-topic linkage
- markers surface drift, contradiction, and staleness
- one run, packet, or memory update may attach to multiple topics at once

This allows AIOS to answer questions and assemble packets from a multifaceted topic layer instead of one-document-at-a-time retrieval.

## Packet Assembly and Ranking Model

Default packet policy is `compact-ranked`.

The operating rule is:

- retrieve broadly inside AIOS
- rank internally across topics, memory, runs, project truth, policies, and CTS
- deliver only compact, explicit, token-budgeted output to the agent
- expose omission and selection trace
- require targeted expansion for anything beyond the compact packet

Packet candidates are ranked from:

- direct project truth
- top matching indexed topics
- recent related runs
- recent memory updates
- workflow and agent policy signals
- prior improvement writebacks
- CTS code-topology context

Stored packet metadata now includes:

- `policy_mode`
- `token_budget`
- `selection_trace_json`
- `omitted_context_json`

This keeps AIOS responsible for shaping and tracing context instead of pushing ranking responsibility onto the agent.

## Why Hybrid Ranked Packet Delivery Is the Default

Open default corpus access was rejected as the baseline model.

Reasons:

- it weakens inspectability
- it degrades policy learning quality
- it wastes tokens
- it makes AIOS less of a control plane and more of a passive search layer

The chosen model preserves retrieval power while keeping AIOS responsible for:

- ranking
- shaping
- omission
- expansion control
- future learning from what was actually useful

## Expansion Mode

Expansion is explicit and traced through `packet_expansions`.

Supported request kinds:

- `topic`
- `failure_pattern`
- `code_area`
- `policy`
- `recent_run`

Every expansion records:

- what was requested
- which packet and run it attached to
- token budget
- what was returned
- trace metadata for why the returned context was chosen

Explore mode exists, but it is an explicit orchestration mode for ambiguous or research-heavy tasks. It is not the default packet policy.

## Approval Gates

Improvement writeback lands in `improvement_writebacks`.

Writebacks may attach to:

- topic
- project
- workflow
- task type
- global policy

Approval rules:

- global behavior changes require approval
- anything likely to worsen token efficiency requires approval
- token-regressive or global proposals should remain non-default until approved

This keeps AIOS self-improving without letting every local success quietly mutate global behavior.
