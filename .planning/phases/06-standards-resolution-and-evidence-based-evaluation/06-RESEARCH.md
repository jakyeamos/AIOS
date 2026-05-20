---
phase: 06-standards-resolution-and-evidence-based-evaluation
phase_number: "06"
type: research
updated: 2026-05-20
---

# Phase 6 Research

**Researched:** 2026-05-20
**Domain:** Standards resolution, success-criteria evaluation, execution-first verification, workflow-stage evaluation hooks
**Confidence:** HIGH

## Summary

Phase 6 binds task execution to explicit standards and converts validation from loose "checklist behavior" into stage-level evaluation backed by durable evidence. The current surfaces already do most of the heavy lifting at run-close time — `services/success_criteria.py` resolves applicable criteria from `config/success-criteria/registry.json` and `skill-map.json`, `bin/hook-session-start.py` previews criteria before execution, `bin/hook-stop.py` calls `evaluate_and_record` to persist findings, and `config/standards/registry.json` defines a parallel standards profile that `services/standards_health.py` snapshots. Phase 5 also added writeback approval policy classes and governed closeout reports that surface unresolved deltas, accepted tradeoffs, and follow-up.

The remaining work is structural, not foundational: (1) the standards profile in `config/standards/` is not yet a first-class **resolution** surface bound to tasks before execution — only `success-criteria` is previewed at session start; (2) evaluation is currently run-scoped, not stage-scoped — there is no `stage_evaluations` concept that lets workflows in `services/workflow_orchestration.py` emit per-stage findings; (3) execution-first verification has an evaluator but its triggers ride on `execution_evidence_for_session(...)` which only inspects `artifacts` (patch metadata) and `rtk_compression_events` — phase 6 must broaden evidence ingestion so the trigger correctly distinguishes "no exec evidence" from "exec evidence simply lives elsewhere"; (4) the planned `audit-only`, `audit-and-implement`, `security review`, `test-first implementation`, and `repo cleanup` workflow contracts from `.planning/WORKFLOW_MATRIX.md` are not yet present in `config/workflows/registry.json` — phase 6 must define their **standards binding** before phase 8 builds the contracts themselves. The `agentize.py` packet today emits hardcoded `relevant_standards` strings that bypass the standards registry entirely; this is the cleanest seam to introduce registry-backed standards resolution.

**Primary recommendation:** Extend `services/success_criteria.py` (or factor out a sibling `services/standards_resolution.py`) so a single **resolve-before-execute** call returns the merged `{criteria_ids, standards_ids, execution_first_triggers, stage_bindings}` set for a packet/task; persist that resolution onto `briefing_packets` and feed it into `bin/hook-session-start.py`, `services/agentize.py`, and `services/workflow_orchestration.py`. Then add a `success_criteria_stage_findings` evidence table keyed off `workflow_execution_reports.run_id` so stage-level validate kinds emit evaluated findings rather than free-form `issues[]` lists. Keep evidence durable by writing both DB rows and JSON artifacts under `data/success-criteria/evaluations/` for every stage.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Standards/criteria resolution (pre-execution) | Python control plane (`services/`) | Hook layer (`bin/hook-session-start.py`, `bin/hook-prompt-submit.py`) | Resolution is a pure-data computation over registry JSON; hooks consume the result and persist it on the packet. |
| Per-stage evaluation hooks | Python control plane (`services/workflow_orchestration.py`) | SQLite (`workflow_execution_reports` + new `success_criteria_stage_findings`) | Stage execution already happens inside `execute_workflow`; emitting structured findings there is the only place the system sees stage boundaries. |
| Execution-first verification | Python control plane (`services/success_criteria.py`) | Hook layer (`bin/hook-stop.py`, `bin/hook-post-tool-use.py`) | The evaluator already lives in `success_criteria.py`; broadening evidence requires hooks to feed test/runtime command rows into the evaluator. |
| Evidence preservation (findings, blockers, tradeoffs) | SQLite (`success_criteria_evaluations`, `success_criteria_findings`, `workflow_execution_reports`) | Filesystem (`data/success-criteria/evaluations/*.json`) | Pattern already established; phase 6 extends the same model to stage-level evidence. |
| Workflow-family standards binding | Config (`config/workflows/registry.json`, `config/success-criteria/skill-map.json`) | Python loader (`services/workflow_orchestration.py`) | Bindings belong in declarative registries so they are reviewable as governed assets in phase 8. |
| Operator-visible standards-aware execution surface | UI (`aios-ui/server/routers/control-plane.ts`) | Python CLI (`services/aios_cli.py`) | Phase 5 just shipped governance overview through this same router seam; phase 6 piggy-backs evaluation visibility there. |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STND-01 | AIOS maps each task to the correct success criteria and standards set before execution | `preview_applicable_criteria` already covers criteria; standards-side equivalent needs to be added by joining `config/standards/registry.json` + `config/success-criteria/registry.json` and persisting the merged resolution onto `briefing_packets`. |
| STND-02 | AIOS evaluates outputs against explicit quality criteria rather than generic model judgment | `evaluate_and_record` + per-criterion evaluators already exist; phase 6 must extend the same pattern to **stage-level** evaluations and to standards-registry items (today only success-criteria registry items have evaluators). |
| STND-03 | AIOS requires execution-first verification for stateful, cross-system, or core-logic changes | `_evaluate_execution_first_verification` already exists and blocks on missing evidence when triggered; gap is broadening `execution_evidence_for_session` to ingest test/runtime evidence from sources beyond `artifacts` (patch metadata) and `rtk_compression_events`. |
| STND-04 | AIOS preserves durable evaluation findings, blockers, warnings, passes, and accepted tradeoffs | `success_criteria_evaluations` + `success_criteria_findings` + `data/success-criteria/evaluations/*.json` already cover run-level; phase 6 adds stage-level findings and wires them into `workflow_execution_reports` so closeout governance from phase 5 surfaces them automatically. |

