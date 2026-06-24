# AIOS Adoption Gate Plan

## Goal

Verify that AIOS is ready to route real runs through the managed runtime by exercising default routing, run lifecycle, closeout artifacts, operator search, and daily-flow replay on a copied live database.

## Scope

- Copy `data/aios.db` before every gate run.
- Use isolated temporary logs for `start-work` so stale live session pointers cannot affect the copied database.
- Run three representative pilot stories:
  - AIOS internal bugfix.
  - Non-AIOS project bugfix.
  - AIOS operator UI verification.
- Execute each pilot through `bin/aios-managed-run.py`.
- Require each pilot to produce completed lifecycle linkage, workflow reports, success-criteria evaluation, improvement writebacks, TMCP receipt, route search result, and daily-flow replay evidence.

## Acceptance

- `scripts/aios-adoption-gate.py --db-copy /tmp/aios-adoption-gate.db` exits `0`.
- The generated report records every check as `pass`.
- Daily-flow replay confirms the canonical eight-step trace shape with confirmed route, packet, run, evaluation, writeback, and next-action evidence.

