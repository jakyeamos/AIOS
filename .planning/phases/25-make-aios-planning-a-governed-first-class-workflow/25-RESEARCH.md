# Phase 25: Make AIOS Planning A Governed First-Class Workflow - Research

**Researched:** 2026-06-24
**Domain:** AIOS workflow routing, GSD planning governance, invoked command routing, standards-at-planning-time
**Confidence:** HIGH for local codebase findings, MEDIUM for final implementation shape until execution validates the exact registry schema edits.

## User Constraints

- Planning must be a first-class AIOS capability, not a fallback around execution governance.
- Standards should surface early in planning and continue through execution, verification, and testing.
- The observed failure is concrete: `codex-aios-shadow.py` returned `route-blocked` for a GSD phase-add objective because no governed workflow matched strongly enough.
- A second observed failure is concrete: a user-invoked `gsd-execute-phase 24` command was shadowed as weak prose (`Execute GSD phase 24`) and returned `route-blocked` even though GSD execution should be a governed AIOS lane.
- Phase 25 should make planning and known invoked-command routing stronger without weakening existing route-blocking behavior for ambiguous or unsupported work.

## Summary

AIOS already contains pieces of a strong planning system: `services/planning_workflow_detection.py` detects GSD planning aliases and natural-language planning; `services/planning_lenses.py` maps `gsd:plan` to executor-readiness, constraint-preservation, artifact-definition, validation-strategy, and escalation-clarity; `services/execution_symmetric_planner.py` can produce planning sections from those signals. [VERIFIED: local source]

The failure happens lower in the governed `start-work` route. `scripts/codex-aios-shadow.py` calls `scripts/codex-aios-route.py`, which calls `aios start-work`; `services/task_routing.route_objective()` blocks when `services.workflow_orchestration.recommend_route_primitives()` returns no selected workflow. The current workflow candidate ranker only scores registry trigger hints plus implementation/recovery/audit/content/writing evidence. Natural-language GSD phase operations like "add a phase" do not have a first-class active workflow family, so the route can block even though the planning detection layer can recognize nearby planning intent. [VERIFIED: local source]

The same route-shape problem applies to invoked commands. When Codex receives a concrete skill invocation such as `gsd-execute-phase 24`, the AIOS shadow helper may only receive a prose objective like "Execute GSD phase 24." That loses the command identity that should make routing deterministic. Known GSD command families should be first-class routing evidence before natural-language fallback scoring, with unknown commands still allowed to block. [VERIFIED: user-observed local failure]

**Primary recommendation:** Add a governed planning workflow family and a known command-invocation routing path to the workflow registry/route selection flow, then make start-work packets carry planning workflow detection, command-family evidence, standards/lens constraints, executable plan-contract expectations, and verification handoff evidence.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
| --- | --- | --- | --- |
| Planning intent detection | `services/planning_workflow_detection.py` | `config/planning/gsd-workflow-phases.json` | Detection is already isolated in a service with configurable aliases. |
| Invoked command routing | `services/workflow_orchestration.py`, `services/task_routing.py` | `scripts/codex-aios-shadow.py`, `scripts/codex-aios-route.py` | Known command identity should reach governed routing before prose fallback scoring. |
| Governed workflow selection | `services/workflow_orchestration.py` | `config/workflows/registry.json` | `recommend_route_primitives()` owns selected workflow and prompt/backend recommendations. |
| Start-work route blocking | `services/task_routing.py` | `services/aios_cli.py` | `route_objective()` decides ready vs blocked before run and packet creation. |
| Planning standards and lenses | `services/planning_lenses.py`, `services/planning_skill_lenses.py` | `config/planning/planning-lenses.json` | Existing planning lens selection already binds workflow/phase to standards references. |
| Packet and evidence visibility | `services/aios_cli.py`, `services/daily_flow.py`, `services/operator_search.py` | SQLite `briefing_packets` and run tables | Start-work packets and drilldowns are the operator-visible contract. |
| Regression coverage | `tests/test_planning_workflow_detection.py`, `tests/test_workflow_orchestration.py`, `tests/test_task_routing.py`, `tests/test_aios_cli.py`, `tests/test_execution_symmetric_planner.py` | copied-live-DB smoke checks | Current tests cover planning detection and start-work blocking, but not governed planning-route success. |

## Standard Stack

No new runtime dependency is required. Use existing AIOS Python services, JSON registries, pytest, and `pnpm context:validate`. [VERIFIED: local source]

