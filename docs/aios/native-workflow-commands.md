# Native Workflow Commands

AIOS native workflow commands are local-first command surfaces for common agent work. They are not plugin clones and do not require second-brain context by default. The machine-readable safety contract lives in `config/commands/native-workflow-commands.json`.

## Commands

### `aios zoom-out`

- Use for: orienting on an unfamiliar file, directory, or module before editing.
- Do not use for: proving behavior or replacing tests.
- Safety class: `read_only`.
- Writes: none.
- Second-brain behavior: disabled by default.
- Sub-agent or reviewer lanes: none in the MVP.
- Example: `aios zoom-out services/native_commands.py`
- Output includes: purpose, system position, inbound/outbound dependencies, sibling modules, conventions, vocabulary, risks, and next context.

### `aios handoff`

- Use for: compact continuation context at a pause point or handoff boundary.
- Do not use for: hiding unresolved blockers or replacing a verification report.
- Safety class: `artifact_write`.
- Writes: preview by default; explicit output paths are limited to planning or docs handoff locations.
- Second-brain behavior: disabled by default.
- Sub-agent or reviewer lanes: suggested next-agent context only.
- Example: `aios handoff --objective "Continue native command docs" --test "uv run pytest -q tests/test_native_commands.py"`
- Output includes: goal, current state, branch/workspace status, files touched, decisions, tests, worked paths, failed paths, blockers, references, and next actions.

### `aios review squad`

- Use for: read-only multi-lane review over a diff or selected files.
- Do not use for: automatic patching or speculative style-only criticism.
- Safety class: `read_only`.
- Writes: none.
- Second-brain behavior: disabled by default.
- Reviewer lanes: security, correctness, testing, architecture, maintainability, and project alignment.
- Example: `aios review squad --file services/native_commands.py`
- Output includes: severity-grouped findings, lane evidence, recommended fixes, confidence, and non-issues checked.

### `aios audit security`

- Use for: targeted security review of risky or privacy-sensitive work.
- Do not use for: generic checklist output without affected files and concrete scenarios.
- Safety class: `read_only`.
- Writes: none.
- Second-brain behavior: disabled by default.
- Reviewer lanes: security only.
- Example: `aios audit security --mode practical --file services/native_commands.py`
- Strict mode: reports critical/high findings.
- Practical mode: reports critical/high/medium findings relevant to local automation, auth, privacy, data handling, secrets, dependencies, and filesystem access.

### `aios cleanup de-slopify`

- Use for: conservative cleanup planning and low-risk formatting cleanup.
- Do not use for: broad rewrites, public API removal, config-key changes, or behavior changes.
- Safety class: `guarded_modify`.
- Writes: plan-only by default; `--apply` only applies low-risk format-only cleanup.
- Second-brain behavior: disabled by default.
- Reviewer lanes: maintainability and test quality by inspection.
- Example: `aios cleanup de-slopify --file services/native_commands.py`
- Output includes: cleanup plan, proposed changes, applied changes, skipped risky changes, checks, and rollback.

### `aios prototype`

- Use for: isolated experiments for uncertain design ideas.
- Do not use for: production implementation or unreviewed code promotion.
- Safety class: `sandbox_write`.
- Writes: only under explicit prototype/sandbox locations such as `.planning/prototypes/`, `prototypes/`, or `/private/tmp`.
- Second-brain behavior: disabled by default.
- Sub-agent or reviewer lanes: none in the MVP.
- Example: `aios prototype --question "Can this parser shape work?" --sandbox-path .planning/prototypes/parser-spike`
- Output includes: question tested, location, experiment, result, proof boundaries, recommendation, promotion steps, and cleanup instructions.

## Metadata Logging

All native commands support optional local metadata logging:

```bash
aios zoom-out services/native_commands.py --log-metadata --metadata-log-path .aios/native-command-metadata.jsonl
```

Metadata logging is local JSONL only. It can include command name, timestamp, repo, branch, scope, safety class, read-only/modifying status, reviewer lanes, files touched, tests run, pass/fail status, confirmation fields, run/session IDs, model/reasoning labels, token/cost estimate, and runtime. It does not send external telemetry.

## Recommended Workflows

### Unfamiliar Code

1. `aios zoom-out`
2. Implement the task.
3. `aios review squad`
4. `aios cleanup de-slopify`
5. Run tests.
6. `aios handoff`

### Risky Or Security-Sensitive Work

1. `aios zoom-out`
2. Implement the task.
3. `aios audit security --mode practical`
4. `aios review squad`
5. Run tests.
6. `aios handoff`

### Uncertain Design Ideas

1. `aios prototype`
2. Review the result.
3. Promote only if useful.
4. Implement the production version separately.
5. `aios review squad`

## Safety Notes

- Read-only commands must not modify files.
- Modifying commands are guarded by explicit mode or sandbox path.
- Prototype output is disposable until promoted through a separate reviewed change.
- De-slopify must list risky structural cleanup separately instead of applying it.
- Second-brain context is off by default; repo-local evidence is the first source.
