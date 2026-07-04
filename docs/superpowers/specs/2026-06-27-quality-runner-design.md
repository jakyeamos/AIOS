# Quality Runner Design

**Date:** 2026-06-27
**Status:** Review ready
**Type:** Standalone workflow design spec
**Author:** jakyeamos

---

## Purpose

Create a standalone audit-and-plan tool named Quality Runner that lets an agent or human say:

```text
Improve this codebase to my standards.
```

Version 1 does not edit code, create commits, or run autonomous remediation. It inspects a target repository, compiles the applicable quality standards, runs available audit signals, and produces an evidence-backed remediation plan that a coding agent can execute through the target repo's normal workflow.

Quality Runner exists because the useful quality machinery is now distributed across several surfaces:

- TMCP expert rubric workflows
- AIOS repo-gate adoption/backfill workflows
- Pre-CR checks
- anti-slop and structural scans
- dead-code scans
- language-specific lint, type, test, build, and smoke commands
- truth-file and git-policy contracts

The durable product is not another analyzer. The durable product is an orchestrator that turns these signals into a prioritized, verifiable remediation queue.

## Product Boundary

Quality Runner is standalone. AIOS may be an adapter and first consuming environment, but AIOS must not own the core workflow.

The project should expose two first-class surfaces:

- a CLI for humans, shell scripts, and CI-like usage
- an MCP server for agents that need structured audit, planning, status, and handoff tools

Both surfaces call the same core package. The core package owns repo discovery, standards compilation, analyzer orchestration, finding normalization, remediation planning, artifact writing, and run status. The CLI and MCP layers only translate input/output.

## Non-Goals for v1

- No source-code modifications.
- No automatic commits.
- No dependency installation.
- No remote service calls by default.
- No attempt to make every repo pass every possible gate.
- No hidden downgrade from failed tools to silent success.
- No AIOS-specific artifact path unless the AIOS adapter is explicitly selected.

## User-Facing Contract

Given a repo path and standards profile, Quality Runner must:

1. discover the repo shape and quality surfaces
2. ingest local and named standards
3. detect available analyzer and verifier capabilities
4. run applicable audit-only checks
5. normalize findings into one evidence model
6. synthesize an ordered remediation plan
7. write machine-readable and human-readable artifacts
8. produce an implementation handoff suitable for a coding agent

Quality Runner may write run artifacts into the target repo. It must not otherwise modify the target repo in v1.

## CLI Surface

Initial commands:

```bash
quality-runner doctor
quality-runner inspect /path/to/repo
quality-runner audit /path/to/repo --standards jakyeamos
quality-runner plan /path/to/repo --standards jakyeamos
quality-runner run /path/to/repo --standards jakyeamos
quality-runner status /path/to/repo
quality-runner export-handoff /path/to/repo --run-id <run-id>
```

Command behavior:

- `doctor` checks local install health, adapter availability, MCP readiness, and optional AIOS integration.
- `inspect` performs repo discovery and capability detection without running quality commands.
- `audit` runs available audit-only analyzers and writes findings.
- `plan` reads an existing audit or runs the minimum missing inspection needed, then writes a remediation plan.
- `run` means audit plus plan. In v1 it does not mean implementation.
- `status` lists recent runs and artifact locations.
- `export-handoff` renders a compact agent handoff from a completed run.

All commands should support `--json`. Commands that write artifacts should print the run id and artifact directory.

## MCP Surface

Initial MCP tools:

```text
quality_runner_doctor
quality_runner_inspect_repo
quality_runner_audit_repo
quality_runner_plan_remediation
quality_runner_run
quality_runner_status
quality_runner_export_handoff
```

MCP outputs must be structured and agent-friendly:

- current stage
- artifact paths
- blocking failures
- warnings
- recommended next action
- whether implementation is allowed

For v1, `implementation_allowed` must always be `false` in Quality Runner output. The handoff may instruct the calling agent how to proceed after user approval, but the MCP server must not directly execute fixes.

## Artifact Layout

Default artifact path:

```text
.quality-runner/
  runs/
    <run-id>/
      run.json
      repo-scan.json
      standards-packet.json
      capability-map.json
      audit-report.json
      audit-report.md
      remediation-plan.json
      remediation-plan.md
      agent-handoff.md
      logs/
        <adapter>.log
```

AIOS adapter runs may additionally mirror or link artifacts into AIOS-owned locations, but the standalone `.quality-runner/` directory is the canonical v1 output.

## Core Architecture

Quality Runner should be split into small, portable modules:

```text
quality_runner/
  core/
    discovery.py
    standards.py
    capabilities.py
    findings.py
    planning.py
    artifacts.py
    run_state.py
  adapters/
    tmcp.py
    aios.py
    pre_cr.py
    antislop.py
    git_policy.py
    truth_file.py
    javascript.py
    python.py
    shell.py
  cli.py
  mcp_server.py
```

The core speaks in data contracts. Adapters may run tools, parse config, or inspect files, but they return normalized capability, finding, evidence, and recommendation objects.

## Adapter Contract

Each adapter should declare:

```json
{
  "id": "string",
  "name": "string",
  "kind": "standards | analyzer | verifier | policy | enrichment",
  "available": true,
  "availability_evidence": ["path-or-command"],
  "read_only": true,
  "writes_artifacts": false,
  "requires_network": false,
  "requires_approval": false
}
```

Analyzer adapters return findings:

