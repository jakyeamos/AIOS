# M1 Retention Decision

**Status:** Awaiting explicit human disposition
**Updated:** 2026-07-14
**Scope:** The 73 unresolved `quality_pipeline_runs` rows identified by the
copied-store M1 transformer.

## Decision required

The live store has not been modified. Before a write-capable migration can be
approved, choose one disposition for the 73 unresolved quality rows:

| Option | Meaning | Consequence |
| --- | --- | --- |
| **A — retain in a local read-only archive (recommended)** | Keep the original payloads in the migration quarantine/archive and remove them from the active projection during reconciliation. | Preserves audit/recovery evidence and avoids irreversible deletion. |
| **B — delete after review** | Confirm that every row is derived, rebuildable, and not required for audit or provenance, then record an explicit deletion ledger. | Irreversible; requires a reviewed backup and row-level sign-off. |
| **C — split by row** | Review the 73 rows individually and assign archive or delete dispositions. | Highest review cost; allows a mixed outcome when evidence differs. |

No option is applied automatically. The reviewer must record the selected
option, reviewer identity, date, and any row-level exceptions below.

```text
Disposition: pending human decision
Reviewer: pending
Date: pending
Exceptions: none recorded
```

## Disposable evidence

The evidence run used a fresh temporary copy of the current local store and
printed aggregate counts only; no original payloads are committed to the
repository.

| Check | Result |
| --- | --- |
| Live preflight | `quick_check=ok`, `integrity_check=ok`, `user_version=0` |
| Live FK inventory | 561 violations; read-only observation only |
| Copied transformer | 561 quarantines; 255 quality rows mapped by unique working directory; 73 quality rows unresolved; 180 missing session references retained with null-session review disposition; 53 missing shadow-task references retained with null-task/archive disposition |
| Copied postflight | `quick_check=ok`, `integrity_check=ok`, zero FK violations, `user_version=1` |
| Restore drill | Restored copy passed quick, integrity, and FK checks; `user_version=1` |
| Replay | Read-only `daily-flow` preview produced all 8 canonical steps |
| Live mutation | None; the source database remained untouched |

## Approval gate

Until the decision above is recorded and the 561 live FK violations are
reconciled against the accepted disposition, the M1 write-capable migration
gate remains closed. The copied-store backup, quarantine, restore, and replay
path is the approved evidence path for further review.
