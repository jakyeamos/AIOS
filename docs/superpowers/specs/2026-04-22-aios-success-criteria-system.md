# AIOS Success Criteria — Evaluation System Audit + Implementation Prompt

**Date:** 2026-04-22
**Status:** Ready to run
**Type:** Audit + implementation prompt
**Author:** jakyeamos

---

## Purpose

Turn AIOS-managed success criteria from passive documentation into a first-class control plane for agent quality across all linked development projects. Success criteria must actively shape planning, implementation, review, completion, and long-term learning.

**Core idea:**
- Skills define how work is done.
- Success criteria define how work is judged.
- Hooks/orchestration define when evaluation happens.
- Stored evaluation artifacts define how the system improves over time.

---

## Prompt

You are auditing and implementing a success-criteria-driven evaluation system inside AIOS.

Goal:
Turn AIOS-managed success criteria into a first-class control plane for agent quality across all linked development projects. These files should not be passive documentation. They must actively shape planning, implementation, review, completion, and long-term learning.

Core idea:
- Skills define how work is done.
- Success criteria define how work is judged.
- Hooks/orchestration define when evaluation happens.
- Stored evaluation artifacts define how the system improves over time.

Context:
AIOS already has or is expected to have global criteria files like:
- spec/success-criteria/code-simplicity.md
- spec/success-criteria/security-review.md
- spec/success-criteria/observability.md
and similar domain-specific evaluation files.

The target state is an AIOS where:
1. Agents resolve applicable success criteria before doing work.
2. Agents use them during execution to guide choices.
3. Agents evaluate the actual diff against them before marking work complete.
4. Results are stored so quality can be measured over time.
5. Skills can be paired with postconditions enforced by success criteria.
6. This system is wired into the real workflow, not just written down in docs.

Your task:
Audit the current AIOS control-plane state, identify what is missing, then implement the strongest reasonable version of this system. This repository is the implementation home; the criteria must be applicable to any linked project through task type, domain, skill, and project-profile rules. Large refactors are allowed if they materially improve clarity, enforceability, and long-term maintainability.

Important constraints:
- Do not treat this as a docs-only task.
- Do not stop at generic guidance.
- Do not create dead files that are never loaded by agents.
- Prefer explicit enforcement over vague convention.
- Prefer AIOS-managed standards and project-profile applicability over generic "best practices."
- Keep the architecture legible. Thin display surfaces, consolidated helpers, clear boundaries.
- Make the system easy for both humans and agents to inspect.
- Be aggressive about removing ambiguity, duplicated logic, dead paths, and unowned standards.

---

## Audit Objectives

1. Find all existing success-criteria or equivalent evaluation files.
2. Find all skills, agent instructions, orchestration docs, hooks, workflows, or registry files that should reference them.
3. Detect path inconsistencies, naming drift, typos, and broken references. For example, catch issues like `success-criteria` vs `success-critieria`.
4. Determine whether the current agent flow has:
   - pre-execution criteria resolution
   - in-execution awareness
   - post-change evaluation
   - blocking vs warning severity
   - artifact persistence
   - human override paths
   - domain-specific activation logic
5. Identify where success criteria should be global, task-type-specific, domain-specific, or skill-specific.
6. Identify where existing skills — especially simplification/refactor skills — can be paired with success-criteria-based postconditions so the system judges whether the skill actually improved the code.

---

## Design Target

Implement a layered system with at least these concepts:
- Global criteria
- Task-type criteria
- Domain/use-case-specific criteria
- Skill-specific postconditions

---

## Required Architecture Outcomes

### 1. Canonical index file

`spec/success-criteria/index.md`

This index should clearly define:
- every criteria file
- its intent
- when it applies
- whether it is blocking or advisory
- path/file/workflow triggers
- any dependencies or related criteria
- whether it is global, task-type, domain-specific, or skill-specific

### 2. Agent-facing documentation

Update `AGENTS.md` and any other central orchestration docs so agents are always aware of the criteria system.

The agent workflow should explicitly require:
- determining applicable criteria before implementation
- evaluating the final diff against applicable criteria before completion
- reporting blockers, warnings, and accepted tradeoffs

### 3. Stable criteria file template

Each criteria file should have a consistent schema/section layout:
- Intent
- Applies When
- Required Checks
- Blockers
- Warnings
- Evidence To Provide
- Related Criteria
- Example Good / Example Bad (where helpful)

