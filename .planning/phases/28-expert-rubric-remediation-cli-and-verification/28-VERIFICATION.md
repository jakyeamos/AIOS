# Phase 28 Verification - Expert Rubric Remediation CLI And Verification

Date: 2026-06-24
Phase: `28-expert-rubric-remediation-cli-and-verification`
Verdict: passed for the read-only expert review-plan workflow, with existing repo quality caveats carried forward.

## Scope

Phase 28 exposed `expert_rubric_remediation_v1` through `aios tmcp review-plan`, recorded focused quality evidence, updated project truth, and smoke-tested the original Soundscape visual-polish use case. The delivered workflow compiles TMCP expertise, builds a rubric, audits supplied evidence, creates ordered remediation slices, and writes an approval-gated implementation handoff. It does not implement remediation slices.

## Plan Completeness

| Check | Result |
| --- | --- |
| Plan summaries | Pass: `28-01-SUMMARY.md` and `28-02-SUMMARY.md` are present; `28-03-SUMMARY.md` is created after this verification ledger. |
| Roadmap state before final summary | Phase 28 shows 2/3 plans executed and active Plan 28-03. |
| AIOS working tree before verification doc | `git status --short` returned no output before this file was created. |

## Smoke Command

```bash
uv run python bin/aios.py --json tmcp review-plan "Review Soundscape UI polish with TMCP expertise and create a rubric remediation plan" --project-path /Users/jakyeamos/projects/soundscape-app --output-dir /tmp/aios-expert-review-smoke --evidence-json '{"dimension_id":"data_realism","severity":"blocker","summary":"Feed waveform uses random visual data.","evidence":["packages/web/src/components/feed/FeedItem.tsx:427"],"recommended_fix":"Derive waveform heights from stable input."}' --selected-slice-id slice-1
```

Result: pass, exit 0.

Output summary:

| Field | Value |
| --- | --- |
| `ok` | `true` |
| `command` | `tmcp-review-plan` |
| `workflow_key` | `expert_rubric_remediation_v1` |
| `run_id` | `tmcp-review-plan-9a0b3de6` |
| `status` | `completed` |
| `selected_slice_id` | `slice-1` |
| `requires_user_approval` | `true` |
| `follow_up_workflow` | `implementation-delivery` |

## Smoke Artifacts

`/tmp` resolves to `/private/tmp` on this macOS host. The smoke command wrote all artifacts under `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/`.

| Artifact | Path |
| --- | --- |
| Expertise packet | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/expertise-packet.json` |
| Rubric JSON | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/rubric.json` |
| Rubric Markdown | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/rubric.md` |
| Audit report JSON | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/audit-report.json` |
| Audit report Markdown | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/audit-report.md` |
| Remediation plan JSON | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/remediation-plan.json` |
| Remediation plan Markdown | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/remediation-plan.md` |
| Implementation handoff JSON | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/implementation-handoff.json` |
| Implementation handoff Markdown | `/private/tmp/aios-expert-review-smoke/.aios/reviews/tmcp-review-plan-9a0b3de6/implementation-handoff.md` |

Artifact existence check:

```bash
find /tmp/aios-expert-review-smoke -maxdepth 5 -type f | sort
```

Result: pass, all nine expected artifact files exist.

## Validation Status

| Validation key | Result |
| --- | --- |
| `tmcp_packet_compiled` | Pass |
| `tmcp_packet_compiled` | Pass |
| `rubric_dimensions_present` | Pass |
| `findings_have_evidence` | Pass |
| `remediation_has_verification` | Pass |

The duplicate `tmcp_packet_compiled` validation is present in runtime output and is non-blocking for Phase 28 because both entries passed with empty issue arrays.

## Generated Review Content

| Output | Evidence |
| --- | --- |
| Audit finding | `[blocker] Feed waveform uses random visual data. Evidence: packages/web/src/components/feed/FeedItem.tsx:427` |
| Remediation slice | `slice-1: Feed waveform uses random visual data.` |
| Target file | `packages/web/src/components/feed/FeedItem.tsx:427` |
| Expected impact | `Derive waveform heights from stable input.` |
| Verification instruction | `Run targeted tests or manual checks covering the cited evidence.` |
| Handoff boundary | Requires user approval and routes follow-up work to `implementation-delivery`. |

## Quality Evidence

| Check | Result |
| --- | --- |
| `uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_writes_expert_review_artifacts tests/test_aios_cli.py::test_tmcp_review_plan_rejects_malformed_evidence_json -q` | Pass: 2 tests. |
| `uv run ruff check services/aios_cli.py tests/test_aios_cli.py` | Pass. |
| `uv run ruff format --check services/aios_cli.py tests/test_aios_cli.py` | Pass after formatting during Plan 28-01. |
| `uv run pytest tests/test_aios_cli.py tests/test_workflow_orchestration.py tests/test_expert_rubric_remediation.py -q` | Fail: 8 existing broader `tests/test_aios_cli.py` failures; expert workflow regressions pass. |
| Focused Phase 26-28 Ruff check | Pass. |
| Focused Phase 26-28 Ruff format check | Pass. |
| Focused Phase 26-28 BasedPyright | Fail: existing `run_cli` complexity, existing `_dx_pack_payload` test helper mismatch, and pytest import warnings. |
| `uv run vulture . --min-confidence 70` | Pass. |
| `git diff --check .tracker/PROJECT_TRUTH.md` | Pass. |