| Surface | Existing authority | Why standard |
| --- | --- | --- |
| Workflow registry | `config/workflows/registry.json` | Active governed routes are registry-driven. |
| GSD phase alias registry | `config/planning/gsd-workflow-phases.json` | Planning aliases are already configurable. |
| Planning lenses | `config/planning/planning-lenses.json` | Existing standards-at-planning-time mechanism. |
| Route API | `services/task_routing.py` + `services/workflow_orchestration.py` | Existing `start-work` route contract flows through these services. |
| Codex command/shadow helpers | `scripts/codex-aios-shadow.py`, `scripts/codex-aios-route.py` | Existing Codex entrypoint into governed AIOS routing. |
| Packet output | `services/aios_cli.py` | Existing handoff packet construction and persistence. |
| Tests | pytest under `tests/` | Existing repo verification convention. |

## Architecture Patterns

### Pattern 1: Registry-first workflow capability

Add a workflow registry entry before adding special-case routing logic. `load_workflow_registry()` validates workflows and `validate_workflow_bindings()` enforces known skills, standards, prompt bindings, and validation criteria. [VERIFIED: local source]

### Pattern 2: Detection as evidence, not replacement

`detect_planning_workflow()` should produce structured planning context. Route selection should consume that context and rank a planning workflow. It should not bypass project resolution or route-blocking gates. [VERIFIED: local source]

### Pattern 3: Command identity as evidence, not prose

Known invoked commands such as `gsd-execute-phase 24` should contribute structured command-family evidence to route selection. They should not depend on whether a lossy objective string like "Execute GSD phase 24" happens to cross a text-scoring threshold. Unknown commands should still route-block or require explicit operator handling. [VERIFIED: user-observed local failure]

### Pattern 4: Packet sections carry the contract

Start-work packets already include workflow, success criteria, required checks, and escalation sections. Planning routes should add planning-specific standards/lens and artifact-contract sections rather than requiring a separate planning-only CLI path. [VERIFIED: local source]

### Pattern 5: Preserve ambiguity blocking

Existing route-blocking is intentional: weak or tied workflow evidence should block before run/packet creation. Planning work should improve confident planning matches without making unknown objectives route by default. [VERIFIED: PROJECT.md and tests]

## Do Not Hand-Roll

| Problem | Do not build | Use instead | Why |
| --- | --- | --- | --- |
| New ad hoc planner router | A second routing path in scripts | `recommend_route_primitives()` and `route_objective()` | Keeps governed start-work behavior centralized. |
| Prose-only command routing | Flatten invoked commands into objective text only | Command-family metadata or canonical command hints consumed by governed routing | Prevents valid known commands from route-blocking because command identity was lost. |
| Hardcoded planning packet prose | One-off packet strings only | Planning lenses and workflow registry metadata | Keeps standards and artifact expectations inspectable. |
| Broad keyword fallback | Route anything with "plan" to implementation | `detect_planning_workflow()` + active planning workflow | Avoids false positives and preserves route-blocking. |
| Manual-only proof | A note saying planning routes work | Unit tests plus `start-work` smoke for failing objective | Prevents recurrence of the exact route-blocked issue. |

## Common Pitfalls

### Pitfall 1: Solving only `/gsd-plan-phase`

The failure objective was not a literal `/gsd-plan-phase`; it was a natural-language GSD phase-add objective. Add coverage for `gsd-add-phase`, `add phase`, `plan phase`, blocker-to-phase, and roadmap-gap closure language. [VERIFIED: local failure]

### Pitfall 2: Solving only planning

The execution failure shows the same issue for invoked GSD commands. Add coverage for `gsd-execute-phase 24` or equivalent command metadata so AIOS does not treat known execution commands as ambiguous prose. [VERIFIED: user-observed local failure]

### Pitfall 3: Weakening route-blocking

Adding a generic "plan" fallback or generic "command" fallback could silently route ambiguous work and undo the recent hardening that blocks weak/tied workflow evidence. Preserve the selected-score and runner-up checks; planning and command routing should win only with explicit planning evidence or known command-family evidence. [VERIFIED: `recommend_route_primitives()`]

### Pitfall 4: Treating planning as implementation

The current selected agent defaults to `implementation-lead`. A planning route can initially reuse the handoff path, but packets must make clear that the next action is planning artifacts, not code execution. [VERIFIED: `task_routing.route_objective()`]

### Pitfall 5: Standards surface too late

If standards and success criteria are only evaluated during execution/commit, planning quality remains reactive. Packet sections should include planning lenses, applicable standards, acceptance criteria, evidence expectations, and verification handoff before implementation begins. [VERIFIED: user constraint and existing planning lens services]

## Validation Architecture

### Test Framework

