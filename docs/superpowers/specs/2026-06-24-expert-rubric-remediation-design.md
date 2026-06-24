# Expert Rubric Remediation Workflow Design

**Date:** 2026-06-24
**Status:** Review ready
**Type:** Workflow design spec
**Author:** jakyeamos

---

## Purpose

Make the pattern "compile task expertise, synthesize a rubric, audit evidence, and produce a remediation plan" a first-class AIOS workflow.

The initial motivating case is the Soundscape UI review: TMCP visual-polish nodes made the agent behave like a stronger product-surface reviewer, then that expertise became a rubric and remediation plan. The durable AIOS concept is broader than UI polish. The same workflow must support visual design, security, architecture, developer experience, data realism, testing, documentation, and product-strategy audits.

Core intent:

```text
objective
  -> expertise packet
  -> task-specific rubric
  -> evidence-backed audit
  -> phased remediation plan
  -> optional implementation handoff
```

The rubric must be an artifact, not only prose in a final answer. This makes the agent's expertise inspectable before it starts judging or prescribing fixes.

## Architecture

Add a general AIOS workflow named `expert_rubric_remediation_v1`.

The workflow sits above TMCP. TMCP remains the expertise compiler: it selects task nodes, modules, source-skill excerpts, behavior atoms, branches, source hashes, and skipped nodes. `expert_rubric_remediation_v1` consumes that packet, turns it into a review rubric, uses the rubric to audit repo evidence, and converts the findings into an ordered remediation plan.

The workflow must not automatically edit code. It produces review artifacts and an optional implementation handoff. This keeps the judging phase separate from the execution phase.

## Workflow Registry Contract

The workflow registry entry must use this shape:

```json
{
  "key": "expert_rubric_remediation_v1",
  "name": "Expert Rubric Remediation v1",
  "workflow_family": "audit_and_plan",
  "purpose": "Compile domain expertise into an explicit rubric, audit concrete evidence, and produce an ordered remediation plan.",
  "trigger_hints": [
    "review using TMCP",
    "make this first class",
    "create a rubric",
    "remediation plan",
    "audit against expert sources",
    "turn expertise into a plan"
  ],
  "output_contract": [
    "expertise packet",
    "scored rubric",
    "evidence-backed audit",
    "ordered remediation plan",
    "optional implementation handoff"
  ],
  "required_validations": [
    "tmcp_packet_compiled",
    "rubric_dimensions_present",
    "findings_have_evidence",
    "remediation_has_verification"
  ]
}
```

## Stages

### 1. `expertise_compile`

Input:

- normalized objective
- project path
- optional domain/profile hints

Output:

- `.aios/reviews/{run_id}/expertise-packet.json`

Requirements:

- Compile a TMCP packet through the existing TMCP runtime.
- Preserve selected nodes, skipped nodes, behavior atoms, source hashes, graph metadata, candidate scores, and traversal fingerprint.
- Record why optional nodes were skipped when they would be plausible but not selected.
- Fail hard when TMCP cannot compile a packet.

### 2. `rubric_synthesize`

Input:

- expertise packet
- normalized objective
- optional project identity/context summary

Output:

- `.aios/reviews/{run_id}/rubric.md`
- `.aios/reviews/{run_id}/rubric.json`

Requirements:

- Produce 5 to 8 dimensions unless the scope clearly requires fewer.
- Each dimension must include a name, weight, scoring scale, evidence expectations, pass threshold, and review questions.
- Include domain-specific dimensions when the packet supports them. For example, visual-polish runs can include surface hierarchy, data realism, interaction architecture, and first-screen product evidence.
- Preserve TMCP provenance by linking dimensions back to selected nodes whenever a dimension is derived from TMCP material.
- Fail hard if no dimensions are produced.

### 3. `evidence_audit`

Input:

- rubric
- target repo or artifact scope
- user-provided examples, screens, docs, or code references

Output:

- `.aios/reviews/{run_id}/audit-report.md`
- `.aios/reviews/{run_id}/audit-report.json`

Requirements:

- Gather concrete evidence from local files, docs, screenshots, command output, or user-provided artifacts.
- Score each rubric dimension.
- Findings must cite evidence paths, screen names, line references, command outputs, or an explicit "not reviewed" gap.
- Separate blocker findings, warnings, and observations.
- Record confidence for each dimension when evidence is partial.
- Fail hard when the report contains findings without evidence references.

### 4. `remediation_plan`

Input:

- rubric
- audit report

Output:

- `.aios/reviews/{run_id}/remediation-plan.md`

Requirements:

- Produce ordered implementation slices, not a flat wish list.
- Each slice must include scope, rationale, expected impact, risk, verification commands or manual checks, and likely follow-up workflow.
- Prefer the smallest useful slices that can be committed independently.
- Mark optional/future polish separately from remediation needed to pass the rubric.
- Fail hard when fixes lack verification expectations.

### 5. `implementation_handoff`

Input:

- remediation plan
- selected slice or user-approved execution scope

Output:

- `.aios/reviews/{run_id}/implementation-handoff.md`