## Post-Closeout Repo-Level Ladder

These commands ran after the Phase 28 metadata commits so the final project truth snapshot could reflect the current full-repo baseline.

| Check | Result |
| --- | --- |
| `uv run ruff check .` | Fail: 25 issues, including existing unused imports/variables, import ordering, `zip(strict=...)`, simplification, and ambiguous-name findings. |
| `uv run ruff format --check .` | Fail: 178 files would be reformatted; 135 files already formatted. |
| `uv run basedpyright` | Fail: 110 errors and 101 warnings, including existing `services/aios_cli.py` `run_cli` complexity. |
| `uv run vulture . --min-confidence 70` | Pass: exit 0 with no output. |
| `uv run pytest -q` | Fail: 11 failed and 950 passed. |

Pytest failure groups:

- 8 existing `tests/test_aios_cli.py` failures in learning analysis/proposal, contracts audit expectations, workflow learning payload, and skills harvest validation shape.
- 1 `tests/test_learning_analysis.py` dispatcher since-bound failure.
- 2 `tests/test_workflow_experiments.py` fixture commits blocked by the user commit quality gate requiring `.pre-cr.json`.

## Target Project Status Review

The target Soundscape repo was not clean before the smoke command; `git -C /Users/jakyeamos/projects/soundscape-app status --short` showed many pre-existing modified and untracked files. The smoke command was configured with `--output-dir /tmp/aios-expert-review-smoke`, and every reported artifact path is under `/private/tmp/aios-expert-review-smoke`, not under `/Users/jakyeamos/projects/soundscape-app`.

Because the target repo was already dirty, this verification does not claim a clean before/after mutation proof for Soundscape. It does verify the CLI's output location and confirms no review artifacts were written into the target project path.

## Requirements Verified

| Requirement | Evidence |
| --- | --- |
| Operator can run a read-only review-plan command against Soundscape | Smoke command exited 0 with `ok: true`. |
| CLI emits structured JSON for workflow metadata and artifacts | Output includes schema, workflow key, run id, status, validation list, artifact paths, remediation slices, and implementation handoff. |
| Artifacts are written under caller output directory | All nine artifact paths are under `/private/tmp/aios-expert-review-smoke`. |
| Evidence-backed remediation slice is generated | `slice-1` cites `packages/web/src/components/feed/FeedItem.tsx:427` and carries the supplied recommended fix as expected impact. |
| Handoff is approval-gated and non-implementing | `requires_user_approval: true`; follow-up workflow is `implementation-delivery`. |
| Known repo-level quality caveats are preserved | `.tracker/PROJECT_TRUTH.md` and `28-02-SUMMARY.md` record broader CLI pytest and BasedPyright failures. |

## Threat Mitigations

| Threat | Mitigation Evidence |
| --- | --- |
| Smoke output could be untraceable | Exact command, run id, validation keys, and artifact paths are recorded in this ledger. |
| Target project could be mutated during review planning | CLI wrote artifacts to `/tmp`; target project path was used only for TMCP packet compilation. |
| Handoff could imply implementation already happened | Handoff explicitly requires user approval and names `implementation-delivery` as the follow-up workflow. |
| Focused pass results could hide repo baseline debt | Quality evidence records both passing expert-workflow checks and existing broader failures. |

## Residual Risks

- Full AIOS repo-level quality remains non-green; Phase 28 did not remediate the existing broader CLI pytest or BasedPyright baseline issues.
- The latest full repo-level ladder also reports Ruff and format baseline failures outside the expert workflow slice.
- Soundscape's target repo was already dirty, so mutation verification is limited to artifact-path inspection rather than a clean before/after git status proof.
- Review scope is bounded to supplied evidence. A real remediation run should inspect neighboring call sites around `FeedItem.tsx:427` before editing.

## Operator Handoff

The first-class workflow is ready for operator use as a review-plan generator:

1. Run `aios tmcp review-plan` with an objective, target project path, output directory, and concrete evidence JSON.
2. Review `audit-report.md`, `remediation-plan.md`, and `implementation-handoff.md` under the generated review directory.
3. Approve a selected remediation slice explicitly.
4. Execute implementation in a separate `implementation-delivery` workflow.

Next action: use the workflow on the full Soundscape visual-polish evidence set, then address the existing AIOS CLI pytest and BasedPyright baseline failures tracked in `.tracker/PROJECT_TRUTH.md`.

## Closeout

Phase 28 passes its functional validation contract. The feature is complete as a read-only expert rubric remediation planning workflow; implementation of remediation slices remains intentionally out of scope.
