# M1 Retention Decision

**Status:** Approved and applied
**Updated:** 2026-07-14
**Scope:** The 73 unresolved `quality_pipeline_runs` rows identified by the
copied-store M1 transformer.

## Decision recorded

The user approved Option A. The 73 unresolved quality payloads are retained in
the live store's local read-only `migration_quarantine` archive, while the
unresolved active rows were removed so the FK graph can be reconciled. No
payloads were committed to Git or sent externally.

| Option | Meaning | Consequence |
| --- | --- | --- |
| **A — retain in a local read-only archive (recommended)** | Keep the original payloads in the migration quarantine/archive and remove them from the active projection during reconciliation. | Preserves audit/recovery evidence and avoids irreversible deletion. |
| **B — delete after review** | Confirm that every row is derived, rebuildable, and not required for audit or provenance, then record an explicit deletion ledger. | Irreversible; requires a reviewed backup and row-level sign-off. |
| **C — split by row** | Review the 73 rows individually and assign archive or delete dispositions. | Highest review cost; allows a mixed outcome when evidence differs. |

The decision and the technical dispositions for the remaining deterministic
repair classes are recorded in `migration_quarantine.reviewer_decision`.

```text
Disposition: A — retain in a local read-only archive
Reviewer: user-approved via Codex session
Date: 2026-07-14
Exceptions: none recorded
```

## Migration evidence

The evidence run used a fresh temporary copy of the current local store and
printed aggregate counts only; no original payloads are committed to the
repository.

| Check | Result |
| --- | --- |
| Disposable preflight | 561 FK violations; copied transform quarantined 561; post-transform and restored copies had zero FK violations; 8-step replay passed |
| Live migration | `m001-archive-live-20260714` ran under `BEGIN IMMEDIATE`; 561 quarantine rows recorded; all 561 rows have an explicit reviewer/technical decision |
| Live postflight | `quick_check=ok`, `integrity_check=ok`, zero FK violations, `user_version=1` |
| Archive scope | 73 `quality_pipeline_runs` rows with `archive-approved-by-user-2026-07-14` |
| Technical dispositions | 255 deterministic project maps; 180 retained with null session; 53 retained with null task |
| Restore drill | Pre-backup restored with the original 561 FK violations; post-backup restored with zero FK violations and `user_version=1` |
| Replay | Read-only `daily-flow` preview produced all 8 canonical steps against the migrated live store |
| Live mutation | Approved archive and deterministic FK reconciliation only; no external egress |

## Approval gate

The archive decision is recorded and the live FK graph is reconciled. The
immutable backups are retained at the local paths recorded in the migration
ledger; restore remains the rollback path. Later write-capable v2 product
features remain subject to their own UI, approval, and operator validation
gates.