## Project Constraints (from CLAUDE.md / AGENTS.md)

| Constraint | Source | Phase 6 Implication |
|------------|--------|--------------------|
| Run quality ladder: `ruff check . && ruff format --check . && basedpyright && vulture` | `~/.claude/CLAUDE.md` Python canonical commands | Plans must include these as verification steps for every implementation task in this phase. |
| Atomic commits scoped to one project and one concern | `~/.claude/CLAUDE.md` Git rules | Each task in this phase commits independently and updates project truth before the next task begins. |
| Update `.tracker/PROJECT_TRUTH.md` if it exists; otherwise update `.planning/PROJECT.md` | `~/.claude/CLAUDE.md` Quality Ladder step 5 + AIOS truth file = `.planning/PROJECT.md` | After each task: append to PROJECT.md and STATE.md per phase 4 truth-update contract. |
| No `--no-verify` or `--no-gpg-sign` bypasses | `~/.claude/CLAUDE.md` Git | Honor pre-commit hooks; if a hook fails, fix the root cause. |
| Never use `cat << EOF` or heredoc for file creation | Agent harness rule | Plans must use Write tool, not heredoc, for any new file. |
| Don't add comments/docstrings/type annotations to code I didn't change | `~/.claude/CLAUDE.md` Working style | Edits in this phase should only re-annotate touched signatures. |
| Three similar lines is better than premature abstraction | `~/.claude/CLAUDE.md` Working style | Resist building a generic "evaluator framework"; extend the existing per-criterion evaluator pattern. |

## Standard Stack

### Core (existing — extend, don't replace)

| Library / Surface | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| `services/success_criteria.py` | in-tree | Registry load, applicability resolution, per-criterion evaluators, evaluation persistence | Already the canonical evaluation entry point; consumed by hook-stop, hook-session-start, harness, and agentize. |
| `services/standards_health.py` | in-tree | Standards profile load, assessment snapshots, delta items, backfill tasks | Already the canonical place for standards definitions; phase 6 reuses it for resolution, not just for health scoring. |
| `services/workflow_orchestration.py` | in-tree | Workflow registry load, stage execution, validation skill dispatch | Only place that sees stage boundaries; phase 6 adds stage-level evaluation hooks here. |
| `config/success-criteria/registry.json` | 2026-04-23 | Declarative criterion catalog with `applies_when` rules | Already supports task_types, domains, project rules, skills via `skill-map.json`. |
| `config/standards/registry.json` | 2026.05.0 | Declarative standards profile (`aios-core`) with weights, applicability, related_criteria, waiver policy | Already cross-links to criteria via `related_criteria`; phase 6 walks this link to merge resolution. |
| `bin/hook-session-start.py` | in-tree | Pre-execution criteria preview into the session packet | Phase 6 extends to also surface resolved **standards** and **execution-first triggers**. |
| `bin/hook-stop.py` | in-tree | Post-execution evaluation, standards snapshot, governed closeout report | Phase 6 extends to write stage-level findings into closeout and to broaden execution evidence ingestion. |
| `services/aios_cli.py` | in-tree | `governance-audit`, `contracts-audit`, status, snapshot commands | Phase 6 adds a `standards-resolution preview` CLI and extends the `EvaluationFinding` contract to include stage scope. |

### Supporting (no new external deps required)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sqlite3` (stdlib) | 3.x | All DB writes follow the `ensure_*_schema` + `INSERT INTO ...` pattern already used in `success_criteria.py` | Adding stage-level findings table |
| `json` (stdlib) | — | Artifact persistence under `data/success-criteria/evaluations/` | Mirroring existing JSON-per-evaluation pattern |
| `uuid` (stdlib) | — | Finding / evaluation IDs follow `criteria-eval-{uuid}` and `criteria-finding-{uuid}` patterns | New stage finding IDs follow `criteria-stage-finding-{uuid}` |
| `pytest` 8.x | — | Test pattern: in-memory `sqlite3.connect(":memory:")` or `tmp_path` DB seeded via `executescript` | All new tests follow `tests/test_success_criteria.py` shape |
| `dataclasses` | stdlib | Frozen dataclasses for criterion/standard records | Follow `CriterionRecord` / `StandardDefinition` shape |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Adding `success_criteria_stage_findings` SQLite table | Embed stage findings as JSON inside `workflow_execution_reports.report_json` | JSON-in-row blocks SQL-side aggregation and conflicts with phase 7 delta scoring queries; better to denormalize as rows. |
| Extending `services/success_criteria.py` | New `services/standards_resolution.py` | Splitting risks duplicating the registry load + applicability logic; better to add a thin `resolve_task_standards()` function in `success_criteria.py` that joins both registries and re-exports. |
| Hard-coded execution-first evidence keywords | A pluggable evidence-source registry | Hard-coded approach already in place via `EXECUTION_FIRST_PATH_MARKERS`; broadening means new sources (workflow_execution_reports test output, harness fixture run events, hook-post-tool-use commands), not a new abstraction layer. |
| Generic "evaluator framework" | Keep per-criterion functions in a dispatch dict | Existing `evaluate_criterion` dispatches by criterion ID — three similar handler functions are better than a premature abstraction per CLAUDE.md working style. |

