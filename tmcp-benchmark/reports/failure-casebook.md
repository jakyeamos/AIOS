# Failure Casebook

## 2026-06-23: first real portable dev-process pair

- Task: `amos-quality-debug-heldout`
- Repository: `amos-saas` at `72148b19e4823e9ecd9751e7ec67754b79287c8d`
- Conditions: `baseline` (`realpair-amos-baseline-260623`) and `tmcp_cold_start` (`realpair-amos-tmcp-cold-260623`)
- Result: both runs failed the public quality command; `test -f package.json` passed, `pnpm lint` failed, and hidden package metadata verification passed.
- Evidence:
  - `tmcp-benchmark/runs/raw/realpair-amos-baseline-260623.json`
  - `tmcp-benchmark/runs/raw/realpair-amos-tmcp-cold-260623.json`
  - `tmcp-benchmark/runs/artifacts/realpair-amos-tmcp-cold-260623/public-1.log`
- Root cause: the benchmark inventory previously treated every discovered Node script as a `pnpm` command. `amos-saas` is an npm-lockfile repo, so the portable command-discovery layer emitted the wrong package-manager command. The run also exposed that isolated worktrees may lack installed dependencies.
- Patch: `services.tmcp_benchmark` now records `package_manager` from `packageManager` or lockfiles and emits `npm run <script>`, `yarn <script>`, or `pnpm <script>` accordingly. Preflight now accepts clean repos with any discovered quality command, not only test commands.
- Claim policy: this pair is failure evidence only. Do not use the aggregate report for performance claims until old dry-run records are separated from real-task records.
