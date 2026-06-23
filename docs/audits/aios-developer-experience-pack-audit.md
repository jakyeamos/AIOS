# AIOS DX Pack Audit

Date: 2026-06-23

## Existing Relevant Infrastructure

- Skills and harvested agent material live in `config/workflows/skills.json`, `skills-library/`, `.cursor/skills/`, and the global skill stores outside this repo. `services/skills_harvest.py` already classifies agent, workflow, prompt, TMCP, docs, testing, debugging, and implementation source material.
- Governed workflows live in `config/workflows/registry.json` and load through `services/workflow_orchestration.py`. Existing active or candidate workflows include `implementation-delivery`, `audit-and-implement`, `standards-backfill`, `security-review`, `audit-only`, and behavioral/spec verification.
- Prompt templates live in `prompts/registry.json` with template bodies under `prompts/`. Current templates cover coding debug, research, reasoning, content writing, summarization, and behavioral spec verification.
- Routing rules are split across `services/task_routing.py`, `services/workflow_orchestration.py`, `config/execution-strategies/model-routing-policy.json`, `config/execution-strategies/task-specs.json`, and `config/execution-strategies/strategies.json`.
- Telemetry and evidence surfaces include orchestration runs, workflow learning events, success criteria evaluations, evidence artifacts, verifier artifacts, retrospective artifacts, model-selection records, and shadow branch metadata in `schema.sql` plus service helpers.
- Eval specs live under `docs/aios/harness-eval/config.json`, `tests/fixtures/harness-eval/`, `services/harness_eval.py`, `services/eval_run_service.py`, `services/second_brain_eval.py`, and `config/agent-eval/ablation-policies/`.
- Shadow-branch testing logic lives in `services/shadow_branch_runner.py`, `services/shadow_automation.py`, `services/shadow_candidate_scorer.py`, `tests/test_shadow_branch_runner.py`, and `tests/test_shadow_branch_cli.py`.
- Second-brain integration and parity logic live in `tools/context-compile.mjs`, `aios/context/**`, `services/second_brain_eval.py`, retrieval policy configs, context manifests, and ablation policies such as `no-second-brain`.
- Documentation conventions live in `README.md`, `docs/workflows/`, `docs/audits/`, `docs/specs/`, `docs/evals/`, `docs/quality/`, and `.planning/phases/**`.
- Quality gates live in `config/quality-gates.json`, `services/quality_gates.py`, `services/success_criteria.py`, `config/success-criteria/registry.json`, `config/quality-pipeline.json`, and commit-ladder helpers.

## Existing Equivalents

| Desired DX capability | Existing equivalent | Decision |
| --- | --- | --- |
| DX optimizer | `standards-backfill`, quality gates, success criteria, project health/delta context, `docs/quality/**` | Extend with DX metrics and friction outputs; do not create a standalone optimizer agent. |
| Interface DX reviewer | `audit-only`, `audit-and-implement`, API/contract success criteria, operator-search/contract audit surfaces | Add interface-focused workflow/prompt bindings and schemas instead of a parallel review system. |
| Documentation writer | `content_writing`, `summarization`, docs conventions, context compiler receipts, quality docs | Add developer-doc output contracts and validation expectations; avoid marketing-doc defaults. |
| Security reviewer | Existing `security-review` workflow and `security-review` success criterion | Reuse directly and add DX-specific trigger/mode metadata only where needed. |
| TypeScript specialist | UI TypeScript conventions, `aios-ui` lint/typecheck, execution strategy specialist role | Add targeted routing metadata; invoke only for TS public API, strictness, package boundary, or typecheck complexity. |
| Spec-fidelity coder | `implementation-delivery`, `audit-and-implement`, behavioral spec verification, success criteria gates | Extend task-family/contracts for spec extraction, assumption logging, small diffs, and acceptance mapping. |
| Agent routing | `task_routing.py`, workflow registry applicability, model-routing policy, orchestrated sub-agent standard | Add DX routing categories and mode decisions; keep model/reasoning dynamic. |
| Model escalation | `config/execution-strategies/model-routing-policy.json`, Phase 16 model-selection records | Reuse model-selection telemetry and avoid hardcoded model-per-agent defaults. |
| Quality gates | `quality_gates.py`, success criteria registry, commit ladder, evidence/verifier artifacts | Add DX-specific checks or eval fixtures only where existing gates cannot express the need. |

## Gaps

- No first-class DX capability pack contract exists with capability IDs, modes, trigger criteria, output schemas, and evidence expectations.
- No DX metrics schema currently records clone-to-run time, setup time, dev server startup, hot reload feedback, validation command count, README quickstart presence, or setup validation presence.
- Existing workflow routing does not yet distinguish compact DX audit, full DX audit, review-only interface/security/docs modes, or spec-fidelity implementation mode.
- Existing prompt templates can support docs/research/reasoning, but no developer-doc template contract enforces authentic setup, commands, limitations, and validation evidence.
- TypeScript specialization is present as a model-routing specialty concept, but not as a concrete workflow skill/capability with strict invocation discipline.
- Shadow/harness fixtures exist, but none are DX-specific poor onboarding, public CLI change, or TypeScript package-boundary scenarios.
- Second-brain parity exists at the context/eval layer, but DX pack behavior still needs explicit with-second-brain and repo-only fallback expectations.
- Developer-facing API/CLI/config error review is not a named reusable output schema.