**Installation:** No new dependencies. Phase 6 is entirely additive to existing in-tree modules.

**Version verification:** Not applicable — no external libraries are being added. The `aios-core` standards profile is already pinned at `2026.05.0` in `config/standards/registry.json`.

## Architecture Patterns

### System Architecture Diagram

```
                       ┌──────────────────────────────────────────┐
                       │ config/success-criteria/registry.json    │
                       │ config/standards/registry.json           │
                       │ config/success-criteria/skill-map.json   │
                       └────────────────┬─────────────────────────┘
                                        │ load_registry / load_skill_map
                                        ▼
   ┌──────────────────────┐   resolve_task_standards()   ┌────────────────────────┐
   │ Task / Packet input  │ ────────────────────────────▶│ services/success_      │
   │  - objective         │                              │ criteria.py (+         │
   │  - classifications   │                              │  standards merge)      │
   │  - changed_files     │                              └────────────┬───────────┘
   │  - skills            │                                           │
   │  - project_id/name   │                                           │ returns
   └──────────────────────┘                                           │ {criteria, standards,
                                                                       │  execution_first_triggers,
                                                                       │  stage_bindings}
                                                                       ▼
   ┌────────────────────────────┐                          ┌──────────────────────────┐
   │ bin/hook-session-start.py  │  preview into packet     │ briefing_packets         │
   │ services/agentize.py       │ ◀────────────────────────│ .selected_standards_json │
   │ services/workflow_orch...  │                          │ .selected_criteria_json  │
   └─────────────┬──────────────┘                          └──────────────────────────┘
                 │
                 │ execution proceeds
                 ▼
   ┌─────────────────────────────────────────┐   per-stage evaluate    ┌──────────────────────────────┐
   │ services/workflow_orchestration.py      │ ────────────────────────▶│ success_criteria_stage_      │
   │  execute_workflow():                    │                          │ findings (NEW)               │
   │   for stage in workflow.stages:         │                          │  - run_id, stage_key,        │
   │     run skills                          │                          │    criterion_id, level,      │
   │     evaluate_stage(criteria, evidence)  │                          │    summary, evidence_json    │
   └─────────────┬───────────────────────────┘                          └──────────────────────────────┘
                 │
                 │ session_close trigger
                 ▼
   ┌─────────────────────────────────────────┐                          ┌──────────────────────────────┐
   │ bin/hook-stop.py                        │  evaluate_and_record     │ success_criteria_evaluations │
   │  - execution_evidence_for_session()     │ ────────────────────────▶│ success_criteria_findings    │
   │    (broadened in phase 6)               │                          │ data/.../*.json artifact     │
   │  - evaluate_standards_health()          │  insert_workflow_exec_rpt│ workflow_execution_reports   │
   │  - insert_workflow_execution_report()   │ ────────────────────────▶│  .governance + new            │
   │                                         │                          │  .stage_evaluations          │
   └─────────────────────────────────────────┘                          └──────────────────────────────┘
                                                                                       │
                                                                                       │ exposes
                                                                                       ▼
                                                                       ┌──────────────────────────────┐
                                                                       │ aios governance-audit (CLI)  │
                                                                       │ aios-ui control-plane router │
                                                                       └──────────────────────────────┘
```

### Recommended Project Structure (additions)

```
services/
├── success_criteria.py       # extend: resolve_task_standards(), evaluate_stage()
├── standards_health.py       # extend: applicability filter consumed by success_criteria
└── workflow_orchestration.py # extend: stage evaluation hook in execute_workflow()

config/
├── success-criteria/
│   └── registry.json         # extend: add stage_applicability hints to criteria
├── standards/
│   └── registry.json         # extend: bind standards to workflow families/stages
└── workflows/
    └── registry.json         # extend: stage-level required_criteria per workflow

bin/
├── hook-session-start.py     # extend: also preview resolved standards + triggers
└── hook-stop.py              # extend: broaden execution_evidence_for_session,
                              #         persist stage findings into closeout

data/
└── success-criteria/
    └── evaluations/
        └── stage-*.json      # NEW: per-stage finding artifacts

schema.sql                    # NEW: success_criteria_stage_findings table

tests/
├── test_success_criteria.py  # extend: resolution merging + execution-first broadening
├── test_orchestration_runtime.py # extend: stage evaluation hook coverage
└── test_aios_cli.py          # extend: governance-audit includes stage findings
```

### Pattern 1: Resolve-Before-Execute

**What:** A single call returns the merged criteria + standards + execution-first trigger set for a task, computed from the registries plus inferred context. The hook layer persists the resolution onto `briefing_packets` so downstream stages do not re-derive it.

**When to use:** Any time a packet is being compiled (`hook-session-start`, `hook-prompt-submit`, `agentize`, `workflow_orchestration.execute_workflow`).

