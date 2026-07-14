---
title: Close the M2 Browser Validation Frontier
type: task
status: resolved
claim: /root (2026-07-14)
resolved: 2026-07-14
blocked_by: []
blocks:
  - 009-ship-read-only-v2-operator-shell
---

# Close the M2 Browser Validation Frontier

## Question

Can the committed UI produce the seeded control-plane route responses and
browser evidence required by ADR-004 without weakening the validation
contract?

## Scope

- Verify seeded `controlPlane.overview` and `controlPlane.runDetail` responses.
- Exercise the control-plane route at 375x812, 768x1024, and 1440x900.
- Capture same-origin network status, console errors, landmarks, focusable
  controls, and duplicate-key behavior.
- Fix only deterministic M2 validation defects; do not begin the v2 shell.
- Record the remaining harness or environment gap as an explicit blocker.

## Completion Evidence

- Source-backed overview and typed run-detail responses return 200.
- All three viewport checks have no horizontal overflow or browser errors.
- Same-origin requests have no 4xx/5xx responses.
- Keyboard-only and pointer checks run through the pinned checked-in harness.

## Resolution

The seeded overview returned 16 workflow templates, 20 runs, 12 packets, and
25 findings. The seeded run-detail route returned a typed response with three
events. The in-app browser matrix passed at all three required viewports with
no horizontal overflow, one main landmark, one navigation landmark, 79
focusable controls, and no console errors. Same-origin capture observed 24
requests; the run-detail tRPC response was 200 and no captured request failed.

The duplicate React-key defect in run-detail standards deltas was fixed by
using a stable composite key. Playwright 1.61.1 is pinned in the UI package,
and the checked-in browser contract now passes seeded overview/run-detail
checks, all three viewports, same-origin response checks, console policy, and
real Tab traversal with visible focus. The production build is warning-free:
prompt and workflow registries are generated before build, and managed-runtime
spawn arguments are statically traceable. M2 is resolved; M3 is unblocked.
