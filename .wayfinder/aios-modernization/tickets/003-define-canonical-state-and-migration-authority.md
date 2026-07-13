---
title: Define Canonical State and Migration Authority
type: research
status: closed
claim: /root (2026-07-13)
blocked_by: []
blocks:
  - 005-classify-satellite-subsystems-and-select-modernization-strategy
  - 006-write-v2-target-and-vertical-modernization-plan
---

# Define Canonical State and Migration Authority

## Question

Which system owns each durable fact and mutation in v2, and what versioned
schema, connection, backup, recovery, and rollback contract makes a large
rewrite safe?

## Scope

- Define the lifecycle and ownership of Project, Work/Run, Invocation, Packet,
  Evidence, Approval, Memory, and their source-backed projections.
- Classify the main SQLite store, CTS stores, vault, staging/raw sources,
  generated context, indexes, and audit data by authority, retention, and
  migration obligation.
- Choose one main-store schema/migration owner and one SQLite connection
  policy, including foreign-key, concurrency, integrity-check, and rollback
  behavior.
- Specify private-data classification, LLM egress/consent/redaction evidence,
  and the configuration/path contract appropriate to the chosen trust boundary.

## Completion Evidence

- A data-authority diagram and source-of-truth matrix.
- A migration/recovery design tested against representative sanitized data.
- Explicit preserve, transform, archive, and delete rules for legacy state.

## Dependencies

Satisfied by [Establish a Reproducible Baseline and Product Invariants](001-establish-reproducible-baseline-and-invariants.md) and [Choose the V2 Operating Loop and Trust Boundary](002-choose-v2-operating-loop-and-trust-boundary.md).

## Resolution

Accepted [ADR-002: Canonical State and Migration Authority](../../../docs/modernization/ADR-002-canonical-state-and-migration-authority.md).

The main store remains local `AIOS_DB`, with one Python-owned, versioned,
checksummed migration ledger and one logical mutation authority. The current
SQL snapshots and runtime DDL are migration inputs, not competing authorities;
the Next UI must become a client of the shared storage contract. Every
connection uses the same path and baseline SQLite pragmas, while migrations
run outside request handlers with a pre-migration backup.

The live store is not migration-ready: its copied snapshot has 557 FK
violations, `user_version=0`, and no main migration ledger. Orphan and ambiguous
rows must be quarantined with original payloads before deterministic transforms;
destructive cleanup requires explicit approval. The ADR records the source of
truth matrix, recovery gates, privacy invariants, and disposable fixture/backup
evidence without modifying live data.