**Example:**
```python
# Source: extends services/success_criteria.py preview_applicable_criteria
def resolve_task_standards(
    *,
    project_id: str | None,
    project_name: str | None,
    objective: str | None,
    prompt_classifications: Sequence[str] | None = None,
    changed_files: Sequence[str] | None = None,
    skills: Sequence[str] | None = None,
    workflow_key: str | None = None,
) -> dict[str, Any]:
    criteria_preview = preview_applicable_criteria(
        project_id=project_id,
        project_name=project_name,
        objective=objective,
        prompt_classifications=prompt_classifications,
        changed_files=changed_files,
        skills=skills,
    )
    context = infer_context(
        objective=objective,
        prompt_classifications=prompt_classifications,
        changed_files=changed_files,
        skills=skills,
    )
    # Reuse load_registry from standards_health, filter via applicability
    _profile, standards = standards_health.load_registry()
    applicable_standards = [
        std for std in standards
        if _standard_applies(std, project_name=project_name, domains=context["domains"])
    ]
    return {
        "criteria": criteria_preview["criteria"],
        "standards": [_standard_summary(s) for s in applicable_standards],
        "execution_first_triggers": context["execution_first_triggers"],
        "workflow_key": workflow_key,
    }
```

### Pattern 2: Stage-Level Evaluation Hook

**What:** Inside `execute_workflow`, after each stage's skills run, call `evaluate_stage(stage, criteria, run_state)` and append findings to the workflow report instead of (or in addition to) the loose `issues[]` list.

**When to use:** When the workflow stage has `kind == "validate"` or when a criterion declares `stage_applicability` for that stage kind.

**Example:**
```python
# Source: extends services/workflow_orchestration.py execute_workflow()
for stage in workflow.stages:
    # ... existing skill execution ...
    stage_findings = evaluate_stage_findings(
        criteria=stage_applicable_criteria,
        context=stage_run_state,
        stage_key=stage.key,
        stage_kind=stage.kind,
    )
    persist_stage_findings(
        conn,
        run_id=context.run_id,
        stage_key=stage.key,
        findings=stage_findings,
    )
    stage_blocker_count = sum(1 for f in stage_findings if f.level == "blocker")
    if stage_blocker_count > 0:
        stage_status = "failed"
```

### Pattern 3: Evidence-Source Broadening for Execution-First

**What:** `execution_evidence_for_session` today reads only from `artifacts` (patch metadata `command` field) and `rtk_compression_events`. Phase 6 adds: tool_events of type `Bash` with non-zero output, workflow_execution_reports test/validate stage outputs, and explicit "execution probe" entries logged by hooks during the session.

**When to use:** Any code path that calls `evaluate_and_record` or `_evaluate_execution_first_verification`.

**Example:**
```python
# Source: extends bin/hook-stop.py execution_evidence_for_session()
def execution_evidence_for_session(conn, session_id):
    evidence = []
    # existing: artifacts + rtk_compression_events
    # NEW: tool_events Bash invocations
    rows = conn.execute(
        "SELECT payload_json FROM tool_events "
        "WHERE session_id = ? AND source_tool = 'claude-code' "
        "AND event_type IN ('Bash','TestRun') ORDER BY event_time",
        (session_id,),
    ).fetchall()
    for row in rows:
        payload = json.loads(row[0] or "{}")
        command = str(payload.get("command", "")).strip()
        if command:
            evidence.append(f"tool-event: {command[:200]}")
    # ... existing dedupe ...
    return deduped
```

### Anti-Patterns to Avoid

- **Inventing a new evaluator framework:** The existing `evaluators = {"criterion-id": handler_fn}` dispatch dict is clear and grep-able. A registry of evaluator classes would obscure call sites without adding power.
- **Embedding stage findings inside `workflow_execution_reports.report_json`:** Findings need to be queryable by criterion_id, level, and run_id for phase 7 delta scoring. Use a relational table.
- **Re-resolving criteria at session-close that were already resolved at session-start:** Persist the resolution on `briefing_packets` once and feed it forward. Re-resolution silently drifts when the registry version changes mid-run.
- **Letting `agentize.py`'s hardcoded `_standards()` and `_success_criteria()` lists diverge from the registry-driven resolution:** Phase 6 must converge `agentize` onto the same `resolve_task_standards()` call, otherwise the operator sees two different "standards" lists for the same task.
- **Implicit blocker promotion:** `evaluate_criterion` already promotes `warning` to `blocker` when `criterion.blocking == True`. Stage-level evaluation must use the same rule, not invent a per-stage promotion policy.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Criteria applicability rules | Custom matchers per workflow | `resolve_applicable_criteria` in `services/success_criteria.py` | Already handles task_types, domains, project, skill linkage with deduping. |
| Standards profile loading | Re-parsing `config/standards/registry.json` | `standards_health.load_registry()` | Already returns `(profile, [StandardDefinition,...])` with all metadata. |
| Per-criterion evaluator dispatch | New abstract base class | Extend the existing `evaluators = {...}` dict | Pattern is grep-able and used by ten different criteria today. |
| Run-scoped evaluation persistence | New SQLite tables | Extend `success_criteria_evaluations` + add sibling `success_criteria_stage_findings` | Pattern already established; mirror the schema. |
| JSON artifact persistence | New artifact root | Reuse `data/success-criteria/evaluations/` | Consumed by `aios contracts-audit` and `aios governance-audit` already. |
| Workflow stage iteration | Custom stage executor | Hook into `execute_workflow` in `services/workflow_orchestration.py` | Already iterates stages, dispatches skills, and collects validations. |
| Approval policy for evaluation blockers | New approval lifecycle | Use phase-5 `writeback_approval_policy` and `impact_scope` | Phase 5 already wired approval gates for high-impact mutations; evaluation blockers should emit writebacks tagged with the same policy classes. |

**Key insight:** Phase 6 is almost entirely about **wiring already-correct primitives** into stage boundaries and broadening evidence ingestion. The only net-new artifact is `success_criteria_stage_findings` plus the registry extensions that declare stage applicability.

