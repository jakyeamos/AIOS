# Phase 19: Native Workflow Command Pack - Research

**Gathered:** 2026-06-01
**Status:** Ready for planning

<source_spec>
## Source Spec

Phase 19 is specified in the pasted "AIOS native workflow commands from claude-plugins/plugins/essentials" prompt ingested on 2026-06-01. The spec asks AIOS to audit and implement the strongest command patterns from the external essentials plugin as AIOS-native workflow commands and skills, without cloning the plugin.

The strongest first commands are `zoom-out`, `handoff`, and `squad-review` because they improve context efficiency, continuity, and review quality while remaining read-only by default. `de-slopify` and `prototype` are useful but require stronger guardrails because they can create or modify files.
</source_spec>

<domain>
## Phase Boundary

Phase 19 creates operator-facing native AIOS workflow commands. It is not a general DX pack, not a static skill import, and not a broad codebase sweep.

It overlaps earlier phases but has a distinct command-surface boundary:

- Phase 15 handles agent-facing skill portfolio integration, including handoff skill concepts.
- Phase 16 provides evidence, verifier, context manifests, and command metadata patterns this phase should consume.
- Phase 17 provides Developer Experience capability metadata for security/docs/interface behavior.
- Phase 18 provides review-first proposal patterns and safety around auto permissions.

Phase 19 focuses on CLI/workflow command contracts, output schemas, safety classes, command logging, tests, and docs.
</domain>

<requirements>
## Phase 19 Requirements

### CMDP-01: Native Command Architecture Audit
AIOS must audit current command, skill, prompt, agent, workflow, CLI, sub-agent, model-routing, second-brain, and eval harness architecture and decide where each candidate command belongs.

### CMDP-02: Command Contracts And Safety Classes
AIOS must define command names, input/output schemas, safety class, read-only/modifying behavior, second-brain usage, sub-agent/reviewer lane representation, validation gates, logging metadata, rollback expectations, and MVP implementation order.

### CMDP-03: Zoom-Out Command
AIOS must implement a read-only `aios zoom-out` command for files, directories, or modules that returns structured orientation: purpose, system position, inbound dependencies, outbound dependencies, sibling modules, conventions, domain vocabulary, risks, and next context to inspect.

### CMDP-04: Handoff Command
AIOS must implement a read-only or artifact-writing `aios handoff` command that creates compact continuation context: goal, current state, branch/workspace status, files touched, decisions, tests run, what worked, failed approaches, blockers, relevant references, and next actions.

### CMDP-05: Squad Review Command
AIOS must implement read-only `aios review squad` with security, correctness, testing, architecture, maintainability, and project-alignment reviewer lanes. It must support branch diff or selected file scopes, produce actionable severity-grouped findings, separate confirmed issues from speculation, and log enough metadata for later eval comparison.

### CMDP-06: Security Audit Command
AIOS must implement read-only `aios audit security` with `strict` and `practical` modes, branch diff and selected file scopes, contextual findings with severity, affected files, issue, exploit/failure scenario, recommended fix, confidence, non-issues checked, and verification suggestions.

### CMDP-07: Guarded Cleanup And Prototype Commands
AIOS must implement guarded `aios cleanup de-slopify` and sandboxed `aios prototype`. De-slopify must preserve behavior/public APIs, produce a cleanup plan, apply only low-risk cleanup, and run checks when available. Prototype must write only to explicit prototype/sandbox locations and include cleanup/promotion guidance.

### CMDP-08: Command Logging, Tests, And Documentation
AIOS must add lightweight command metadata logging for eval/shadow comparison, tests for registration/schema/read-only/safety behavior, and docs covering command purpose, when to use or avoid, safety class, sub-agent use, second-brain use, examples, outputs, and recommended workflows.
</requirements>

<plan_sequence>
## Recommended Plan Sequence

- **19-01**: Audit command/skill/workflow/CLI architecture and produce command-pack audit.
- **19-02**: Define command schemas, safety classes, output contracts, logging metadata, and implementation order.
- **19-03**: Implement read-only MVP commands: `zoom-out`, `handoff`, `review squad`.
- **19-04**: Implement targeted `audit security` with strict/practical modes.
- **19-05**: Implement guarded modifying/sandboxed commands: `cleanup de-slopify` and `prototype`.
- **19-06**: Add command metadata logging for eval and shadow comparison.
- **19-07**: Add tests and documentation for all command contracts and workflows.
</plan_sequence>

<implementation_constraints>
## Implementation Constraints

- Do not clone the external plugin.
- Do not implement broad repo-wide sweep behavior in this pass.
- Do not add heavy dependencies unless justified.
- Prefer read-only commands first.
- Do not make destructive changes.
- Do not remove existing variables, architecture, public APIs, or config keys unless clearly safe or explicitly approved.
- Keep outputs structured and machine-readable enough for future AIOS evals.
- Integrate with existing command/skill/workflow architecture instead of creating a parallel system.
</implementation_constraints>