Requirements:

- Produce a bounded prompt or plan suitable for the normal implementation workflow.
- Include artifact links, target files, acceptance criteria, verification commands, and known risks.
- Do not execute implementation unless the user explicitly approves that transition.

## Artifact Schemas

### `rubric.json`

```json
{
  "schema": "aios-expert-rubric-v0.1",
  "run_id": "string",
  "objective": "string",
  "source_packet": "expertise-packet.json",
  "dimensions": [
    {
      "id": "string",
      "name": "string",
      "weight": 1,
      "scale": "0-4",
      "pass_threshold": 3,
      "evidence_expectations": ["string"],
      "review_questions": ["string"],
      "source_nodes": ["@task:...", "@module:..."]
    }
  ]
}
```

### `audit-report.json`

```json
{
  "schema": "aios-expert-audit-report-v0.1",
  "run_id": "string",
  "rubric": "rubric.json",
  "scores": [
    {
      "dimension_id": "string",
      "score": 2,
      "confidence": "high",
      "evidence": ["path-or-command-reference"],
      "gaps": ["string"]
    }
  ],
  "findings": [
    {
      "id": "string",
      "severity": "blocker",
      "dimension_id": "string",
      "summary": "string",
      "evidence": ["path-or-command-reference"],
      "recommended_fix": "string"
    }
  ]
}
```

### `remediation-plan.md`

The markdown plan must include:

- objective and scope
- selected expertise nodes
- score summary
- ordered remediation slices
- acceptance criteria per slice
- verification commands or manual checks per slice
- implementation handoff notes
- explicit deferred scope

## Error Handling

Hard failures:

- TMCP packet cannot compile.
- Target repo path is missing or unreadable.
- Rubric synthesis produces no dimensions.
- Audit report has findings without evidence references.
- Remediation plan has fixes without verification expectations.

Soft warnings:

- Some requested scope was not reviewed.
- Screenshots or runtime evidence were not available.
- Scores are low confidence because evidence was partial.
- TMCP selected a broad fallback task instead of a precise profile.
- Product-specific identity nodes were skipped because project identity was unknown.

## Data Flow

```text
objective + project_path + optional domain/profile
  -> compile_tmcp_packet()
  -> expertise-packet.json

expertise-packet.json
  -> rubric dimensions
  -> evidence expectations
  -> scoring policy
  -> rubric.md + rubric.json

rubric + repo context
  -> relevant files/screens/docs/commands
  -> scored findings
  -> audit-report.md + audit-report.json

audit-report + rubric
  -> prioritized work slices
  -> verification ladder
  -> remediation-plan.md

remediation-plan + user-approved slice
  -> implementation-handoff.md
  -> normal implementation workflow
```

## Initial Profiles

The workflow is general, but v1 must prove three profiles:

- `visual_polish`: use TMCP visual-polish task/modules and produce product-surface, interaction, hierarchy, and data-realism dimensions.
- `security_privacy`: use selected security, tool-safety, dependency, secrets, permissions, and data-flow sources.
- `developer_experience`: use selected DX, command-discovery, docs, validation-loop, onboarding, and interface clarity sources.

The Soundscape visual-polish case must be captured as a regression fixture for the first profile.

## Testing

Unit tests:

- Rubric synthesis rejects empty dimensions.
- Rubric dimensions preserve TMCP provenance.
- Audit validation rejects findings without evidence.
- Remediation validation rejects slices without verification expectations.
- Implementation handoff refuses to execute without user-approved scope.

Fixture workflow tests:

- Visual-polish fixture using the Soundscape-inspired findings: analytics dashboard, feed waveform randomness, landing hero product evidence, and profile card-stack hierarchy.
- Security/privacy fixture with secrets, permission, or logging evidence.
- Developer-experience fixture with setup commands, docs, failing command discovery, and validation gaps.

Regression assertions:

- Each fixture writes all required artifacts.
- The audit report includes selected and skipped TMCP nodes.
- Each score links to evidence or an explicit gap.
- Remediation slices are ordered and independently verifiable.

## Rollout Plan

1. Add workflow registry entry and stage definitions without changing default routing.
2. Implement artifact writers and validators.
3. Add CLI preview command that runs the workflow in read-only mode.
4. Add the three fixtures and validation tests.
5. Enable routing hints for explicit user requests only.
6. After repeated successful runs, consider promoting common profiles into shortcuts.

## Non-Goals

- No automatic code edits during the review workflow.
- No remote pushes, dependency installs, hook installation, or external writes.
- No requirement that all evidence gathering be automated in v1.
- No Soundscape-specific behavior in the core workflow; Soundscape is only a regression fixture.

## Success Criteria

The workflow is successful when an agent can take a broad request such as "review this app like a product UI expert and make a remediation plan" and produce:

- a clear expertise packet explaining which sources shaped the review
- a rubric that can be inspected before accepting the critique
- findings grounded in concrete evidence
- remediation slices that can be implemented and verified independently
- a handoff into normal implementation only after explicit user approval
