# Complexity Pattern Checklist

Patterns derived from codex-complexity-optimizer (https://github.com/Kappaemme-git/codex-complexity-optimizer) and the AIOS Complexity+Simplification Gate spec. This is a local copy — no external dependency.

Use this checklist when Rule 12 triggers the Complexity + Simplification Gate. For every real pattern found, record a hotspot with the template in `docs/quality/complexity-simplification-gate.md`, then follow that doc's fix-now-vs-defer rule.

## Criteria Mapping

- Algorithmic patterns: `complexity-budget`
- Render/UI patterns: `performance-budget`, `thin-display`
- Data-access patterns: `complexity-budget`, `data-integrity`, `api-contract` when caller behavior changes

## Algorithmic Complexity Patterns

### 1. Nested-Loop-Scan

- What to look for: `for x in items: for y in items:` or nested loops over collections that can grow with user or database data.
- Why it matters: often turns linear work into O(n^2) work as data grows.
- Preferred remedy: build a lookup map, pre-group records, or use a join/indexed query before the loop.

### 2. Repeated-Collection-Scan

- What to look for: multiple `find`, `filter`, `map`, or list comprehensions over the same collection for related values.
- Why it matters: repeated full scans hide avoidable O(k*n) behavior.
- Preferred remedy: compute all needed values in one pass or precompute keyed structures.

### 3. Sort-Inside-Loop

- What to look for: `sort`, `sorted`, `.sort()`, or order-by style work repeated inside a loop.
- Why it matters: repeated O(n log n) work can dominate the path.
- Preferred remedy: sort once before the loop or maintain an ordered structure.

### 4. Linear-Lookup-That-Should-Be-Map

- What to look for: `array.find`, `list.index`, `filter()[0]`, or manual search inside a loop by ID/key.
- Why it matters: repeated linear lookup turns joins into O(n*m).
- Preferred remedy: build `{id: item}` / `Map<id, item>` / dictionary lookups before joining.

### 5. N+1-Query

- What to look for: one database/API call to fetch a list, followed by one call per item.
- Why it matters: latency and load grow with result count.
- Preferred remedy: batch IDs, join in SQL, eager-load relations, or fetch details in one query.

### 6. Repeated-Object-Construction

- What to look for: recreating the same config, regex, formatter, schema, dict, or object in a hot path.
- Why it matters: allocation and initialization cost repeats unnecessarily.
- Preferred remedy: hoist stable construction outside the loop or cache by stable key.

### 7. Unbounded-Accumulation

- What to look for: appending to a list, array, log buffer, or in-memory map without limit or pagination.
- Why it matters: memory usage grows with data size and can fail under backfill or long-running jobs.
- Preferred remedy: stream results, page work, cap buffers, or flush batches.

### 8. Deep-Clone-In-Hot-Path

- What to look for: `copy.deepcopy`, `structuredClone`, or `JSON.parse(JSON.stringify(...))` inside loops or render paths.
- Why it matters: deep cloning scales with object size and often masks mutation problems.
- Preferred remedy: clone only changed branches, use immutable update helpers, or avoid mutation at the source.

### 9. Missing-Memoization-Boundary

- What to look for: expensive derived data recalculated on every call for identical inputs.
- Why it matters: repeated derivation can become the hidden hot path.
- Preferred remedy: memoize by stable input, cache at the service boundary, or precompute once per request.

### 10. Repeated-Serialization/Parsing

- What to look for: repeated JSON/YAML/config parsing or stringifying in loops or request handlers.
- Why it matters: parsing cost grows with payload size and repeats work already done.
- Preferred remedy: parse once, pass structured data, cache parsed config, or serialize only at boundaries.

## Render/UI Complexity Patterns

### 11. Expensive-Derived-Data-Without-Memo

- What to look for: filtering, grouping, sorting, or aggregating props/state directly on every render.
- Why it matters: render cost grows with data size and interaction frequency.
- Preferred remedy: use memoization with stable dependencies or move derivation server-side.

### 12. Unstable-Prop-Reference

- What to look for: inline object, array, or function literals passed to memoized child components.
- Why it matters: new references force child work even when data is unchanged.
- Preferred remedy: hoist constants, use stable callbacks, or pass primitive props when possible.

### 13. Missing-Key-On-List

- What to look for: list rendering with missing keys, indexes as keys for mutable lists, or unstable generated keys.
- Why it matters: unstable identity causes unnecessary remounts and state loss.
- Preferred remedy: use stable domain IDs or deterministic composite keys.

### 14. Heavy-Computation-In-Render

- What to look for: sorting, searching, parsing, markdown processing, graph layout, or aggregation inside render functions.
- Why it matters: render should be cheap and predictable.
- Preferred remedy: precompute outside render, memoize, virtualize, or move heavy work to server/data layer.

## Data Access Complexity Patterns

### 15. N+1-In-Loop

- What to look for: database calls inside loops after an initial query.
- Why it matters: DB round trips grow with result size and can overload local SQLite or remote stores.
- Preferred remedy: query with `WHERE id IN (...)`, join tables, or batch reads.

### 16. Unbounded-Query

- What to look for: queries against potentially large tables without `LIMIT`, pagination, cursor, or scoped predicate.
- Why it matters: one request can load the whole store and block the workflow.
- Preferred remedy: add pagination, bounded windows, indexed predicates, or streaming.

### 17. Missing-Index-On-Hot-Path

- What to look for: frequent filters, joins, or ordering over columns without supporting indexes.
- Why it matters: repeated scans become a durable performance floor.
- Preferred remedy: add an index in a migration after validating write cost and query shape.

## How To Use

1. Pick the categories that match the code you changed.
2. Scan each changed file for the listed structural cues.
3. Use `scripts/quality-eval.sh` for complementary file-level metrics; this checklist covers judgment-heavy algorithmic patterns.
4. Record real hotspots with file, category, severity, confidence, suggested remediation, behavior risk, tests/benchmarks needed, and agent-safe classification.
5. Fix only when the gate allows it; defer the rest to a remediation pass.
