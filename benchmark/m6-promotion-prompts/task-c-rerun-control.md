You are one side of a fresh bounded M6 browser-contract rerun. Work only in this
clean repository at the protected start SHA. Do not use private state, network,
production systems, or credentials. Do not edit product code or project truth.

Task: repair and verify the Verify → Review → Closeout browser contract.

Required implementation surface:
- `aios-ui/tests/browser/m6-verify-review-closeout.spec.ts`
- `aios-ui/tests/browser/global-setup.ts`
- existing browser fixture helpers only when needed

Required contract:
1. Cover distinct Verify, Review, and Closeout journeys and assert the stage rail
   contains all three labels with the expected active stage.
2. Seed one deterministic lifecycle event for each seeded run, including a
   closeout event for the closed fixture.
3. Seed a valid closed session and one closeout artifact linked by its required
   non-null `session_id`; include the run id and evidence ids in artifact metadata
   so touched-file/provenance assertions are meaningful.
4. Use the structured packet-section shape consumed by the run-inspection view.
5. Assert the closeout event list and touched-file count are visible.
6. Keep the expected error allowlist narrow: only the known exact 412
   `controlPlane.reviewWriteback` response is allowed; no arbitrary 4xx/5xx.
7. Preserve mobile, tablet, desktop, keyboard, provenance, console, and network
   checks already required by the existing spec.

Run and report exact results for UI lint, architecture lint, production build,
browser discovery, and the focused browser spec. If the runner is incapable of
loopback/browser execution, record that as an environment blocker rather than
weakening the contract.