### 4. Real evaluation mechanism

Implement the strongest reasonable version for AIOS:
- a script
- a registry-driven evaluator
- a workflow-integrated review step
- a hook-triggered check
- structured output saved to artifacts

Do not overengineer, but do not leave evaluation purely manual if it can reasonably be automated.

### 5. Runtime integration

Success criteria should be resolved and applied during actual agent execution, not merely referenced in docs. Wire them into the current AIOS control flow:
- task planning
- implementation
- pre-stop or completion hooks
- review/report generation
- run/session state

### 6. Stored evaluation artifacts

For each relevant run/task/change, store structured information:
- task identifier
- files changed
- criteria applied
- passes
- warnings
- blockers
- accepted tradeoffs
- human override or approval status if relevant

Design this so future analytics can answer:
- which criteria are most predictive
- which criteria are noisy
- which skills tend to violate which criteria
- where simplifier/refactor skills help or hurt

### 7. Skill integration

Create a clean way for skills to declare or map to expected postconditions:
- a simplifier skill → judged against code-simplicity criteria
- a security-related skill → judged against security-review criteria
- observability-related work → judged against observability criteria

Make the mapping explicit and inspectable.

### 8. Domain-specific criteria

Where appropriate, propose and scaffold high-value domain-specific criteria for AIOS:
- agent-harness-safety
- workflow-state-integrity
- truth-file-consistency
- repo-boundary-discipline
- telemetry-schema-quality
- task-queue-correctness

Only add criteria that are justified by the architecture and workflow.

---

## Implementation Style
- Favor clarity over cleverness.
- Keep files and naming consistent.
- Use registries/config where they help discoverability.
- Avoid creating a maze of abstractions just to feel "enterprisey."
- When adding automation, make failure states understandable.
- Distinguish blockers from warnings.
- Keep the review output concise but structured.

---

## Execution Instructions

1. Audit AIOS first, including how linked projects are represented.
2. Summarize the delta between current state and target state.
3. Implement the system incrementally.
4. As you go, update documentation and any project truth/handoff files that should reflect the new architecture.
5. If AIOS integration is too large to finish in one pass, do not stop with vague notes. Create a concrete handoff document that records:
   - what was completed
   - what remains
   - exact files touched
   - next recommended implementation steps
   - architectural decisions already locked in
6. Preserve working momentum: do not leave behind partially connected standards with no runtime path unless clearly documented as staged work.

---

## Concrete Deliverables

- canonical success criteria index
- normalized/cleaned criteria file layout and naming
- criteria template or schema
- agent/orchestration docs updated to require criteria resolution and evaluation
- implementation of evaluation flow or evaluator harness
- storage location/format for evaluation artifacts
- explicit skill-to-criteria mapping where appropriate
- a small but strong starter set of domain-specific criteria if missing
- final audit report of what changed and why

---

## Acceptance Criteria

Complete only when all of the following are true:
1. There is one obvious place to discover all success criteria.
2. Agents have a clear instruction path telling them when and how to use criteria.
3. The system can determine which criteria apply to a task/change.
4. The final diff is evaluated against applicable criteria before completion.
5. The result distinguishes blockers, warnings, and accepted tradeoffs.
6. Evaluation results are stored in a durable, inspectable way.
7. Skill usage can be meaningfully judged against relevant postconditions.
8. The system is domain-aware, not just generic.
9. Naming/path inconsistencies and broken references are fixed.
10. The final architecture is simpler, more enforceable, and more inspectable than what existed before.

---

## Output Format

Provide:
1. A brief audit summary of the initial state.
2. The implementation plan you chose.
3. The actual repo changes.
4. The final architecture summary.
5. A concise "what remains" section.
6. A handoff document if the work cannot be fully completed in one pass.

---

## Biases to Follow
- Prefer enforcement over aspiration.
- Prefer explicit evaluation over vibes.
- Prefer AIOS project truth and project-profile metadata over generalized doctrine.
- Prefer measurable quality loops over one-off rules.
- Prefer a smaller number of strong standards over many weak ones.

---

## Special Requirement: Simplification vs Harmful Refactor

Where simplification/refactor skills are involved, ensure the system can tell the difference between:
- true simplification
- superficial line-count reduction
- harmful abstraction collapse
- hidden complexity moved elsewhere
