---
id: behavioral_spec_verification
name: Behavioral Spec Verification
version: "1.0"
classification: plan
tags:
  - behavioral
  - verification
  - rehabilitation
  - spreadsheet
  - regression
purpose: Run a gated mature-repo behavioral spec verification loop with a canonical spreadsheet, evidence-backed testing, defect remediation, regression coverage, and complexity review.
when_to_use: Use for mature repos where exhaustive behavioral verification and rehabilitation are worth the cost.
when_not_to_use: Do not use for small prototypes, early experiments, low-surface-area repos, or narrow bug fixes.
required_inputs:
  - repo_path: Current repository path.
  - maturity_report: Eligibility report explaining the maturity signals.
optional_inputs:
  - manual_override: Explicit operator opt-in for mature repo rehabilitation.
output_contract: Produce one canonical behavioral-spec.xlsx plus a final report with feature counts, defect outcomes, regression coverage, commands, skipped tests, remaining risk, and complexity gate result.
eval_criteria:
  - The canonical spreadsheet remains single-writer and unforked.
  - Verified rows have source citations, command/action evidence, observed result, iteration, and last tested commit.
  - Regression-Covered rows have automated coverage or documented infeasibility.
  - Fixes reuse thermo-nuclear-simplification as the complexity gate.
owner: jakyeamos
last_updated: "2026-06-23"
lifecycle_state: candidate
applicability:
  - mature_repo_rehabilitation
last_evaluated_at: "2026-06-23T00:00:00Z"
changelog:
  - version: "1.0"
    date: "2026-06-23"
    note: Initial candidate prompt for the mature-repo behavioral verification workflow.
---

# Behavioral Spec Verification

## Goal

Produce a verified, code-derived behavioral spec for a mature web platform, captured in one canonical spreadsheet that carries every feature from spec to tested to fixed to verified to regression-covered.

## Operating Rules

- Work on the current repo.
- Keep exactly one canonical `.xlsx` as the source of truth.
- Derive expected behavior from code citations, not guesses.
- Test every story with the strongest available method.
- Fix only logged defects.
- Re-test fixed and adjacent stories.
- Add regression coverage for fixed functional or logistical defects.
- Reuse `thermo-nuclear-simplification` as the complexity gate.
- Stop a failing story after three full fix/re-test iterations and preserve evidence.

## Checkpoints

Checkpoint only when an action is destructive or irreversible, a fix requires a genuine product decision, required input can only come from the user, or a story has failed after the safety cap and needs escalation.

Otherwise continue autonomously through plan, catalog and spec, coverage audit, test, fix, re-test, regression-cover, boundary audit, and final report.
