# Quality Runner Adoption

Quality Runner is a standalone audit-and-plan package with CLI and MCP surfaces.
AIOS invokes the latest repository source through the source-first tool contract;
it does not depend on a local QR checkout path. AIOS retains the QR Git source
as its compatibility-module dependency for existing evidence and gate adapters.

AIOS should consume Quality Runner as an external tool. AIOS may provide
adapters, standards profiles, or workflow shortcuts, but the standalone package
owns the core workflow and `.quality-runner/` artifact contract.

The default latest-source command is:

```bash
uvx --refresh \
  --from git+https://github.com/jakyeamos/quality-runner.git \
  quality-runner run /path/to/repo --profile jakyeamos --json
```

For local QR development, set `QUALITY_RUNNER_MODE=local` and
`QUALITY_RUNNER_REPO=/path/to/quality-runner` before invoking AIOS.

Initial MCP tool:

```text
quality_runner_run
```
