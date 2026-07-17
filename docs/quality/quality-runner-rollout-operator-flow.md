# Quality Runner Rollout Operator Flow

AIOS launches the external Quality Runner multi-repo rollout workflow through:

```bash
uv run python bin/aios.py --json quality rollout \
  --repo /Users/jakyeamos/projects/example-repo \
  --run-id-prefix aios-rollout-20260704 \
  --verify-timeout-seconds 180 \
  --total-timeout-seconds 300
```

For batches, pass a text or JSON repo list as the positional argument, or repeat
`--repo`. The repo list format is the Quality Runner `rollout` format, so AIOS
does not own a second parser contract.

## Artifact Capture

AIOS delegates execution to the Quality Runner CLI through the source-first tool
contract. The default invocation uses `uvx --refresh` against the QR Git
repository; `QUALITY_RUNNER_MODE=local` and `QUALITY_RUNNER_REPO` opt into a
specific local checkout for development. Quality Runner remains the source of
truth for:

- `rollout-ledger.json`
- `*-controller-report.json`
- `*-controller-report-validation.json`
- `per-repo-summaries/INDEX.md`
- `fleet-remediation-phases.md`

AIOS adds one index file beside those artifacts:

```text
~/AIOS/artifacts/quality-rollouts/<run-id-prefix>/aios-rollout-artifact-index.json
```

The index lists the rollout ledger, controller reports, validation artifacts,
per-repo Quality Runner artifact paths, and fleet documents. The CLI JSON output
returns the index path and the controller report paths directly.

## Evidence Logging

`aios quality rollout` records a durable evidence row in `~/AIOS/data/aios.db`
when the AIOS DB is available. Use `--task-id`, `--run-id`, or `--session-id` to
link that row to an existing AIOS run or operator session.

```bash
uv run python bin/aios.py --json evidence --run-id aios-rollout-20260704
```

The evidence row is a pointer record. The controller reports and rollout ledger
remain file artifacts under the rollout output directory.

## Operator Closeout

1. Run `aios quality rollout` with a stable `--run-id-prefix`.
2. Open the returned `artifact_index_path`.
3. Review rejected controller reports first.
4. Review `fleet-remediation-phases.md` for the next repo-local remediation
   batches.
5. Use `aios evidence --run-id <run-id-prefix>` to confirm AIOS captured the
   rollout evidence pointer.