## Common Pitfalls

### Pitfall 1: Resolution Drift Between Session-Start Preview and Session-Close Evaluation

**What goes wrong:** Today `hook-session-start.py` calls `preview_applicable_criteria` and shows them in the packet, but `hook-stop.py` re-derives criteria via `evaluate_and_record` (which calls `resolve_applicable_criteria` again). If the registry mutates between the two events, the operator sees one set of criteria during work and a different set at closeout.

**Why it happens:** Resolution is recomputed in two places instead of persisted on `briefing_packets`.

**How to avoid:** Persist the resolved criteria + standards onto `briefing_packets.selected_criteria_json` and `.selected_standards_json` at session start, and have `evaluate_and_record` consume those when present. Fall back to re-resolution only when the packet has no recorded resolution.

**Warning signs:** Closeout report shows criteria the operator never saw at session start, or success_criteria_evaluations.criteria_ids_json drifts from the packet's expected list.

### Pitfall 2: Execution-First Blockers Firing for Pure-Doc Sessions

**What goes wrong:** The current `_evaluate_execution_first_verification` requires execution evidence when `code_changes and not test_changes` (among other triggers). A session that only edits markdown but happens to set off the "core/shared logic" path marker (because the doc lives under `services/`) will be flagged as a blocker with no recourse.

**Why it happens:** Path markers (`/services/`, `/bin/`, `model`, etc.) trigger purely on substring presence; they do not check file extension before triggering.

**How to avoid:** Constrain execution-first path markers to combine with `_is_code_path` for the same files. Markdown / planning docs under `/services/` should not trip the "core/shared logic modification" trigger.

**Warning signs:** Doc-only sessions show `execution-first-verification` blocker in closeout report despite no code change.

### Pitfall 3: Standards Resolution Without Project Profile Binding

**What goes wrong:** `config/standards/registry.json` defines a single `aios-core` profile, and `project_standards_profiles` is supposed to bind each project to a profile with `attached_version` and `latest_version`. If a new project is added without an attachment row, `resolve_task_standards()` returns an empty standards list silently — making the operator think "no standards apply" when in reality "no standards profile was attached."

**Why it happens:** `project_standards_profiles` is keyed PRIMARY KEY on project_id; missing rows return no error.

**How to avoid:** `resolve_task_standards()` must surface a `resolution_status: "no_profile_attached"` warning when a project has no profile binding, so the resolver distinguishes "intentionally empty" from "misconfigured."

**Warning signs:** Two projects with identical task types resolve to different standards lists with no rationale visible in the packet.

### Pitfall 4: Stage Findings Without Evaluation Trigger

**What goes wrong:** If stage-level evaluation runs unconditionally on every stage kind, the noise overwhelms operators — `parse_request` stages have no real validation surface and will emit pass-only findings.

**Why it happens:** Naive "evaluate on every stage" loops add no signal.

**How to avoid:** Stage-level evaluation should run only when (a) `stage.kind == "validate"`, (b) the criterion declares `stage_applicability` matching the stage kind, or (c) a `required_validations` skill on the stage maps to a criterion via `skill-map.json`.

**Warning signs:** `success_criteria_stage_findings` rowcount explodes on every run, mostly with `level = "pass"` and no actionable signal.

### Pitfall 5: Findings Resolution State Becoming Stale

**What goes wrong:** Phase 5 already added `resolution_status`, `resolution_actor`, `resolution_rationale`, `resolution_evidence_json`, `resolved_at` columns to `success_criteria_findings`, but no surface today writes resolution rows. Stage findings will inherit the same columns and the same "no one ever marks them resolved" problem.

**Why it happens:** No CLI or hook command exists to transition findings from `open` to `accepted/resolved/waived/stale`.

**How to avoid:** Add an `aios criteria-finding resolve --id X --status accepted --rationale "..."` command as part of phase 6 task 02 or 03, so the lifecycle column actually transitions.

**Warning signs:** All findings remain in `resolution_status = 'open'` across all runs.

## Code Examples

Verified patterns from existing code:

### Loading Both Registries Together

```python
# Source: combines services/success_criteria.py:load_registry and
#         services/standards_health.py:load_registry
from services import success_criteria, standards_health

criteria_registry = success_criteria.load_registry()       # list[CriterionRecord]
skill_map = success_criteria.load_skill_map()              # dict[str, list[str]]
profile, standards = standards_health.load_registry()      # tuple[dict, list[StandardDefinition]]
```

### Resolving Criteria for a Task

```python
# Source: services/success_criteria.py:preview_applicable_criteria (verbatim usage)
preview = success_criteria.preview_applicable_criteria(
    project_id=project_id,
    project_name=project_name,
    objective=objective,
    prompt_classifications=["implement"],
    changed_files=["services/foo.py"],
    skills=["workflow"],
)
# preview["criteria"] -> list[{id, title, scope, blocking, path}]
# preview["context"]  -> {task_types, domains}
```

### Recording an Evaluation (Run-Scoped, Existing)

```python
# Source: bin/hook-stop.py line 614 (verbatim)
criteria_eval = evaluate_and_record(
    conn,
    project_id=row[1],
    project_name=project_name,
    run_id=linked_run_id,
    session_id=session_id,
    packet_id=linked_packet_id,
    objective=row[4],
    task_id=linked_run_id or session_id,
    trigger_kind="session_close",
    cwd=row[3],
    prompt_classifications=prompt_classifications,
    changed_files=criteria_changed_paths,
    execution_evidence=execution_evidence,
    used_legacy_link=used_legacy_link,
    accepted_tradeoffs=accepted_tradeoffs,
)
```

