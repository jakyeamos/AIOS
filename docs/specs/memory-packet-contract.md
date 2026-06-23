# AIOS Memory Packet Contract

## Purpose

This contract governs every model-facing memory packet produced by `services/memory_compiler.py`.
The compiler may read structured JSON, SQLite rows, graph edges, or context receipts internally, but
the final model-facing packet must be readable, compact, and organized for LLM reasoning.

Raw JSON may not appear in model-facing output. This is an immutable rule. JSON is allowed only as an
internal representation, a database payload, a test fixture, or a debug artifact outside the final
packet body sent to a model.

## Required Sections

Every model-facing memory packet must include these sections in this order:

1. `Current Truth`
2. `Sources/Provenance`

`Current Truth` contains the active facts the model should rely on for the current task.
`Sources/Provenance` contains the minimum source trail required to audit the packet. This section is
never dropped under token pressure.

## Optional Sections

The compiler may include these sections when relevant source material exists:

1. `Relevant Prior Decisions`
2. `Constraints`
3. `Causal/Dependency Chain`
4. `Contradictions or Stale Information`
5. `Open Questions`

Optional sections are omitted when empty. Empty placeholder headings are not allowed.

## Section Ordering Rules

When all sections are present, the order is:

1. `Current Truth`
2. `Constraints`
3. `Causal/Dependency Chain`
4. `Relevant Prior Decisions`
5. `Contradictions or Stale Information`
6. `Open Questions`
7. `Sources/Provenance`

This ordering is also the token budget priority, except that `Sources/Provenance` is mandatory and
must remain present even if it is shortened.

## Internal Schema Representation

The internal packet representation may be structured as rows or JSON using this shape:

- `packet_id`: stable packet identifier.
- `mode`: compiler mode, such as `compact`, `full`, or `verification`.
- `current_truth`: ordered list of fact ids and rendered fact text.
- `constraints`: ordered list of active constraint fact ids.
- `causal_chain`: ordered relationship ids using allowed predicates from
  `services/memory_layers.py:ALLOWED_PREDICATES`.
- `prior_decisions`: ordered list of decision facts or source ids.
- `contradictions_or_stale`: ordered list of superseded, contradicted, uncertain, or archived fact ids.
- `open_questions`: ordered list of question facts or relationships.
- `sources`: ordered list of source ids from `memory_raw_sources`.
- `token_count`: estimated model-facing token count.

Internal fields may contain raw ids, JSON arrays, database rows, or graph edges. The rendered packet
must translate those internals into prose bullets with source labels.

## Model-Facing Markdown Format

The rendered packet must use compact Markdown:

```markdown
# Memory Packet: <title or task>

## Current Truth

- <fact text> [S1]

## Constraints

- <constraint text> [S2]

## Sources/Provenance

- [S1] <source_type>: <source_path or stable id> (<confidence>, <freshness/status>)
```

Rules:

- Use concise bullets, not raw table dumps.
- Include source markers such as `[S1]` on factual claims.
- Prefer stable source paths or ids over long excerpts.
- Include confidence and status when they materially affect trust.
- Do not include raw JSON, SQL rows, or unrendered graph triples.

## Validity Status Semantics

`memory_facts.validity_status` has these allowed meanings:

- `active`: current truth; eligible for `Current Truth`, `Constraints`, `Causal/Dependency Chain`,
  `Relevant Prior Decisions`, and `Open Questions`.
- `superseded`: replaced by a newer fact; render only in `Contradictions or Stale Information` when
  relevant to avoid using stale guidance.
- `contradicted`: conflicts with another active fact; render in `Contradictions or Stale Information`
  with both sides or with a clear missing-side warning.
- `uncertain`: low confidence or incomplete evidence; render outside `Current Truth` unless the task
  explicitly needs uncertainty.
- `archived`: intentionally retired; omit unless explaining historical context or migration history.

These values must match `services/memory_layers.py:FactMemory` validation. A packet compiler that
silently treats unknown statuses as active is non-compliant.

## Provenance Rules

Every packet must preserve provenance from model-facing claims back to sources:

- Every `Current Truth` bullet needs at least one source marker.
- Every contradiction or stale warning needs the source marker for the stale/conflicting item.
- `Sources/Provenance` must include source id or path, source type, confidence, and status/freshness
  when available.
- Source labels must be stable within the packet. `[S1]` cannot refer to different sources in
  different sections.
- Long source excerpts are optional. Stable ids and compact labels are preferred under token pressure.

## Stale And Superseded Facts

