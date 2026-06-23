# Phase 19 Plan 19-01 Summary: Native Command Pack Audit

## Completed Scope

- Added `docs/audits/aios-native-command-pack-audit.md`.
- Audited current command, skill, prompt, workflow, CLI, agent/sub-agent, model-routing, second-brain/context, and eval harness surfaces.
- Evaluated `squad-review`, `handoff`, `zoom-out`, `de-slopify`, `security-audit`, `prototype`, `codebase-rehab`, and `codebase-sweep`.
- Classified read-only, modifying/artifact-writing, confirmation-required, shadow-branch-required, and test-gated command classes.
- Recommended MVP order: `zoom-out`, `handoff`, `squad-review`, then `security-audit`, guarded `de-slopify`, sandboxed `prototype`, workflow-shaped `codebase-rehab`, and deferred `codebase-sweep`.
- Explicitly deferred `codebase-sweep` as default behavior.

## TMCP / Agent-Rule Placement Decision

No always-loaded agent files were edited. The command-pack audit is phase-specific planning context and belongs in `docs/audits/`, not an always-loaded rule. Later command rules should use thin pointers to command contracts rather than inlining full command behavior in agent defaults.

## Requirement Evidence

- `CMDP-01`: Complete. The audit determines where each candidate belongs and records safety, dependency, reuse, risk, and MVP placement decisions.

## Verification

- Candidate command coverage checked with `rg` for all eight candidate names.
- Safety sections checked with `rg` for read-only, modifying, confirmation, shadow branch, MVP order, and `codebase-sweep` deferral.
- `pnpm context:validate` -> passed.
- `git diff --check` -> passed.

## Next Plan

Proceed to Phase 19 Plan 19-02: command contracts and safety classes.
