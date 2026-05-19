# 05-03 Summary: Governance Visibility Surface

## Result

Governance state is now available through typed UI/server control-plane surfaces.

## Shipped

- Added governance overview types for proposals, pending approvals, policy classes, and terminal-run evidence gaps.
- Added `getGovernanceOverview` to the control-plane server layer.
- Embedded governance overview in `getControlPlaneOverview`.
- Added `controlPlane.governance` to the tRPC router.
- Included governance link rules for agents and operators.

## Verification

- `pnpm lint` from `aios-ui/`

The lint command passed with the existing warning-only anti-slop baseline.

## Follow-Up

- Render governance cards in the Control Plane UI.
- Add approve/reject/waive transitions as first-class governance events across all proposal sources.
