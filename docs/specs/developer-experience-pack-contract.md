# Developer Experience Pack Contract

Date: 2026-06-23

## Purpose

The Developer Experience pack is an intent-specific capability pack for improving how developers understand, run, validate, extend, and safely change a project. It extends AIOS registries and workflows instead of adding broad always-loaded agent instructions.

The executable subset lives in `config/developer-experience/capability-pack.json`.

## Loading Policy

- Keep global agent files thin.
- Load this pack only for DX, docs, interface, security-review, TypeScript-specialist, or spec-fidelity intents.
- Load the minimum context needed for the selected capability and mode.
- Do not hardcode a fixed model for any capability; use model-routing metadata and recorded model-selection evidence.
- Peer-run workflows must not depend on personal second-brain context.

## Modes

- `compact`: fast, bounded review of the highest-signal DX issues.
- `full_audit`: repo-level audit with metrics, risks, and prioritized remediation.
- `implementation`: scoped changes after requirements and acceptance criteria are clear.
- `review_only`: read-only review for interface, security, docs, TypeScript, or spec-fidelity risk.

## Capabilities

### dx_optimizer

Purpose: find and prioritize developer workflow friction across setup, local commands, validation, docs, and CI.

Responsibilities: audit setup and run paths, collect available DX metrics, identify quick wins and larger investments, and rank findings by developer impact and implementation risk.

Invoke when setup, onboarding, validation loops, or developer commands are slow, missing, or ambiguous. Avoid for isolated code fixes with no developer workflow impact.

Outputs: metrics, findings, quick wins, larger investments, and verification plan.

### interface_dx_reviewer

Purpose: review public APIs, SDKs, CLIs, config schemas, examples, errors, and migration paths from a developer-consumer perspective.

Responsibilities: map developer-facing surfaces, review naming and error clarity, check examples and migrations, and identify confusing or breaking interface behavior.

Invoke for public API, CLI, config schema, developer-facing error, or migration changes. Avoid for private refactors with no interface impact.

Outputs: surface map, findings, consumer examples, and recommended changes.

### docs_writer

Purpose: create or revise developer-first documentation that is accurate, practical, and validation-backed.

Responsibilities: write setup and usage docs, include working commands and limitations, remove marketing or placeholder prose, and document validation commands.

Invoke when README/docs are missing, stale, or affected by a feature/setup change. Avoid documenting unimplemented behavior.

Outputs: changed docs, commands documented, limitations, and validation evidence.

### security_reviewer

Purpose: perform contextual security review for permissions, secrets, auth, dependencies, tools, CI, logs, privacy, or network/file-system risk.

Responsibilities: identify concrete security surfaces, review secrets and permission boundaries, check logging/privacy risks, and recommend scoped mitigations.

Invoke for security-sensitive changes. Avoid generic checklist output that is not tied to repo evidence.

Outputs: security surfaces, findings, accepted risks, and recommended gates.

### typescript_specialist

Purpose: handle TypeScript-specific DX issues around strictness, inference, public types, package boundaries, and typecheck/build performance.

Responsibilities: review public TypeScript APIs and inferred types, inspect strict compiler or package-boundary issues, assess typecheck/build performance where measurable, and recommend focused type-level fixes.

Invoke for public TypeScript APIs, strict type errors, package boundaries, or typecheck performance issues. Avoid simple TypeScript edits without type-system risk.

Outputs: type surfaces, findings, typecheck commands, and recommended changes.

### spec_fidelity_coder

Purpose: implement from PRDs, ADRs, design specs, issues, or acceptance criteria while preserving scope and logging assumptions.

Responsibilities: extract requirements and acceptance criteria, map files and tests, implement small scoped changes, and record assumptions, verification, and residual risk.

Invoke when implementation must trace back to a PRD, ADR, issue, design spec, or acceptance criteria. Avoid when the spec is missing or conflicting and no safe bounded assumption exists.

Outputs: requirements map, changed files, tests/checks, assumptions, and acceptance results.

## Metrics

Each DX run should record measured values where available and `not_measured` plus a future measurement method otherwise.

Required metric IDs:

- `clone_to_running_app`
- `setup_time`
- `dev_server_startup`
- `feedback_loop_speed`
- `unit_test_runtime`
- `typecheck_runtime`
- `lint_runtime`
- `build_runtime`
- `ci_runtime`
- `manual_setup_steps`
- `validation_command_count`
- `readme_quickstart_presence`
- `setup_validation_presence`
- `ambiguous_developer_instructions`
- `token_cost_and_agent_calls`

## Assumptions Policy

Capabilities may make bounded assumptions only when the assumption is low-risk, local, reversible, and explicitly logged. They must stop for destructive actions, security-sensitive uncertainty, data-loss risk, broad architecture changes, or approval-gated decisions.

## Evidence Expectations

Outputs must cite repo files, docs, configs, commands, observed timings, test output, typecheck output, interface examples, or recorded telemetry. Missing or unavailable evidence must remain visible.

## Second-Brain Behavior

When `second_brain_available` is true, the pack may use prior project conventions, known pain points, house style, and historical decisions as supporting context.

When `second_brain_available` is false, the pack must fall back to repo-local docs, configs, source, tests, and command evidence. Peer-run workflows must be valid in this mode.
