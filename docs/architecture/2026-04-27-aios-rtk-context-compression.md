# AIOS RTK Context Compression Integration

Date: 2026-04-27

## Decision

Adopt RTK as an AIOS system primitive between command execution and agent ingestion.

Unified interface:

```text
rtk_run(command: string, mode: "compressed" | "raw" | "adaptive")
```

AIOS delegates to upstream `rtk` when it is installed and the command shape is supported. When `rtk` is absent, AIOS uses deterministic local compression with the same preservation contract and records comparable metrics.

## Context Waste Map

| Rank | Source | Entry point | Approx. token cost | Full fidelity |
|---:|---|---|---:|---|
| 1 | Runtime logs (`docker logs`, tails, hook logs) | Bash/PostToolUse, debugging workflows | 1k-50k | Optional; preserve errors, timestamps, repeats |
| 2 | Large diffs (`git diff`, `git show`) | Bash/PostToolUse, review workflows | 500-30k | Adaptive; raw for final patch review |
| 3 | Build logs (`pnpm build`, `next build`, Docker builds) | Bash/PostToolUse, CI simulation | 1k-20k | Optional; preserve errors/artifacts |
| 4 | Test output (`pytest`, Jest, Vitest, Playwright) | Bash/PostToolUse, quality gates | 500-12k | Optional unless failure ambiguous |
| 5 | Typecheck/lint (`tsc`, ESLint, ruff, pyright) | Bash/PostToolUse, quality gates | 300-8k | Optional; preserve file/rule/message |
| 6 | Exploration (`rg`, `find`, `ls`, `cat`) | Bash/PostToolUse, session packets | 200-15k | Optional; preserve paths and matches |
| 7 | Agent verbose summaries | Stop/handoff/writebacks | 300-5k | Optional; preserve decisions and evidence |

Repeated low-signal patterns: package-manager progress, successful test listings, git transfer progress, unchanged-file listings, duplicated stack frames, and full logs after the first actionable error.

## Integration Layer

Implemented surfaces:

- `services.rtk_integration.rtk_run()` runs commands and returns compressed output, raw path, exit code, and token estimates.
- `services.rtk_integration.compress_tool_output()` compresses existing hook tool responses.
- `bin/rtk-run.py` exposes the primitive for manual and workflow usage.
- `config/rtk/rules.json` is the runtime compression rules source.
- `rtk_compression_events` stores per-command compression telemetry.
- `workflow_metrics` receives `rtk.raw_tokens`, `rtk.compressed_tokens`, `rtk.tokens_saved`, and `rtk.token_reduction_percent`.

Compressed output must preserve:

- exit code
- errors and stack traces
- changed files
- failing tests
- key diff headers/hunks
- reproduction command
- raw tee path for failures

Compressed output reduces:

- repetitive logs
- successful test noise
- unchanged files
- boilerplate CLI output
- package-manager and git progress output

## Workflow Modes

| Workflow | RTK mode | Behavior |
|---|---|---|
| Code generation | compressed | Default concise command feedback |
| Test execution | adaptive | Preserve failures; tee raw output on ambiguity |
| CI/CD simulation | adaptive | Preserve failing gate and reproduction command |
| Debugging | adaptive | Expand ambiguous failures automatically |
| Refactoring | compressed | Keep changed files, diffs, and validation failures |
| Exploration | compressed | Keep paths/matches, collapse traversal noise |

## Hook Updates

- `SessionStart`: creates RTK schema, loads compression rules, and injects the active policy into the startup packet.
- `PostToolUse`: compresses Bash responses, records telemetry, and surfaces compressed high-signal output back into context.
- `Stop`: logs session-level RTK savings and stores the summary in the Stop event payload.

## Metrics Schema

```sql
CREATE TABLE rtk_compression_events (
  id TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(id),
  run_id TEXT REFERENCES orchestration_runs(id),
  workflow_key TEXT,
  source_kind TEXT NOT NULL,
  command TEXT,
  mode TEXT NOT NULL,
  effective_mode TEXT NOT NULL,
  exit_code INTEGER,
  raw_chars INTEGER NOT NULL,
  compressed_chars INTEGER NOT NULL,
  estimated_raw_tokens INTEGER NOT NULL,
  estimated_compressed_tokens INTEGER NOT NULL,
  token_reduction_percent REAL NOT NULL,
  ambiguous_failure INTEGER NOT NULL DEFAULT 0,
  raw_output_path TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
```

Tracked metrics:

- token reduction percentage
- raw/compressed token estimates
- tokens saved
- ambiguous failures
- per-workflow efficiency score
- existing success metrics remain in `workflow_metrics` for before/after comparison

## Example

Before:

```text
pytest -q
tests/test_a.py::test_one PASSED
tests/test_a.py::test_two PASSED
tests/test_b.py::test_bad FAILED
Traceback ...
AssertionError: expected 1 got 2
... hundreds of success/progress lines ...
```

After:

```text
$ pytest -q
exit_code=1

failing_tests_or_assertions:
- tests/test_b.py::test_bad FAILED
- AssertionError: expected 1 got 2

signal:
Traceback ...
File "tests/test_b.py", line 8, in test_bad

[raw output saved: ~/AIOS/logs/rtk-raw/..._pytest_-q.log]
```

## Failure Rules

- Non-zero exit with weak error signal is treated as ambiguous.
- Ambiguous adaptive runs tee raw output and expose the raw file path.
- Agents can request raw mode explicitly through `bin/rtk-run.py --mode raw -- <command>`.
- Compressed output never removes exit code, command, errors, stack traces, changed files, failing tests, or raw recovery path.

## Required File Changes

- Core: `services/rtk_integration.py`
- CLI: `bin/rtk-run.py`
- Config: `config/rtk/rules.json`
- Hooks: `bin/hook-session-start.py`, `bin/hook-post-tool-use.py`, `bin/hook-stop.py`
- Pipeline: `bin/aios-pipeline.py`
- Schemas: `schema.sql`, `aios-ui/server/aios/schema.ts`
- UI: `aios-ui/server/routers/costs.ts`, `aios-ui/app/costs/page.tsx`, `aios-ui/lib/types.ts`
- Tests: `tests/test_rtk_integration.py`, `tests/test_aios_cli.py`

## Risk Assessment

- Over-compression: mitigated by mandatory preservation rules and raw tee files for failures.
- False confidence: ambiguous failures force adaptive expansion.
- Upstream absence: local compression keeps AIOS functional until `rtk` is installed.
- Hook limitations: PostToolUse cannot erase context already emitted by some agent runtimes, but it controls AIOS durable ingestion and injects compact replacement context.
- Metric quality: token counts are estimates; they are stable enough for trend and reduction scoring.
