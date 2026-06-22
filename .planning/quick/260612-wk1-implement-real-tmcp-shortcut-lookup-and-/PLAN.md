# Quick Task Plan

Task: Implement real TMCP shortcut lookup and promotion on managed runtime path.

Scope:
- Add receipt-history lookup in `services/tmcp_runtime.py`.
- Mark managed TMCP receipts with workflow execution outcomes in `bin/aios-managed-run.py`.
- Verify with focused tests plus a runtime-shaped managed invocation.

Acceptance:
- Repeated successful traversal fingerprints promote to an active shortcut candidate.
- Managed runtime compiles TMCP packets using persisted receipt history.
- Runtime evidence shows a promoted shortcut in the workflow report artifact.
