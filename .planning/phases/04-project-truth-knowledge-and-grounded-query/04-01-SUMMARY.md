# 04-01 Summary: Truth Freshness and Governed Update Contract

## Result

AIOS now exposes project truth freshness and governed truth-update evidence through `aios truth-audit --json`.

## Shipped

- Added a truth audit CLI command with a default `PROJECT.md` truth authority and `--truth-file` override.
- Added required truth facet checks for goals, architecture, risks, completed work, unresolved deltas, next actions, and decisions.
- Connected truth review evidence to recent governed closeout reports and resumable run snapshots.
- Declared the governed truth contract: accepted truth comes from the truth file, proposed updates come from closeout and resume evidence, and important updates require review.
- Added regression coverage for the governed contract and missing-facet warning behavior.

## Verification

- `uv run pytest tests/test_aios_cli.py -q`
- `uv run ruff check services/aios_cli.py tests/test_aios_cli.py`

## Follow-Up

- Surface the truth audit in the operator UI alongside knowledge/project pages.
- Add durable proposal objects for truth updates instead of relying only on closeout and resume evidence previews.
