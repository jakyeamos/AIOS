# Developer Experience Pack

Status: draft capability pack
Config: `config/developer-experience/capability-pack.json`
Routing policy: `config/developer-experience/routing-policy.json`
Eval spec: `docs/evals/developer-experience-pack-eval.md`

## What It Does

The Developer Experience pack routes developer-usability work to six intent-specific capabilities:

- `dx_optimizer`: audits setup, local run paths, validation commands, feedback loops, and priority tradeoffs.
- `interface_dx_reviewer`: reviews public APIs, CLIs, config schemas, examples, errors, and migration paths from the consumer side.
- `docs_writer`: writes practical setup, usage, and validation docs from observed behavior.
- `security_reviewer`: reviews concrete shell, network, filesystem, auth, secret, dependency, CI, logging, privacy, or permission risk.
- `typescript_specialist`: reviews TypeScript API surface, strictness, inference, package boundaries, and build impact.
- `spec_fidelity_coder`: implements scoped changes against explicit requirements and records out-of-scope assumptions.

The pack is not a static prompt library. It is a routed capability contract: AIOS selects only the capabilities justified by the task, mode, risk, and evidence available.

## When Capabilities Run

Use `dx_optimizer` when onboarding, setup, local validation, or feedback-loop friction is the task.

Example: "Make this repo easier to clone, install, run, and verify locally."

Use `interface_dx_reviewer` when a developer-facing API, CLI, config schema, example, error, or migration behavior changes.

Example: "Review this CLI flag rename for naming, defaults, help text, errors, examples, and migration impact."

Use `docs_writer` when README, setup, usage, or validation docs are missing, stale, or changed by implementation.

Example: "Add the minimal quickstart and validation commands for this package."

Use `security_reviewer` only when the task touches a concrete risky surface: shell execution, network access, filesystem mutation, secrets, auth, permissions, dependencies, CI, logs, privacy, or destructive operations.

Example: "This setup command downloads and executes a script; review the risk and document the safe path."

Use `typescript_specialist` only for TypeScript surfaces where types matter: public package APIs, strictness, inference, exported contracts, package boundaries, or build/typecheck behavior.

Example: "Change this exported TypeScript package API and preserve inference for consumers."

Use `spec_fidelity_coder` when the task asks for implementation against a spec or acceptance criteria.

Example: "Implement exactly this CLI behavior and do not broaden the feature."

## Modes

- `compact_audit`: quick top-findings pass for small docs or single-surface work.
- `full_audit`: repo-level DX audit with metrics, risks, and prioritized remediation.
- `implementation`: scoped file changes after acceptance criteria are clear.
- `review_only`: read-only interface, security, docs, or TypeScript review.

The selected mode and reasoning level come from `config/developer-experience/routing-policy.json`, then model tier is selected dynamically by `config/execution-strategies/model-routing-policy.json`. The pack does not assign fixed models to fixed capabilities.

## Shadow Branch Support

The pack is compatible with AIOS shadow-branch evaluation. A candidate run should record:

- task prompt and acceptance criteria
- selected DX capabilities and skipped nearby capabilities
- second-brain mode
- changed files and diff size
- validation commands and results
- before/after metrics or explicit `not_measured` reasons

Use shadow branches when a DX routing or implementation strategy needs comparison against baseline behavior without contaminating the active branch.

## Second-Brain Behavior

With second-brain context available, AIOS may use prior project conventions, known pain points, and local preferences as supporting context.

Without second-brain context, the pack must still work from repo-local files, configs, docs, tests, and explicit assumptions. Peer or portable runs must not require private personal corpus context.

## Metrics

Record measurements when available:

- clone-to-run or setup time
- dev-server startup time
- feedback-loop latency
- test, typecheck, lint, build, or CI runtime
- manual setup step count
- validation command count
- README quickstart presence
- setup validation presence
- ambiguous instruction count
- token cost and agent calls when telemetry exists

When a metric cannot be measured, record `not_measured` with a concrete reason.

## Override And Disable

Override a recommendation by choosing a narrower mode, removing a capability from the task plan, or recording an accepted tradeoff in the run artifact.

Disable second-brain influence by running the task in repo-only or peer-portable context. The expected fallback is repo-local evidence, not a blocked run.

Skip `security_reviewer` when there is no concrete risky surface. Skip `typescript_specialist` when there is no TypeScript API, type, package-boundary, or build/typecheck concern.

## Inspection Commands

Inspect the capability pack:

```bash
uv run python bin/aios.py --json dx-pack
```

Include the final report template:

```bash
uv run python bin/aios.py --json dx-pack --report-template
```

Run the harness eval suite:

```bash
uv run python bin/aios.py --json harness-eval run --config docs/aios/harness-eval/config.json
```

Validate context configuration:

```bash
pnpm context:validate
```

Run focused Python checks for the current DX pack surfaces:

```bash
uv run pytest -q tests/test_workflow_orchestration.py tests/test_execution_strategy.py tests/test_harness_eval.py tests/test_aios_cli.py
uv run ruff check services/workflow_orchestration.py services/execution_strategy.py services/harness_eval.py services/aios_cli.py tests/test_workflow_orchestration.py tests/test_execution_strategy.py tests/test_harness_eval.py tests/test_aios_cli.py
```

`tests/test_aios_cli.py` may include unrelated historical failures when run as a full file in some local states. For DX pack report-format validation, the focused assertion is `test_dx_pack_report_template_matches_required_closeout_sections`.

## Eval Coverage

DX eval coverage is defined in `docs/evals/developer-experience-pack-eval.md` and loaded from `config/agent-eval/developer-experience-fixtures.json`.

The required fixtures are:

- poor onboarding repo
- public CLI change
- TypeScript package boundary change

Each fixture must run with second-brain context available and unavailable. The fixtures verify routing, metrics, README clarity, interface review, contextual security, TypeScript invocation discipline, assumption logging, small diffs, and before/after metric recording.

## Implementation Report

Use this format after changing the DX pack:

```md
## Developer Experience Pack Implementation Report

### Summary
### Files Added
### Files Modified
### Capabilities Added
### Routing Changes
### Eval Coverage
### Validation Results
### Assumptions Made
### Known Limitations
### Recommended Next Steps
```

The same template is available through `aios dx-pack --report-template`.

## Known Limitations

- Most timing metrics are measured only when commands are known and runnable in the local environment.
- The pack records `not_measured` instead of inventing setup, CI, or cost metrics.
- Security review is contextual and does not replace a full threat model for release-critical surfaces.
- TypeScript review is targeted to type/API/build risk and should not be invoked for unrelated docs or non-TypeScript work.
- The fixture registry validates expected scenarios and routing discipline; it does not execute live model rollouts.
