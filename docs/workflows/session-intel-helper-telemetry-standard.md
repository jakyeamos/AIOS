# Session Intelligence Helper Telemetry Standard

When session-intelligence helper families are relevant to a task, use the helper command surface instead of recreating equivalent ad hoc shell probes.

- Prefer `python bin/aios.py session-intel helper run --family <family> ...` for supported helper families so invocation telemetry is recorded.
- Use `python bin/aios.py session-intel helper list --json` before and after helper-heavy work when practical to confirm helper `telemetry_status` and `removal_status`.
- Do not use broad ad hoc commands merely because they are familiar when a helper family already covers the same evidence shape: `doc_excerpt`, `artifact_probe`, `repo_state`, `git_history`, `package_check`, `deployment_flow`, `bespoke_review`, or `workflow_skill`.
- If a helper is intentionally bypassed because it is slower, insufficient, too broad, or mismatched to the evidence need, record that with `python bin/aios.py session-intel helper bypass --family <family> --reason "<reason>"`.
- Do not manufacture failure or bypass telemetry in the live DB for testing. Use unit tests or a temporary DB for adverse telemetry paths; reserve live failure and bypass records for real operational outcomes.
- Treat Removal Candidates as telemetry-driven. A helper should move toward removal review only from recorded failures, bypasses, neutral value, or stale usage evidence, not from anecdote alone.
- When changing helper behavior, report the telemetry impact explicitly: invocation count, success/failure/bypass count, median latency if available, status transition, and candidate coverage.
