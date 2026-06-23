---
id: data-integrity
title: Data Integrity and Migration Safety
scope: domain-specific
blocking: true
evaluation_method: heuristic
version: 1.0
---

## Intent

Protect existing persistent data from loss, corruption, unsafe defaults, and unstable identifiers.

## Applies When

Tasks that touch schema files, migrations, durable SQLite/Postgres tables, data import/export, IDs, timestamps, uniqueness, backfills, or persistence contracts.

## Required Checks

- Confirm migrations preserve existing data.
- Check rollback or recovery path.
- Verify defaults, nullability, uniqueness, and backfill behavior.
- Check timestamp/timezone handling.
- Confirm IDs remain stable where callers depend on them.
- Exercise the migration or write path when feasible.

## Blockers

- Migration can lose or corrupt existing data.
- Required backfill is missing.
- Nullability, uniqueness, or default change can break existing records.
- Rollback/recovery path is absent for a risky schema change.

## Warnings

- Rollback is manual but documented.
- Data shape changed with limited fixture coverage.
- Timezone or ID assumptions need follow-up hardening.

## Evidence To Provide

- Migration risk.
- Backfill needed or ruled out.
- Rollback or recovery plan.
- Data-loss risk.
- Execution evidence against representative data.

## Related Criteria

- `api-contract`
- `test-quality`
- `execution-first-verification`

## Example Good

A nullable-to-required migration backfills existing rows, validates counts, and documents recovery if validation fails.

## Example Bad

A schema change adds a required column with no default and no backfill plan.
