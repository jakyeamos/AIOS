# Codex AIOS Command Trigger Summary

Date: 2026-06-23

## Result

Codex can now route tasks through AIOS from an explicit command prefix.

Use:

- ordinary prompts for normal Codex work with automatic AIOS shadow evidence
- `/aios ...` when the AIOS route and packet should govern the baseline task
- `/aios-route-only ...` only when a routed record is needed without a shadow lane

`scripts/codex-aios-shadow.py` is the default helper for ordinary tasks and `/aios` tasks. `/aios` passes `--governed-route`; ordinary tasks leave the AIOS route as evidence only. `scripts/codex-aios-route.py` remains available for `/aios-route-only`; it infers the active project from the current working directory, creates a routed AIOS run, and returns operator-search, daily-flow, and next-action inspection commands.

## Verification

```bash
uv run pytest -q tests/test_codex_aios_route.py
python3 scripts/codex-aios-route.py "Verify the Codex AIOS prompt trigger helper" --db /tmp/aios-field-pressure.db --cwd /Users/jakyeamos/AIOS
```
