# Codex AIOS Automatic Shadow Summary

Date: 2026-06-23

## Result

Codex now creates a shadow AIOS lane automatically for every non-trivial task.

Use:

```text
Fix the scoped task and verify the checks
```

`scripts/codex-aios-shadow.py` is the default helper. It preserves the current workspace as the baseline, records an AIOS route, creates an isolated `.aios/shadow-worktrees/` worktree unless `--no-worktree` is passed, and prints the prompt to run in a separate Codex thread.

For ordinary prompts, the AIOS route is evidence only and does not govern the baseline. For `/aios` prompts, Codex passes `--governed-route` and treats the AIOS route and packet as authoritative context.

Shadow output is comparison evidence only until explicitly reviewed and promoted.

## Verification

```bash
uv run pytest -q tests/test_codex_aios_shadow.py
python3 scripts/codex-aios-shadow.py "Verify shadow prompt helper" --db /tmp/aios-field-pressure.db --cwd /Users/jakyeamos/AIOS --no-worktree
python3 scripts/codex-aios-shadow.py "Shadow smoke test for Codex AIOS helper after branch namespace fix" --db /tmp/aios-field-pressure.db --cwd /Users/jakyeamos/AIOS
```

The real worktree smoke requires normal Git ref permissions because `git worktree add` writes under `.git`. The smoke worktree and branch were removed after verification.