Stale or superseded facts must not appear as current truth. If relevant, they belong in
`Contradictions or Stale Information` with one of these forms:

- `Superseded: <old fact> -> replaced by <new fact> [S1, S2]`
- `Stale: <fact> has expired or lacks recent confirmation [S3]`
- `Archived: <fact> is historical context, not current guidance [S4]`

The compiler must prefer active facts with recent confirmation over expired, superseded, or archived
facts.

## Contradiction Handling

Contradictions require explicit handling:

- If two active facts conflict, include both in `Contradictions or Stale Information`.
- If one side is superseded, mark the superseded side and keep the active side in `Current Truth`.
- If confidence differs, name the stronger source and confidence reason.
- If the compiler cannot resolve the contradiction, add an `Open Questions` bullet instead of
  flattening the conflict into a single false certainty.

## Confidence Levels

Confidence may be numeric internally, but the model-facing packet uses these labels:

- `high`: confidence >= 0.8, recent or authoritative source.
- `medium`: confidence >= 0.5 and < 0.8, plausible but not fully authoritative.
- `low`: confidence < 0.5 or source is inferred, stale, partial, or unreviewed.
- `unknown`: no confidence signal exists.

Low or unknown confidence facts do not belong in `Current Truth` unless the packet explicitly frames
them as uncertainty for the task.

## Token Budget Priority

When a packet exceeds budget, trim in this priority order:

1. Keep `Current Truth`.
2. Keep `Constraints`.
3. Keep `Causal/Dependency Chain`.
4. Keep `Relevant Prior Decisions`.
5. Keep `Contradictions or Stale Information`.
6. Keep `Open Questions`.
7. Shorten but never remove `Sources/Provenance`.

Source excerpts are shortened before source labels are removed. The `Sources/Provenance` heading and
at least one source line per retained factual section must remain.

## Good Packet Example 1

```markdown
# Memory Packet: Phase 12 Memory Compiler

## Current Truth

- AIOS stores raw sources, normalized facts, typed relationships, and packet receipts in SQLite. [S1]
- Relationship predicates must come from the shared `ALLOWED_PREDICATES` set. [S2]

## Constraints

- The model-facing packet must be Markdown, not raw JSON. [S3]

## Sources/Provenance

- [S1] schema: `schema.sql` (high, active)
- [S2] service: `services/memory_layers.py` (high, active)
- [S3] spec: `docs/specs/memory-packet-contract.md` (high, active)
```

Why this is good: it includes current truth, constraints, and source markers without exposing raw
database rows.

## Good Packet Example 2

```markdown
# Memory Packet: Runtime Resume Behavior

## Current Truth

- `ensure_runtime_schema` installs memory layer tables on first runtime touch. [S1]

## Causal/Dependency Chain

- Runtime schema setup supports memory compiler persistence; memory compiler persistence supports
  packet receipt auditing. [S1, S2]

## Open Questions

- Whether packet receipts should be attached to every session-start packet remains unresolved. [S3]

## Sources/Provenance

- [S1] runtime: `bin/aios_orchestration_runtime.py` (high, active)
- [S2] service: `services/memory_layers.py` (high, active)
- [S3] audit: `docs/audits/graph-native-memory-audit.md` (medium, active)
```

Why this is good: it separates truth, dependency reasoning, and unresolved questions while preserving
source labels.

## Bad Packet Example 1

```markdown
# Memory Packet

{"current_truth":[{"fact_text":"AIOS has memory tables","source_id":"raw-1"}]}
```

Violation: raw JSON appears in model-facing output. This violates the immutable no-raw-JSON rule and
the model-facing Markdown format.

## Bad Packet Example 2

```markdown
# Memory Packet: Memory Schema

## Current Truth

- AIOS still uses only flat grep retrieval.

## Sources/Provenance
```

Violation: the current-truth bullet has no source marker, the source section is empty, and the claim
ignores newer active facts. This violates provenance rules, source non-dropping rules, and stale
fact handling.

## Compliance Checklist

- Required sections are present.
- Optional sections are included only when non-empty.
- Section order follows this contract.
- Internal JSON/rows/edges are rendered into readable Markdown.
- Every current-truth claim has provenance.
- `validity_status` values use only `active`, `superseded`, `contradicted`, `uncertain`, or
  `archived`.
- Contradictions are surfaced instead of flattened.
- Low-confidence facts are marked or excluded from current truth.
- Token trimming follows the defined priority.
- `Sources/Provenance` is present under every token budget.