### Stage Iteration In Workflow Executor

```python
# Source: services/workflow_orchestration.py:execute_workflow (existing structure)
for stage in workflow.stages:
    stage_started = _now_iso()
    skill_reports = []
    stage_issues = []
    for skill_key in stage.required_skills:
        spec = skills[skill_key]
        output, validation = _execute_skill(spec, stage, state=run_state, context=context)
        # ...
        if validation is not None:
            validations.append(validation)
            if not validation.get("passed", False):
                stage_issues.extend(validation.get("issues", []))
    # PHASE 6 ADDS HERE: per-stage criteria evaluation + persistence
    stage_status = "completed" if not stage_issues else "failed"
```

### Workflow Execution Report Closeout (Phase 5 Pattern To Extend)

```python
# Source: bin/hook-stop.py line 658 (verbatim — phase 5 governed closeout)
closeout_summary = {
    "report_type": "governed_closeout",
    "run_id": linked_run_id,
    "checks_run": {
        "success_criteria_evaluation_id": criteria_eval["evaluation_id"],
        "standards_snapshot_id": standards_eval["snapshot_id"],
        "consistency_evaluation_id": consistency_eval_id,
    },
    "governance": {
        **governance_summary,
        "unresolved_follow_up_count": len(risk_items) + len(open_questions),
        "requires_review": pending_approval_count > 0
        or len(risk_items) > 0
        or len(open_questions) > 0,
    },
    # PHASE 6 ADDS: "stage_evaluations": [{stage_key, blocker_count, warning_count, finding_ids}]
}
```

### Approval Policy Class (Phase 5 Pattern To Reuse)

