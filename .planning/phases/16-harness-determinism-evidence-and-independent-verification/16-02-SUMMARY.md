# Phase 16 Plan 16-02 Summary: Evidence Chain Hardening

## Completed

- Added `evidence_artifacts` as an additive durable schema in `schema.sql`.
- Added `services/evidence_artifacts.py` with schema installation, evidence recording, output hashing, freshness validation, usable-evidence filtering, and stable evidence refs.
- Wired `bin/hook-post-tool-use.py` to record Bash command evidence with run/session, command, exit code, raw output path/hash, status, and caveats.
- Wired `bin/hook-stop.py` to prefer fresh usable evidence artifact refs when building execution evidence for closeout.
- Added `aios evidence` in `services/aios_cli.py` for read-only run/session artifact inspection and validation output.
- Added optional commit-ladder evidence binding in `services/commit_quality_ladder.py`; missing fresh evidence is reported as `skip`/unknown, not pass.

## Verification

- `uv run pytest -q tests/test_evidence_artifacts.py tests/test_hook_stop.py tests/test_commit_quality_ladder.py`
- `uv run ruff check services/evidence_artifacts.py tests/test_evidence_artifacts.py tests/test_hook_stop.py tests/test_commit_quality_ladder.py services/commit_quality_ladder.py bin/hook-post-tool-use.py bin/hook-stop.py services/aios_cli.py`
- `uv run python -m services.aios_cli --db <tmpdb> --json evidence --limit 1`

## Requirement Coverage

- HARN-03 is complete.
- Empty marker and agent-authored pass claims downgrade to `unknown`.
- Freshness is checked against run/session identifiers when present.
- Command evidence includes output paths plus hashes when available, or explicit output absence caveats.
