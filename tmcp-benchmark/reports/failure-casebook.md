# Failure Casebook

## 2026-06-23: first real portable dev-process pair

- Task: `bidcamp-quality-debug-heldout`
- Repository: `BidCamp` at `72148b19e4823e9ecd9751e7ec67754b79287c8d`
- Conditions: `baseline` (`realpair-bidcamp-baseline-260623`) and `tmcp_cold_start` (`realpair-bidcamp-tmcp-cold-260623`)
- Result: both runs failed the public quality command; `test -f package.json` passed, `pnpm lint` failed, and hidden package metadata verification passed.
- Evidence:
  - `tmcp-benchmark/runs/raw/realpair-bidcamp-baseline-260623.json`
  - `tmcp-benchmark/runs/raw/realpair-bidcamp-tmcp-cold-260623.json`
  - `tmcp-benchmark/runs/artifacts/realpair-bidcamp-tmcp-cold-260623/public-1.log`
- Root cause: the benchmark inventory previously treated every discovered Node script as a `pnpm` command. This pair was originally captured under the legacy local checkout label before correcting the repo identity to `BidCamp`, so the raw command logs still preserve the historical package/worktree strings emitted by the tool. The portable command-discovery layer emitted the wrong package-manager command for that checkout, and the run also exposed that isolated worktrees may lack installed dependencies.
- Patch: `services.tmcp_benchmark` now records `package_manager` from `packageManager` or lockfiles and emits `npm run <script>`, `yarn <script>`, or `pnpm <script>` accordingly. Preflight now accepts clean repos with any discovered quality command, not only test commands.
- Claim policy: this pair is failure evidence only. Do not use the aggregate report for performance claims until old dry-run records are separated from real-task records.