| Property | Value |
| --- | --- |
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest -q tests/test_planning_workflow_detection.py tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_aios_cli.py tests/test_execution_symmetric_planner.py` |
| Full suite command | `uv run pytest -q tests/test_planning_workflow_detection.py tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_aios_cli.py tests/test_execution_symmetric_planner.py && pnpm context:validate` |

### Phase Requirements To Test Map

| Requirement | Behavior | Test Type | Automated Command |
| --- | --- | --- | --- |
| Governed planning workflow | GSD phase-add objective selects planning workflow instead of route-blocking | unit/CLI | `uv run pytest -q tests/test_task_routing.py tests/test_aios_cli.py` |
| Governed command invocation | `gsd-execute-phase 24` selects a governed execution lane instead of route-blocking | unit/CLI | `uv run pytest -q tests/test_workflow_orchestration.py tests/test_task_routing.py tests/test_codex_aios_route.py tests/test_codex_aios_shadow.py` |
| Planning detection breadth | `gsd-add-phase`, `add phase`, blocker-to-phase, and roadmap planning phrases classify as planning | unit | `uv run pytest -q tests/test_planning_workflow_detection.py` |
| Standards at planning time | Route packet exposes planning lenses, standards, acceptance criteria, and verification contract | unit/CLI | `uv run pytest -q tests/test_aios_cli.py tests/test_execution_symmetric_planner.py` |
| Governance preservation | Ambiguous project/workflow routes still block before packet creation | regression | `uv run pytest -q tests/test_task_routing.py tests/test_aios_cli.py` |
| Registry validity | New workflow/skill/prompt bindings validate | unit | `uv run pytest -q tests/test_workflow_orchestration.py` |

## Security Domain

Planning routes affect governance and agent behavior, not end-user authentication or data access. Security concerns are still relevant because bad planning can silently weaken standards.

| Threat | STRIDE | Mitigation |
| --- | --- | --- |
| Planning route bypasses governed checks | Elevation of privilege | Keep route inside `start-work`, not a script bypass. |
| Invoked command bypasses governed checks | Elevation of privilege | Treat known command identity as route evidence inside `start-work`, not as a shell/script bypass. |
| Ambiguous objective gets over-routed to planning | Tampering | Preserve weak/tied route blocking and add tests for non-planning ambiguity. |
| Unknown command gets over-routed | Tampering | Route only known command families; unknown commands must block or require explicit operator handling. |
| Packet omits standards or evidence expectations | Repudiation | Persist planning detection/lens metadata in route result or packet sections. |
| Planning packet leaks broad project context | Information disclosure | Use selected standards/lenses and scoped artifacts, not broad Markdown loading. |

## Open Questions (RESOLVED)

1. **Should Phase 25 implement a standalone planning CLI?** RESOLVED: No. Use governed `start-work` routing so planning is first-class inside AIOS rather than a parallel path.
2. **Should all "plan" language route to planning?** RESOLVED: No. Use explicit planning workflow detection and registry hints; preserve route-blocking when evidence is weak or tied.
3. **Should this phase add external dependencies?** RESOLVED: No. Existing Python services, JSON registries, and pytest are sufficient.

## Source Audit Input

| Source | Item | Planning implication |
| --- | --- | --- |
| GOAL | Make AIOS planning a governed first-class workflow | Plans must cover workflow registry, route selection, packets, tests, and docs/truth. |
| USER | Standards should show at planning time and carry into execution/verification/testing | Plans must include planning lenses/standards and verification handoff packet work. |
| FAILURE | `route-blocked` for GSD phase-add objective | Plans must include the exact regression scenario. |
| FAILURE | `route-blocked` for invoked `gsd-execute-phase 24` command after flattening to prose | Plans must include command-invocation regression coverage. |
| CODE | `detect_planning_workflow()` exists but is not enough for `start-work` route success | Plans must bridge detection into `recommend_route_primitives()` / route packets. |
| CODE | `recommend_route_primitives()` blocks when candidate evidence is weak or tied | Plans must preserve this safety property. |

## Sources

### Primary

- `scripts/codex-aios-shadow.py`
- `scripts/codex-aios-route.py`
- `services/task_routing.py`
- `services/workflow_orchestration.py`
- `services/planning_workflow_detection.py`
- `services/planning_lenses.py`
- `services/execution_symmetric_planner.py`
- `config/planning/gsd-workflow-phases.json`
- `config/planning/planning-lenses.json`
- `config/workflows/registry.json`
- `tests/test_planning_workflow_detection.py`
- `tests/test_execution_symmetric_planner.py`
- `tests/test_workflow_orchestration.py`

## Metadata

**Confidence breakdown:**
- Route failure location: HIGH - verified in local source and observed CLI output.
- Planning detection capability: HIGH - verified in service and tests.
- Exact registry entry shape: MEDIUM - must be validated during implementation with `validate_workflow_bindings()`.
- Packet section placement: MEDIUM - requires executor to inspect current packet construction helpers before editing.

**Research date:** 2026-06-24
**Valid until:** 2026-07-24
