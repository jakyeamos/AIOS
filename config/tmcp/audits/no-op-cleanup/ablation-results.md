# Ablation Results

Date: 2026-06-24

## Static Proof Results

| Candidate | Result | Material behavior change |
|---|---|---|
| NOC-001 | Proven vague legitimate requirement; rewritten. | The prompt-library purpose now names observable required assets instead of "high-quality". |
| NOC-002 | Rejected as no-op candidate; retained metadata. | None; allowlist prevents future false positive churn. |
| NOC-003 | Rejected as no-op candidate; retained metadata. | None; allowlist prevents future false positive churn. |
| NOC-004 | Rejected as no-op candidate; retained anti-example. | None; line continues to reject weak leading words. |
| NOC-005 | Rejected as no-op candidate; retained anti-example. | None; line continues to reject weak leading words. |
| NOC-006 | Rejected as no-op candidate; retained anti-example. | None; line continues to reject weak leading words. |

## Automated Evidence

`pnpm tmcp:no-op-scan` after remediation:

```text
Scanned 96 agent-facing instruction files.
No unallowlisted generic instruction candidates found.
```
