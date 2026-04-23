# Anti-Slop ESLint Ratchet (Phase 1b)

Date: 2026-04-23  
Status: Ratchet pass implemented

## 1) Audit Snapshot

- `aios-ui/eslint.config.mjs` already had `eslint-plugin-anti-slop` wired with all seven rules.
- `.config/anti-slop.json` already held project lexicon configuration.
- Missing pieces before this pass:
  - no fixture lane to protect against false positives
  - no architecture-enforcement adapter for anti-slop fixture checks
  - no CI workflow wiring for anti-slop-specific verification
  - no per-rule operating guidance for rollout across linked TS/React repos

## 2) Ratchet Changes

### Fixture-based false-positive checks
- Added fixture config:
  - `aios-ui/eslint/anti-slop-fixtures.config.mjs`
- Added pass fixtures:
  - `aios-ui/eslint/fixtures/anti-slop/pass/client-interaction.jsx`
  - `aios-ui/eslint/fixtures/anti-slop/pass/app/runs/page.jsx`
- Added npm script:
  - `npm run lint:anti-slop:fixtures`

### Architecture-enforcement metadata
- Added `anti-slop-fixtures` adapter in:
  - `config/architecture-enforcement/profiles.json`
- Adapter executes `npm run lint:anti-slop:fixtures` when required anti-slop fixture/config paths exist.

### CI/check wiring
- Added GitHub Actions workflow:
  - `.github/workflows/aios-ui-quality.yml`
- Workflow runs:
  - `npm --prefix aios-ui run lint`
  - `npm --prefix aios-ui run lint:architecture`
  - `npm --prefix aios-ui run lint:anti-slop:fixtures`

## 3) Per-Rule Guidance

### `no-unjustified-use-client`
- Keep as `error`.
- Expected-safe signals: React state/effect hooks, JSX event handlers, browser globals, configured client-only imports.

### `no-useless-memo`
- Keep as `warn`.
- Promote to `error` only after repeated evidence of low false-positive rate in fixture and app code.

### `no-placeholder-copy`
- Keep as `error`.
- Changes to placeholder pattern list should be reviewed with concrete examples.

### `no-marketing-copy`
- Keep as `warn`.
- Maintain project lexicon in `.config/anti-slop.json`; avoid globally banning domain-critical terms.

### `require-empty-state-action`
- Keep as `warn`.
- Require either action wording (`run`, `retry`, etc.) or actionable controls in empty-state blocks.

### `no-demo-data-primary-path`
- Keep as `error` for route files.
- Allow demo imports only with real-data indicators present in same route path.

### `no-generic-stat-label`
- Keep as `warn`.
- Tune blocked labels in `.config/anti-slop.json` as product lexicon evolves.

## 4) Rollout Guidance for Linked TS/React Repos

1. Copy `.config/anti-slop.json` and tune lexicon per repo domain.
2. Add plugin wiring to `eslint.config.mjs`.
3. Add `lint:anti-slop:fixtures` script with at least one pass fixture.
4. Start with recommended severities (`error` only for high-confidence rules).
5. Promote warnings to errors only after two clean cycles with low disable churn.