```python
# Source: bin/aios_orchestration_runtime.py:writeback_approval_policy
policy = writeback_approval_policy(
    workflow_key=workflow_key,
    impact_scope="standards-default",  # or "workflow-default", "global", etc.
    requires_approval=blocker_count > 0,
)
# Phase 6 reuses: when stage evaluation produces a blocker tied to a standard change,
# emit a writeback with the same policy class
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Free-form "validation issues" string lists per workflow stage | Structured `CriterionFinding` records with level/evidence/metadata | Phase 6 (this phase) | Findings become queryable, aggregatable, and feedable to phase 7 delta scoring. |
| Run-only evaluation at session_close | Stage-level + run-level evaluation | Phase 6 | Failures localize to a stage instead of collapsing into one blob. |
| Hardcoded `relevant_standards` strings in `services/agentize.py` | Registry-resolved standards via `resolve_task_standards()` | Phase 6 | Packet's standards list becomes auditable against `config/standards/registry.json`. |
| Execution-evidence ingestion from only `artifacts` + `rtk_compression_events` | Broadened to include `tool_events`, `workflow_execution_reports`, harness fixtures | Phase 6 | Reduces false-positive execution-first blockers for sessions that ran tests through a non-RTK path. |
| Approval gates only on writebacks | Approval gates also on standards-affecting evaluation blockers | Phase 6 | Aligns evaluation outcomes with phase 5 governance contract. |

**Deprecated/outdated:**
- `services/agentize.py:_standards()` and `:_success_criteria()` — these hardcoded lists should be retired in favor of registry-driven resolution. Mark deprecated, keep as fallback for one cycle, remove in phase 8.
- "Validation = required_validations list of skill keys" without criterion bindings — phase 6 supersedes by binding criteria to stages.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The five phase-6-named workflows (`audit-only`, `audit-and-implement`, `security review`, `test-first implementation`, `repo cleanup`) are intentionally **not yet** in `config/workflows/registry.json` — they live in `WORKFLOW_MATRIX.md` as "Planned" entries and phase 8 owns their stage contracts. Phase 6 binds standards to their **planned workflow_family** values so phase 8 can lift them straight in. | Architecture Patterns | If the user expected phase 6 to also CREATE these workflow entries (not just bind their standards), scope is too narrow and phase 6 risks delivering nothing executable for those families. Confirm in discuss-phase. |
| A2 | `briefing_packets.selected_criteria_json` and `.selected_standards_json` columns can be added via the existing `_ensure_column` pattern; the packet schema is mutation-tolerant. | Pattern 1 | If the briefing packet schema is frozen by a downstream consumer (e.g., aios-ui type contract), the persistence target needs to be a sibling table instead. |
| A3 | Adding `success_criteria_stage_findings` table is cheaper than embedding stage findings into `workflow_execution_reports` JSON. Phase 7 will benefit from a queryable table. | Anti-Patterns | If phase 7 ends up wanting per-stage aggregation only via JSON path queries, the table is over-engineering — but stdlib SQLite supports JSON1 functions, so even then no extra dep is needed. |
| A4 | Hooks (`hook-session-start.py`, `hook-stop.py`) remain the right enforcement points; no new hook is needed for phase 6. | Architectural Responsibility Map | If the user wants standards resolution wired into a **prompt-submit** moment (before the model is invoked at all), `bin/hook-prompt-submit.py` also needs extension. |

## Open Questions (RESOLVED)

1. **Should standards resolution include a "current snapshot of standards health" by default?**
   - What we know: `standards_health.py` produces per-project snapshots stored in `standards_health_snapshots`. The latest snapshot is already exposed by `_latest_standards_snapshot(conn)` in `aios_cli.py`.
   - What's unclear: Whether the **resolution** call (pre-execution) should include the project's latest health snapshot as advisory context, or whether snapshots stay purely a post-execution artifact.
   - Recommendation: Include snapshot-id as a reference in the resolution payload but do not block on it; treat snapshot freshness as a phase-7 concern.

2. **How aggressive should stage-level execution-first verification be?**
   - What we know: Today execution-first verification is a single global criterion evaluated once at session close.
   - What's unclear: Whether stages with `kind = "generate"` for implementation workflows should each independently require execution evidence, or whether one run-level pass is enough.
   - Recommendation: Keep execution-first as a **run-level** criterion in phase 6 (do not duplicate per stage). Add stage-level checks only for `validate` stages where the criterion explicitly opts in.

3. **Where do "accepted tradeoffs" get authored?**
   - What we know: `evaluate_and_record(accepted_tradeoffs=[...])` already accepts the list and persists it onto `success_criteria_evaluations.accepted_tradeoffs_json`. `hook-stop.py` reads them from `reason_json["accepted_tradeoffs"]`.
   - What's unclear: There is no surfaced UI or CLI today for an operator to declare a tradeoff during work; they only appear if the agent writes them into reason_json.
   - Recommendation: Add a thin `aios tradeoff record --run-id X --rationale "..."` CLI in phase 6 task 03, mirroring how phase 5 added governance commands. This unblocks future operator-driven blocker-acceptance flows.

4. **Should the `agentize.py` packet keep emitting hardcoded standards strings for one cycle as a compatibility layer, or switch immediately?**
   - What we know: `agentize.py` consumers downstream may rely on the existing hardcoded list shape.
   - What's unclear: Whether anyone except the `agentize_evaluations` table actually reads `selected_standards_json`.
   - Recommendation: Inline-replace in phase 6 task 01 (write registry-driven values into `relevant_standards` field), keep field name and shape stable for one cycle. Mark `_standards()` private function as deprecated in code comment.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All phase 6 work | ✓ | 3.12 (per pyproject.toml requires-python) | — |
| sqlite3 stdlib | Stage findings table, evaluations | ✓ | stdlib | — |
| ruff | Lint gate | Assumed (per Quality Ladder) | — | `pnpm`/CI fails fast if missing |
| basedpyright | Typecheck gate | Assumed | — | — |
| pytest | Test gate | ✓ (referenced as `uv run pytest` in phase 5 verification) | — | — |
| vulture | Dead-code report | Assumed | — | Report-only, non-blocking |
| `uv` runner | Used in phase 5 verification commands | Likely ✓ | — | Fall back to bare `python -m pytest` |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** None; all dependencies are in-tree or stdlib.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (Python 3.12) |
| Config file | `pyproject.toml` (ruff + basedpyright + vulture sections) — no `pytest.ini` or `[tool.pytest.ini_options]` block |
| Quick run command | `uv run pytest tests/test_success_criteria.py tests/test_orchestration_runtime.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| STND-01 | Resolution merges criteria + standards before execution | unit | `uv run pytest tests/test_success_criteria.py::test_resolve_task_standards_merges_criteria_and_standards -x` | ❌ Wave 0 (new test) |
| STND-01 | Resolution persisted on `briefing_packets` and consumed at closeout | integration | `uv run pytest tests/test_orchestration_runtime.py::test_packet_resolution_round_trip -x` | ❌ Wave 0 |
| STND-02 | Stage-level evaluation produces structured findings, not free-form `issues[]` | unit | `uv run pytest tests/test_orchestration_runtime.py::test_stage_evaluation_emits_findings -x` | ❌ Wave 0 |
| STND-02 | `agentize.py` packet pulls registry-resolved standards | unit | `uv run pytest tests/test_agentize.py::test_agentize_standards_come_from_registry -x` | ❌ Wave 0 |
| STND-03 | Execution-first ignores docs-only sessions under `services/` | unit | `uv run pytest tests/test_success_criteria.py::test_execution_first_skips_pure_doc_changes -x` | ❌ Wave 0 |
| STND-03 | Broadened evidence sources (tool_events Bash) feed the evaluator | integration | `uv run pytest tests/test_success_criteria.py::test_execution_first_accepts_tool_event_evidence -x` | ❌ Wave 0 |
| STND-04 | Stage findings survive session close as queryable rows + JSON artifact | integration | `uv run pytest tests/test_orchestration_runtime.py::test_stage_findings_persisted_to_db_and_artifact -x` | ❌ Wave 0 |
| STND-04 | Closeout report references stage findings under `governance.stage_evaluations` | integration | `uv run pytest tests/test_aios_cli.py::test_governance_audit_includes_stage_findings -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_success_criteria.py tests/test_orchestration_runtime.py tests/test_agentize.py tests/test_aios_cli.py -x -q && uv run ruff check services bin tests && uv run ruff format --check services bin tests && uv run basedpyright`
- **Per wave merge:** `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run basedpyright`
- **Phase gate:** Full suite green + governance-audit and contracts-audit both report `implemented_count = canonical_contract_count` for `EvaluationFinding`.

### Wave 0 Gaps
- [ ] Add fixtures for stage-evaluation in `tests/fixtures/harness/` mirroring the `passing-complete.json` shape but with explicit stage finding expectations.
- [ ] No new conftest.py needed — existing tests use direct `sqlite3.connect(":memory:")` and `_seed_minimal_runtime_tables` patterns.
- [ ] Framework install: not required; pytest + ruff + basedpyright already wired in `pyproject.toml`.

## Security Domain