## Reuse Opportunities

- Add DX capability metadata to `config/workflows/skills.json` and workflow stages in `config/workflows/registry.json` instead of adding static always-loaded agent files.
- Extend `config/execution-strategies/model-routing-policy.json` with DX routing categories and use Phase 16 `model_selection_records` for inspection.
- Use `services/workflow_orchestration.py` stage bindings for required outputs, prompt bindings, standards bindings, evidence, and verifier gates.
- Use `services/success_criteria.py` and `config/success-criteria/registry.json` for DX blocker/warning criteria rather than embedding pass/fail rules in prompt prose.
- Use `services/harness_eval.py`, `tests/fixtures/harness-eval/`, and `services/second_brain_eval.py` for DX eval fixtures and second-brain/no-second-brain parity.
- Use `services/shadow_branch_runner.py` parity metadata for before/after DX comparisons and replay instructions.
- Use `docs/audits/`, `docs/specs/`, and `.planning/phases/17-*` for reviewable design artifacts before promoting any prompt, skill, or workflow default.
- Use `tools/context-compile.mjs` context manifests to show which repo docs, prior decisions, or second-brain sources informed a DX run.

## Proposed Files to Add or Modify

- `docs/specs/developer-experience-capability-pack.md`: capability contract, modes, outputs, assumptions policy, and evidence expectations.
- `config/workflows/skills.json`: DX optimizer, interface reviewer, documentation writer, TypeScript specialist, and spec-fidelity capability metadata.
- `config/workflows/registry.json`: workflow stages or applicability for compact/full DX audit, review-only, and spec-fidelity implementation modes.
- `prompts/registry.json` and targeted `prompts/*.md`: only small prompt bindings where existing research/reasoning/content/coding templates are insufficient.
- `config/execution-strategies/model-routing-policy.json`: DX routing categories and escalation rules; no fixed model-per-agent mapping.
- `services/execution_strategy.py` or a small adjacent DX metrics service: persist measurable DX metrics where telemetry supports it.
- `services/harness_eval.py`, `docs/aios/harness-eval/config.json`, and `tests/fixtures/harness-eval/`: add DX eval fixtures.
- `services/aios_cli.py`: expose DX audit/report payloads only after the underlying contract exists.
- `docs/workflows/developer-experience-pack.md`: operator-facing usage, overrides, parity, and validation workflow.

## Risks

- Static-agent duplication: adding six large always-loaded agent files would violate the TMCP goal of thin default context and intent-specific loading.
- Prompt bloat: stuffing DX behavior into broad prompts would make routing less auditable and harder to evaluate.
- Checklist bloat: security, docs, and TypeScript review can become generic if not tied to concrete repo evidence and trigger conditions.
- Model overuse: a fixed strong model for every DX capability would conflict with the model-routing policy and Phase 16 model-selection telemetry.
- Peer-run leakage: second-brain conventions must improve local runs without becoming required for portable peer evals.
- Parallel quality systems: DX checks should plug into success criteria, quality gates, and harness evals instead of creating a second gate stack.
- Ambiguous ownership: DX metrics must declare whether they are measured, inferred, or unavailable instead of blending them in prose.

## Implementation Plan

1. Define a machine-readable DX capability contract with six capability IDs, modes, triggers, schemas, assumptions policy, evidence expectations, and always-loaded versus intent-specific placement decisions.
2. Add workflow/skill metadata for the capabilities using existing registries and stage bindings; keep prompt edits minimal and intent-specific.
3. Add measurable DX metric capture with explicit unavailable states for metrics the local harness cannot observe.
4. Add routing and model/reasoning categories for compact audit, full audit, review-only, implementation, TypeScript specialist, and security-sensitive cases.
5. Add second-brain parity behavior and DX eval fixtures for poor onboarding, public CLI/interface change, and TypeScript package boundary change.
6. Document usage, overrides, shadow-branch support, validation commands, and final report format after the executable contract exists.

## Capability Map

- DX Optimizer: reuse standards, quality, context, and eval surfaces; gap is DX-specific metric schema and prioritization output.
- Interface DX Reviewer: reuse audit workflows and success criteria; gap is API/SDK/CLI/config consumer-perspective schema.
- Documentation Writer: reuse content/summarization prompts and docs conventions; gap is developer-first docs contract with validation evidence.
- Security Reviewer: reuse `security-review`; gap is DX-specific trigger wiring and final output shape.
- TypeScript Specialist: reuse specialist role and UI TypeScript conventions; gap is targeted invocation metadata and TS-specific output schema.
- Spec-Fidelity Coder: reuse implementation workflows and behavioral spec verification; gap is explicit PRD/ADR/issue extraction and acceptance mapping mode.