```json
{
  "id": "string",
  "source": "adapter-id",
  "severity": "blocker | warning | observation",
  "category": "lint | types | tests | dead_code | structure | security | docs | workflow | ui | git | truth",
  "summary": "string",
  "evidence": [
    {
      "kind": "file | command | artifact | absence",
      "reference": "string",
      "detail": "string"
    }
  ],
  "recommended_fix": "string",
  "verification": ["string"]
}
```

Adapters must report evidence-of-absence when expected quality surfaces are missing. A missing Pre-CR config, absent truth file, unavailable dead-code command, or missing typecheck script is a finding, not an invisible skip.

## Standards Profiles

The first named profile should be `jakyeamos`.

It should compile standards from, in order:

1. explicit CLI/MCP inputs
2. target repo `AGENTS.md` or equivalent agent contract
3. target repo truth file and local quality config
4. user-global standards when available
5. built-in Quality Runner defaults

The standards packet should preserve provenance. If a requirement came from `AGENTS.md`, the packet must cite that file. If it came from the built-in profile, the packet must identify the profile version.

## v1 Workflow

### 1. `repo_inspect`

Input:

- repo path
- optional standards profile

Output:

- `repo-scan.json`
- `capability-map.json`

Responsibilities:

- detect git root, active branch, dirty state, remotes, and truth file
- detect languages, package managers, test frameworks, CI files, scripts, hooks, Pre-CR config, anti-slop config, dead-code tools, UI/runtime surfaces, and docs
- detect AIOS/TMCP availability without requiring it
- record missing expected capabilities as warnings

### 2. `standards_compile`

Input:

- repo scan
- standards profile
- local instruction files

Output:

- `standards-packet.json`

Responsibilities:

- compile repo-specific and user-specific standards into normalized requirements
- preserve source provenance
- distinguish hard gates, soft gates, preferences, and unsupported requirements
- include commit/truth-file rules when present

### 3. `audit_collect`

Input:

- repo scan
- standards packet
- capability map

Output:

- `audit-report.json`
- `audit-report.md`

Responsibilities:

- run read-only analyzers that are available and appropriate
- record skipped analyzers with explicit reasons
- normalize tool output into findings
- include evidence paths, command references, or evidence-of-absence
- never mark unknown or skipped checks as passing

### 4. `remediation_plan`

Input:

- audit report
- standards packet

Output:

- `remediation-plan.json`
- `remediation-plan.md`

Responsibilities:

- group findings into ordered implementation slices
- prefer small slices that can be committed independently
- separate blockers, quality debt, and optional improvements
- include verification commands or manual checks for every slice
- identify likely owner workflow, such as TMCP expert rubric, repo gate adoption, Pre-CR, UI runtime verification, or language-specific quality ladder

### 5. `agent_handoff`

Input:

- remediation plan
- current run metadata

Output:

- `agent-handoff.md`

Responsibilities:

- summarize the target repo state
- list approved and unapproved scope clearly
- include the first recommended implementation slice
- include verification expectations
- state that Quality Runner v1 performed audit-and-plan only

## Prioritization Rules

The remediation planner should rank work by:

1. hard gate failures blocking repo trust
2. missing verification surfaces
3. high-confidence defects with clear evidence
4. structural problems that make future fixes unreliable
5. documentation/truth drift
6. optional polish or maturity improvements

The planner should avoid giant "fix everything" slices. When a finding requires broad cleanup, the plan should first propose a narrow enabling slice that improves the repo's ability to verify the cleanup.

## Error Handling

Hard failures:

- target path does not exist
- target path is not readable
- artifact directory cannot be written
- standards profile cannot be resolved and no fallback profile is allowed
- audit report contains findings without evidence
- remediation plan contains slices without verification expectations

Warnings:

- repo is not a git repository
- repo has dirty worktree state
- optional adapter is unavailable
- tool command exists but fails
- check is skipped because it would require network or dependency installation
- AIOS adapter is unavailable
- TMCP adapter returns thin or process-only expertise

## Verification Strategy

Quality Runner v1 should have behavior-focused tests for:

- repo discovery on fixture repos
- standards packet provenance
- missing-capability findings
- audit report schema validation
- remediation slice ordering
- CLI JSON output
- MCP JSON-RPC tool dispatch
- no source-code writes outside `.quality-runner/`
- AIOS adapter absence fallback
- TMCP adapter thin-source fallback

Manual smoke checks should run the CLI against:

- a small Python repo
- a small TypeScript repo
- an AIOS-integrated repo
- a repo with missing gates
- a repo with dirty git state

## Open Design Choices

1. Implementation language: Python is the fastest fit for existing AIOS/package patterns, but TypeScript may be easier for MCP distribution in some agent hosts.
2. Artifact directory name: `.quality-runner/` is clearest for standalone ownership; `.aios/quality-runner/` should be adapter-only.
3. Standards profile packaging: the `jakyeamos` profile can start as built-in data, but should eventually be externally versioned.
4. MCP transport: stdio should be the first target; HTTP can wait.
5. Whether Quality Runner should later grow an execution mode. v1 should not, but its plan schema should be compatible with future approved-slice execution.

## Success Criteria

Quality Runner v1 is successful when:

- a user can run one command against a repo and receive a coherent audit plus remediation plan
- an agent can call one MCP tool and receive structured next actions
- missing tools and missing proof become explicit findings
- TMCP, AIOS, Pre-CR, anti-slop, dead-code, truth-file, and language quality signals can participate without becoming hard dependencies
- no target repo source files are modified
- the resulting handoff is specific enough for a coding agent to start the first remediation slice without rediscovering the whole repo
