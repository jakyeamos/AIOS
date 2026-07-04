# Quality Runner Adoption

Quality Runner lives in `/Users/jakyeamos/quality-runner` as a standalone
audit-and-plan package with CLI and MCP surfaces.

AIOS should consume Quality Runner as an external tool. AIOS may provide
adapters, standards profiles, or workflow shortcuts, but the standalone package
owns the core workflow and `.quality-runner/` artifact contract.

Initial command:

```bash
quality-runner run /path/to/repo --profile jakyeamos --json
```

Initial MCP tool:

```text
quality_runner_run
```