> Phase 6 has no new authentication, session management, network surface, or cryptographic concerns. Security applicability is bounded to (a) how standards-affecting evaluation blockers are gated through phase-5 approval policy, and (b) the existing `security-review` success criterion's evaluation continuing to work.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — internal CLI / hook surface |
| V3 Session Management | no | n/a |
| V4 Access Control | partial | Phase-5 approval policy classes already gate standards-affecting writebacks; phase 6 extends to evaluation-driven writebacks |
| V5 Input Validation | yes | All registry JSON is parsed via `_load_json` with type guards; new resolution payload must validate criterion IDs against the registry |
| V6 Cryptography | no | n/a |
| V7 Error Handling | yes | Resolution must not silently drop standards when `project_standards_profiles` row is missing — surface `no_profile_attached` warning instead |
| V10 Malicious Code | partial | The `security-review` criterion already flags `.env` changes as blocker; phase 6 must preserve this behavior |
| V13 API & Web Service | no | n/a |

### Known Threat Patterns for Standards Evaluation

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Silent registry drift between session-start preview and session-close evaluation | Tampering | Persist resolution on briefing_packets; compare at close, log mismatches |
| Operator accepting a blocker without rationale | Repudiation | Phase-5 already requires `requires_owner` and `requires_review_date` in `waiver_policy`; reuse for stage findings |
| Standards waiver granted with no review date | Repudiation / Elevation of Privilege | Inherit `waiver_policy.max_days` from standards registry; reject waiver creation if not provided |
| Execution-first evidence forged via fake tool_event entries | Tampering | tool_events are written only by managed hooks (`hook-post-tool-use.py`); no operator write path |
| Evaluation finding lifecycle stuck in `open` forever | Information Disclosure | Add `aios criteria-finding resolve` CLI; surface stale-open count in `governance-audit` |

## Sources

### Primary (HIGH confidence)

- `services/success_criteria.py` (in-tree, lines 1-986) — full evaluator, registry loader, persistence pattern. [VERIFIED: read]
- `services/standards_health.py` (in-tree, lines 1-200) — standards registry loader, `StandardDefinition` shape, profile binding. [VERIFIED: read]
- `services/workflow_orchestration.py` (in-tree, lines 1-960) — stage iteration in `execute_workflow`, `required_validations` binding. [VERIFIED: read]
- `bin/hook-session-start.py` (in-tree, lines 220-300) — `preview_applicable_criteria` integration into session packet. [VERIFIED: read]
- `bin/hook-stop.py` (in-tree, lines 160-740) — `execution_evidence_for_session`, `evaluate_and_record` wiring, governed closeout summary. [VERIFIED: read]
- `config/success-criteria/registry.json` — 8 criteria, scope + applies_when rules. [VERIFIED: read]
- `config/success-criteria/skill-map.json` — 5 skill → criteria mappings. [VERIFIED: read]
- `config/standards/registry.json` — `aios-core` profile v2026.05.0 with 10 standards including `divergent_strategy_standard` and `command_center_operability`. [VERIFIED: read]
- `config/workflows/registry.json` — 6 current workflows: `academic_paper_v1`, `implementation-delivery`, `failure-recovery`, `divergent-strategy`, `personalized-humanizer`, `agentize`. [VERIFIED: read via jq]
- `.planning/WORKFLOW_MATRIX.md` — defines `audit-only`, `audit-and-implement`, `security review`, `test-first implementation`, `repo cleanup` as **planned** workflows, not yet in registry. [VERIFIED: read]
- `schema.sql` lines 544-720 — `success_criteria_evaluations`, `success_criteria_findings`, `standards_*` table layout. [VERIFIED: read]
- `.planning/phases/05-*/05-*-SUMMARY.md` — phase 5 shipped governance audit, approval policy classes, governance overview tRPC route. [VERIFIED: read]
- `.planning/phases/03-*/03-RESEARCH.md` and `04-*/04-RESEARCH.md` — confirm phase dependencies are landed. [VERIFIED: read]
- `tests/test_success_criteria.py` (148 lines) — test pattern for in-memory sqlite + `_seed_minimal_runtime_tables` helper. [VERIFIED: read]

### Secondary (MEDIUM confidence)

- `services/agentize.py` lines 280-310 — hardcoded `_standards()` and `_success_criteria()` produce static strings, not registry-resolved. [VERIFIED: read]
- `services/harness.py` line 332 — harness simulation already passes `execution_evidence` to `evaluate_and_record`, confirming the broadening path is well-trodden. [VERIFIED: read]
- `services/aios_cli.py` lines 2620-2772 — `_contracts_audit_payload` includes `EvaluationFinding` contract with `EVALUATION_FINDING_LIFECYCLE_STATES = ["open","accepted","resolved","waived","stale"]`. [VERIFIED: read]

### Tertiary (LOW confidence)

- None — this is an internal phase researched entirely against in-tree code and config; no external web sources required.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all surfaces are in-tree and read directly during research.
- Architecture: HIGH — pattern follows phase 3/4/5 conventions; no novel external dependencies.
- Pitfalls: HIGH — pitfalls 1-3 surfaced by reading the existing evaluator code; pitfalls 4-5 are forward-looking but grounded in observed schema state (resolution_status column exists but no writer).
- Workflow-family bindings (planned workflows): MEDIUM — confirmed planned-not-implemented in registry, but the exact stage shape for each planned workflow is owned by phase 8.

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (30 days — stable surfaces, but standards registry version `2026.05.0` could rev)
