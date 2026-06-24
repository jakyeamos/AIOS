# Expert Rubric Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `expert_rubric_remediation_v1`, a first-class AIOS workflow that compiles TMCP expertise into a rubric, audits evidence, writes remediation artifacts, and produces an optional implementation handoff.

**Architecture:** Add a focused `services/expert_rubric_remediation.py` module for schemas, deterministic profile selection, artifact rendering, and validation. Wire that module into the existing workflow executor through small skill-dispatch branches, then expose it through workflow/skill registry entries, routing, and a read-only `aios tmcp review-plan` CLI.

**Tech Stack:** Python 3.12, AIOS workflow registry JSON, existing TMCP runtime, existing `services.workflow_orchestration` executor, pytest, Ruff, BasedPyright, Vulture.

---

## File Structure

- Create: `services/expert_rubric_remediation.py`
  - Owns review artifact schemas, profile selection, rubric synthesis, audit validation, remediation planning, markdown rendering, and artifact writing.
- Create: `tests/test_expert_rubric_remediation.py`
  - Unit coverage for rubric synthesis, evidence requirements, remediation validation, artifact writing, and Soundscape-inspired visual-polish fixture behavior.
- Modify: `services/workflow_orchestration.py`
  - Imports the new service, adds expert-review keys to workflow artifacts, dispatches new workflow skills, and routes explicit rubric/remediation language correctly.
- Modify: `config/workflows/registry.json`
  - Adds `expert_rubric_remediation_v1` with stage keys from the spec and existing stage kinds.
- Modify: `config/workflows/skills.json`
  - Adds skill specs for expertise compilation, rubric synthesis, evidence auditing, remediation planning, handoff creation, and validation skills.
- Modify: `services/aios_cli.py`
  - Adds `aios tmcp review-plan` for read-only artifact generation.
- Modify: `tests/test_workflow_orchestration.py`
  - Adds registry, routing, and executor regression coverage.
- Modify: `tests/test_aios_cli.py`
  - Adds CLI JSON and artifact-write coverage.
- Create: `tests/fixtures/expert-rubric-remediation/soundscape-visual-polish-evidence.json`
  - Compact fixture for Analytics dashboard, FeedItem waveform randomness, landing hero product evidence, and profile card hierarchy.
- Modify: `.tracker/PROJECT_TRUTH.md`
  - Records the implemented workflow state and quality evidence after implementation completes.

## Task 1: Expert Review Service Skeleton And Validators

**Files:**
- Create: `services/expert_rubric_remediation.py`
- Create: `tests/test_expert_rubric_remediation.py`

- [ ] **Step 1: Write failing service validation tests**

Add this initial test file:

```python
from __future__ import annotations

import json
from pathlib import Path

from services.expert_rubric_remediation import (
    AUDIT_REPORT_SCHEMA,
    REMEDIATION_PLAN_SCHEMA,
    RUBRIC_SCHEMA,
    build_remediation_plan,
    synthesize_rubric,
    validate_audit_report,
    validate_remediation_plan,
    validate_rubric,
    write_review_artifacts,
)


def _visual_packet() -> dict[str, object]:
    return {
        "schema": "tmcp-runtime-packet-v0.1",
        "task_id": "visual_polish",
        "objective": "Review Soundscape UI polish and create a remediation plan",
        "project_path": "/tmp/soundscape-app",
        "selected_nodes": [
            "@task:visual_polish",
            "@module:saas_interaction_architecture",
            "@module:visual_polish_system",
            "@module:enterprise_saas_visual_polish",
            "@module:data_realism_polish",
        ],
        "skipped_nodes": [
            {"node": "@module:print_report_design", "reason": "No PDF/report export scope."}
        ],
        "behavior_atoms": ["ui_quality", "visual_verification"],
        "source_hashes": {},
        "candidate_scores": {},
        "traversal_fingerprint": "visual-fingerprint",
    }


def test_synthesize_rubric_preserves_tmcp_provenance() -> None:
    rubric = synthesize_rubric(
        packet=_visual_packet(),
        run_id="review-run-1",
        objective="Review Soundscape UI polish and create a remediation plan",
    )

    assert rubric["schema"] == RUBRIC_SCHEMA
    assert rubric["run_id"] == "review-run-1"
    assert len(rubric["dimensions"]) >= 5
    assert {dimension["id"] for dimension in rubric["dimensions"]} >= {
        "surface_hierarchy",
        "data_realism",
        "interaction_architecture",
    }
    assert all(dimension["source_nodes"] for dimension in rubric["dimensions"])
    assert validate_rubric(rubric)["passed"] is True


def test_validate_audit_report_rejects_finding_without_evidence() -> None:
    report = {
        "schema": AUDIT_REPORT_SCHEMA,
        "run_id": "review-run-1",
        "rubric": "rubric.json",
        "scores": [],
        "findings": [
            {
                "id": "finding-1",
                "severity": "blocker",
                "dimension_id": "data_realism",
                "summary": "Waveform bars are random during render.",
                "evidence": [],
                "recommended_fix": "Make waveform heights deterministic from stable input.",
            }
        ],
    }

    result = validate_audit_report(report)

    assert result["passed"] is False
    assert "finding-1 is missing evidence" in result["issues"]


def test_remediation_plan_requires_verification() -> None:
    plan = {
        "schema": REMEDIATION_PLAN_SCHEMA,
        "run_id": "review-run-1",
        "slices": [
            {
                "id": "slice-1",
                "title": "Stabilize feed waveform",
                "scope": ["packages/web/src/components/feed/FeedItem.tsx"],
                "rationale": "Random visual data undermines trust and can cause hydration drift.",
                "expected_impact": "Stable rating card rendering.",
                "risk": "Low; local UI rendering behavior.",
                "verification": [],
                "follow_up_workflow": "implementation-delivery",
            }
        ],
        "deferred_scope": [],
    }

    result = validate_remediation_plan(plan)

    assert result["passed"] is False
    assert "slice-1 is missing verification" in result["issues"]


def test_write_review_artifacts_creates_expected_files(tmp_path: Path) -> None:
    packet = _visual_packet()
    rubric = synthesize_rubric(packet=packet, run_id="review-run-1", objective=str(packet["objective"]))
    audit = {
        "schema": AUDIT_REPORT_SCHEMA,
        "run_id": "review-run-1",
        "rubric": "rubric.json",
        "scores": [
            {
                "dimension_id": "data_realism",
                "score": 1,
                "confidence": "high",
                "evidence": ["packages/web/src/components/feed/FeedItem.tsx:427"],
                "gaps": [],
            }
        ],
        "findings": [
            {
                "id": "finding-data-realism-1",
                "severity": "blocker",
                "dimension_id": "data_realism",
                "summary": "Feed waveform uses Math.random during render.",
                "evidence": ["packages/web/src/components/feed/FeedItem.tsx:427"],
                "recommended_fix": "Derive waveform heights from stable rating data.",
            }
        ],
    }
    remediation = build_remediation_plan(audit_report=audit, run_id="review-run-1")

    paths = write_review_artifacts(
        output_dir=tmp_path,
        expertise_packet=packet,
        rubric=rubric,
        audit_report=audit,
        remediation_plan=remediation,
        implementation_handoff=None,
    )

    assert paths["expertise_packet"].name == "expertise-packet.json"
    assert paths["rubric_json"].exists()
    assert paths["rubric_markdown"].exists()
    assert paths["audit_report_json"].exists()
    assert paths["remediation_plan_markdown"].exists()
    assert json.loads(paths["rubric_json"].read_text(encoding="utf-8"))["schema"] == RUBRIC_SCHEMA
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_expert_rubric_remediation.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.expert_rubric_remediation'`.

- [ ] **Step 3: Create service module with schemas, synthesis, validation, and writers**

Create `services/expert_rubric_remediation.py` with these public functions and constants:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RUBRIC_SCHEMA = "aios-expert-rubric-v0.1"
AUDIT_REPORT_SCHEMA = "aios-expert-audit-report-v0.1"
REMEDIATION_PLAN_SCHEMA = "aios-expert-remediation-plan-v0.1"
IMPLEMENTATION_HANDOFF_SCHEMA = "aios-expert-implementation-handoff-v0.1"

ValidationResult = dict[str, Any]


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _selected_nodes(packet: dict[str, Any]) -> list[str]:
    return [str(node) for node in packet.get("selected_nodes", []) if str(node)]


def _profile_id(packet: dict[str, Any]) -> str:
    nodes = " ".join(_selected_nodes(packet)).lower()
    task_id = str(packet.get("task_id", "")).lower()
    if "visual_polish" in task_id or "visual_polish" in nodes:
        return "visual_polish"
    if any(term in nodes or term in task_id for term in ("security", "privacy", "tool_safety")):
        return "security_privacy"
    if any(term in nodes or term in task_id for term in ("developer", "command_discovery", "docs")):
        return "developer_experience"
    return "general_review"


def _dimension(
    *,
    dimension_id: str,
    name: str,
    weight: int,
    expectations: list[str],
    questions: list[str],
    source_nodes: list[str],
    pass_threshold: int = 3,
) -> dict[str, Any]:
    return {
        "id": dimension_id,
        "name": name,
        "weight": weight,
        "scale": "0-4",
        "pass_threshold": pass_threshold,
        "evidence_expectations": expectations,
        "review_questions": questions,
        "source_nodes": source_nodes,
    }


def _profile_dimensions(profile_id: str, source_nodes: list[str]) -> list[dict[str, Any]]:
    fallback_nodes = source_nodes or ["@task:agent_workflow"]
    if profile_id == "visual_polish":
        return [
            _dimension(
                dimension_id="surface_hierarchy",
                name="Surface Hierarchy",
                weight=4,
                expectations=["File, screen, or screenshot evidence showing dominant and supporting regions."],
                questions=["Is there one dominant work region?", "Are cards used only where they frame real repeated objects?"],
                source_nodes=[node for node in fallback_nodes if "visual" in node or "saas" in node] or fallback_nodes,
            ),
            _dimension(
                dimension_id="interaction_architecture",
                name="Interaction Architecture",
                weight=4,
                expectations=["Evidence for containers, loading states, empty states, overlays, and primary actions."],
                questions=["Does the container match the user task?", "Are empty/loading/error states decision-useful?"],
                source_nodes=[node for node in fallback_nodes if "interaction" in node or "saas" in node] or fallback_nodes,
            ),
            _dimension(
                dimension_id="data_realism",
                name="Data Realism",
                weight=4,
                expectations=["Evidence for source, freshness, deterministic data, and non-vanity metrics."],
                questions=["Are metrics credible?", "Are visualizations driven by stable data rather than decoration?"],
                source_nodes=[node for node in fallback_nodes if "data_realism" in node] or fallback_nodes,
            ),
            _dimension(
                dimension_id="product_evidence",
                name="Product Evidence",
                weight=3,
                expectations=["Evidence that the first screen shows product, media, object, or real state."],
                questions=["Can a viewer understand the actual product from the first screen?", "Is decoration replacing product proof?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="design_system_fit",
                name="Design System Fit",
                weight=3,
                expectations=["Evidence for tokens, component conventions, typography, spacing, and state consistency."],
                questions=["Does the surface follow local tokens?", "Are raw utility colors or decorative defaults leaking through?"],
                source_nodes=fallback_nodes,
            ),
        ]
    if profile_id == "security_privacy":
        return [
            _dimension(
                dimension_id="secret_exposure",
                name="Secret Exposure",
                weight=4,
                expectations=["Evidence for env, logs, fixtures, configs, and generated artifacts touching secrets."],
                questions=["Can credentials leak through logs or committed files?", "Are sensitive values redacted?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="permission_boundary",
                name="Permission Boundary",
                weight=4,
                expectations=["Evidence for file, network, auth, database, and tool side-effect boundaries."],
                questions=["Are mutations explicit?", "Are privileged operations approval-gated?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="data_flow_privacy",
                name="Data Flow Privacy",
                weight=4,
                expectations=["Evidence for inputs, persistence, retention, and outbound data flow."],
                questions=["Is sensitive data minimized?", "Can retained data be explained and audited?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="supply_chain",
                name="Supply Chain",
                weight=3,
                expectations=["Evidence for dependency changes, lockfiles, install commands, and provenance."],
                questions=["Are dependencies justified?", "Do lockfiles and package managers match repo policy?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="security_verification",
                name="Security Verification",
                weight=3,
                expectations=["Evidence for tests, scans, or review commands tied to the security concern."],
                questions=["Was the relevant risky path executed or checked?", "Are residual risks documented?"],
                source_nodes=fallback_nodes,
            ),
        ]
    if profile_id == "developer_experience":
        return [
            _dimension(
                dimension_id="command_discoverability",
                name="Command Discoverability",
                weight=4,
                expectations=["Evidence for setup, test, lint, typecheck, build, and local run commands."],
                questions=["Can a new developer find the correct commands?", "Do docs match actual scripts?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="validation_loop",
                name="Validation Loop",
                weight=4,
                expectations=["Evidence for fast targeted checks and complete release checks."],
                questions=["Is the inner loop fast enough?", "Are failures actionable?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="interface_clarity",
                name="Interface Clarity",
                weight=3,
                expectations=["Evidence for API, CLI, schema, errors, and examples."],
                questions=["Are public interfaces predictable?", "Can errors guide the next action?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="onboarding_path",
                name="Onboarding Path",
                weight=3,
                expectations=["Evidence for README, examples, seed data, fixtures, or guided first run."],
                questions=["Can a first run succeed?", "Are setup assumptions explicit?"],
                source_nodes=fallback_nodes,
            ),
            _dimension(
                dimension_id="maintenance_signal",
                name="Maintenance Signal",
                weight=3,
                expectations=["Evidence for ownership, freshness, health notes, and known blockers."],
                questions=["Can maintainers see project health?", "Are stale or failing checks disclosed?"],
                source_nodes=fallback_nodes,
            ),
        ]
    return [
        _dimension(
            dimension_id="source_grounding",
            name="Source Grounding",
            weight=4,
            expectations=["Evidence that findings cite concrete local or user-provided sources."],
            questions=["Is each claim grounded?", "Are skipped scopes explicit?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="risk_priority",
            name="Risk Priority",
            weight=4,
            expectations=["Evidence that blockers, warnings, and observations are separated."],
            questions=["Are correctness and user-impact risks first?", "Are preferences separated from defects?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="verification_readiness",
            name="Verification Readiness",
            weight=4,
            expectations=["Evidence that remediation can be verified with commands or manual checks."],
            questions=["Can the next worker know when a slice is done?", "Are residual risks visible?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="scope_control",
            name="Scope Control",
            weight=3,
            expectations=["Evidence for reviewed scope, deferred scope, and explicit gaps."],
            questions=["Is the reviewed surface bounded?", "Are unreviewed areas named?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="remediation_sequence",
            name="Remediation Sequence",
            weight=3,
            expectations=["Evidence that fixes are ordered into coherent implementation slices."],
            questions=["Can slices be committed independently?", "Does the sequence reduce risk first?"],
            source_nodes=fallback_nodes,
        ),
    ]


def synthesize_rubric(*, packet: dict[str, Any], run_id: str, objective: str) -> dict[str, Any]:
    selected_nodes = _selected_nodes(packet)
    return {
        "schema": RUBRIC_SCHEMA,
        "run_id": run_id,
        "objective": objective,
        "source_packet": "expertise-packet.json",
        "profile": _profile_id(packet),
        "selected_nodes": selected_nodes,
        "skipped_nodes": packet.get("skipped_nodes", []),
        "dimensions": _profile_dimensions(_profile_id(packet), selected_nodes),
    }


def validate_rubric(rubric: dict[str, Any]) -> ValidationResult:
    issues: list[str] = []
    dimensions = rubric.get("dimensions")
    if rubric.get("schema") != RUBRIC_SCHEMA:
        issues.append("Rubric schema is invalid")
    if not isinstance(dimensions, list) or not dimensions:
        issues.append("Rubric has no dimensions")
    else:
        for dimension in dimensions:
            dimension_id = str(dimension.get("id", ""))
            if not dimension_id:
                issues.append("Rubric dimension is missing id")
            if not dimension.get("source_nodes"):
                issues.append(f"{dimension_id} is missing source_nodes")
            if not dimension.get("evidence_expectations"):
                issues.append(f"{dimension_id} is missing evidence_expectations")
    return {"validation_key": "rubric_dimensions_present", "passed": not issues, "issues": issues}


def validate_audit_report(report: dict[str, Any]) -> ValidationResult:
    issues: list[str] = []
    if report.get("schema") != AUDIT_REPORT_SCHEMA:
        issues.append("Audit report schema is invalid")
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        issues.append("Audit report findings must be a list")
    else:
        for finding in findings:
            finding_id = str(finding.get("id", "finding"))
            evidence = finding.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                issues.append(f"{finding_id} is missing evidence")
    return {"validation_key": "findings_have_evidence", "passed": not issues, "issues": issues}


def build_remediation_plan(*, audit_report: dict[str, Any], run_id: str) -> dict[str, Any]:
    slices = []
    for index, finding in enumerate(audit_report.get("findings", []), start=1):
        finding_id = str(finding.get("id", f"finding-{index}"))
        slices.append(
            {
                "id": f"slice-{index}",
                "title": str(finding.get("summary", finding_id))[:80],
                "scope": list(finding.get("evidence", [])),
                "rationale": str(finding.get("summary", "")),
                "expected_impact": str(finding.get("recommended_fix", "")),
                "risk": "Review scope is limited to cited evidence; verify neighboring call sites before editing.",
                "verification": ["Run targeted tests or manual checks covering the cited evidence."],
                "follow_up_workflow": "implementation-delivery",
                "source_findings": [finding_id],
            }
        )
    return {
        "schema": REMEDIATION_PLAN_SCHEMA,
        "run_id": run_id,
        "slices": slices,
        "deferred_scope": list(audit_report.get("deferred_scope", [])),
    }


def validate_remediation_plan(plan: dict[str, Any]) -> ValidationResult:
    issues: list[str] = []
    if plan.get("schema") != REMEDIATION_PLAN_SCHEMA:
        issues.append("Remediation plan schema is invalid")
    slices = plan.get("slices", [])
    if not isinstance(slices, list):
        issues.append("Remediation slices must be a list")
    else:
        for item in slices:
            slice_id = str(item.get("id", "slice"))
            verification = item.get("verification")
            if not isinstance(verification, list) or not verification:
                issues.append(f"{slice_id} is missing verification")
    return {"validation_key": "remediation_has_verification", "passed": not issues, "issues": issues}


def render_rubric_markdown(rubric: dict[str, Any]) -> str:
    lines = [f"# Expert Rubric: {rubric['objective']}", "", f"Profile: `{rubric['profile']}`", ""]
    for dimension in rubric["dimensions"]:
        lines.extend(
            [
                f"## {dimension['name']}",
                "",
                f"- ID: `{dimension['id']}`",
                f"- Weight: {dimension['weight']}",
                f"- Pass threshold: {dimension['pass_threshold']}/4",
                f"- Source nodes: {', '.join(dimension['source_nodes'])}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_audit_markdown(report: dict[str, Any]) -> str:
    lines = [f"# Expert Audit Report: {report['run_id']}", ""]
    lines.append("## Scores")
    for score in report.get("scores", []):
        lines.append(f"- `{score['dimension_id']}`: {score['score']}/4 ({score['confidence']} confidence)")
    lines.extend(["", "## Findings"])
    for finding in report.get("findings", []):
        lines.append(f"- [{finding['severity']}] {finding['summary']} Evidence: {', '.join(finding['evidence'])}")
    return "\n".join(lines).rstrip() + "\n"


def render_remediation_markdown(plan: dict[str, Any]) -> str:
    lines = [f"# Remediation Plan: {plan['run_id']}", ""]
    if not plan.get("slices"):
        lines.append("No remediation slices were generated from the current evidence.")
    for item in plan.get("slices", []):
        lines.extend(
            [
                f"## {item['id']}: {item['title']}",
                "",
                f"- Scope: {', '.join(item['scope'])}",
                f"- Rationale: {item['rationale']}",
                f"- Expected impact: {item['expected_impact']}",
                f"- Risk: {item['risk']}",
                f"- Verification: {', '.join(item['verification'])}",
                f"- Follow-up workflow: `{item['follow_up_workflow']}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_handoff_markdown(handoff: dict[str, Any]) -> str:
    selected = handoff.get("selected_slice") or {}
    lines = [
        f"# Implementation Handoff: {handoff['run_id']}",
        "",
        f"- Requires user approval: {handoff['requires_user_approval']}",
        f"- Follow-up workflow: `{handoff['follow_up_workflow']}`",
        f"- Selected slice: `{handoff.get('selected_slice_id')}`",
        "",
    ]
    if selected:
        lines.extend(
            [
                "## Selected Slice",
                "",
                f"- Title: {selected.get('title')}",
                f"- Scope: {', '.join(selected.get('scope', []))}",
                f"- Verification: {', '.join(selected.get('verification', []))}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_review_artifacts(
    *,
    output_dir: Path,
    expertise_packet: dict[str, Any],
    rubric: dict[str, Any],
    audit_report: dict[str, Any],
    remediation_plan: dict[str, Any],
    implementation_handoff: dict[str, Any] | None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "expertise_packet": output_dir / "expertise-packet.json",
        "rubric_json": output_dir / "rubric.json",
        "rubric_markdown": output_dir / "rubric.md",
        "audit_report_json": output_dir / "audit-report.json",
        "audit_report_markdown": output_dir / "audit-report.md",
        "remediation_plan_json": output_dir / "remediation-plan.json",
        "remediation_plan_markdown": output_dir / "remediation-plan.md",
    }
    _json_dump(paths["expertise_packet"], expertise_packet)
    _json_dump(paths["rubric_json"], rubric)
    paths["rubric_markdown"].write_text(render_rubric_markdown(rubric), encoding="utf-8")
    _json_dump(paths["audit_report_json"], audit_report)
    paths["audit_report_markdown"].write_text(render_audit_markdown(audit_report), encoding="utf-8")
    _json_dump(paths["remediation_plan_json"], remediation_plan)
    paths["remediation_plan_markdown"].write_text(
        render_remediation_markdown(remediation_plan),
        encoding="utf-8",
    )
    if implementation_handoff is not None:
        handoff_json = output_dir / "implementation-handoff.json"
        handoff_markdown = output_dir / "implementation-handoff.md"
        _json_dump(handoff_json, implementation_handoff)
        handoff_markdown.write_text(
            render_handoff_markdown(implementation_handoff),
            encoding="utf-8",
        )
        paths["implementation_handoff_json"] = handoff_json
        paths["implementation_handoff_markdown"] = handoff_markdown
    return paths
```

- [ ] **Step 4: Run service tests**

Run:

```bash
uv run pytest tests/test_expert_rubric_remediation.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit service skeleton**

```bash
git add services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py
git commit -m "Add expert rubric remediation service"
```

## Task 2: Evidence Fixture And Audit/Remediation Builders

**Files:**
- Modify: `services/expert_rubric_remediation.py`
- Modify: `tests/test_expert_rubric_remediation.py`
- Create: `tests/fixtures/expert-rubric-remediation/soundscape-visual-polish-evidence.json`

- [ ] **Step 1: Add Soundscape-inspired evidence fixture**

Create `tests/fixtures/expert-rubric-remediation/soundscape-visual-polish-evidence.json`:

```json
[
  {
    "dimension_id": "data_realism",
    "severity": "blocker",
    "summary": "Feed rating card waveform uses Math.random during render.",
    "evidence": ["packages/web/src/components/feed/FeedItem.tsx:427"],
    "recommended_fix": "Derive waveform heights from stable rating or track data."
  },
  {
    "dimension_id": "product_evidence",
    "severity": "warning",
    "summary": "Landing hero relies on decorative blur without first-screen product evidence.",
    "evidence": ["packages/web/src/features/landing/components/Hero.tsx:33"],
    "recommended_fix": "Add a real app, media, or product-state preview in the first viewport."
  },
  {
    "dimension_id": "surface_hierarchy",
    "severity": "warning",
    "summary": "Profile refresh stacks equal raised cards instead of one dominant profile region.",
    "evidence": ["packages/web/src/app/[locale]/(main)/profile/[id]/page-refresh.tsx:108"],
    "recommended_fix": "Consolidate the profile header and stats into one dominant region with supporting modules."
  },
  {
    "dimension_id": "interaction_architecture",
    "severity": "warning",
    "summary": "Analytics dashboard labels insights but does not expose freshness, owner, exception state, or next action.",
    "evidence": ["packages/web/src/features/analytics/components/AnalyticsDashboard.tsx:71"],
    "recommended_fix": "Add decision context, source/freshness metadata, exception state, and next action."
  }
]
```

- [ ] **Step 2: Write failing fixture tests**

Append to `tests/test_expert_rubric_remediation.py`:

```python
def test_soundscape_fixture_builds_evidence_backed_audit_and_plan() -> None:
    fixture_path = ROOT / "tests" / "fixtures" / "expert-rubric-remediation" / "soundscape-visual-polish-evidence.json"
    evidence_items = json.loads(fixture_path.read_text(encoding="utf-8"))
    packet = _visual_packet()
    rubric = synthesize_rubric(packet=packet, run_id="soundscape-review", objective=str(packet["objective"]))

    audit = build_audit_report(rubric=rubric, evidence_items=evidence_items, run_id="soundscape-review")
    remediation = build_remediation_plan(audit_report=audit, run_id="soundscape-review")
    handoff = build_implementation_handoff(
        remediation_plan=remediation,
        run_id="soundscape-review",
        selected_slice_id="slice-1",
    )

    assert validate_audit_report(audit)["passed"] is True
    assert validate_remediation_plan(remediation)["passed"] is True
    assert audit["findings"][0]["evidence"] == ["packages/web/src/components/feed/FeedItem.tsx:427"]
    assert remediation["slices"][0]["follow_up_workflow"] == "implementation-delivery"
    assert handoff["selected_slice_id"] == "slice-1"
    assert handoff["requires_user_approval"] is True
```

Update the existing import block near the top of `tests/test_expert_rubric_remediation.py` to include:

```python
    build_audit_report,
    build_implementation_handoff,
```

Add `ROOT` below the imports:

```python
ROOT = Path(__file__).resolve().parents[1]
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_expert_rubric_remediation.py::test_soundscape_fixture_builds_evidence_backed_audit_and_plan -q
```

Expected: FAIL because `build_audit_report` and `build_implementation_handoff` are not defined.

- [ ] **Step 4: Implement audit and handoff builders**

Add to `services/expert_rubric_remediation.py`:

```python
def build_audit_report(
    *,
    rubric: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    dimension_ids = {str(dimension["id"]) for dimension in rubric.get("dimensions", [])}
    findings: list[dict[str, Any]] = []
    scores_by_dimension: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(evidence_items, start=1):
        dimension_id = str(item.get("dimension_id", "source_grounding"))
        if dimension_id not in dimension_ids:
            dimension_id = next(iter(sorted(dimension_ids)), "source_grounding")
        evidence = [str(ref) for ref in item.get("evidence", []) if str(ref)]
        finding = {
            "id": f"finding-{index}",
            "severity": str(item.get("severity", "warning")),
            "dimension_id": dimension_id,
            "summary": str(item.get("summary", "")),
            "evidence": evidence,
            "recommended_fix": str(item.get("recommended_fix", "")),
        }
        findings.append(finding)
        severity = finding["severity"]
        score = 1 if severity == "blocker" else 2 if severity == "warning" else 3
        existing = scores_by_dimension.get(dimension_id)
        if existing is None or score < int(existing["score"]):
            scores_by_dimension[dimension_id] = {
                "dimension_id": dimension_id,
                "score": score,
                "confidence": "high" if evidence else "low",
                "evidence": evidence,
                "gaps": [] if evidence else ["Finding has no evidence."],
            }
    for dimension in rubric.get("dimensions", []):
        dimension_id = str(dimension["id"])
        scores_by_dimension.setdefault(
            dimension_id,
            {
                "dimension_id": dimension_id,
                "score": 3,
                "confidence": "low",
                "evidence": [],
                "gaps": ["No evidence item supplied for this dimension."],
            },
        )
    return {
        "schema": AUDIT_REPORT_SCHEMA,
        "run_id": run_id,
        "rubric": "rubric.json",
        "scores": list(scores_by_dimension.values()),
        "findings": findings,
    }


def build_implementation_handoff(
    *,
    remediation_plan: dict[str, Any],
    run_id: str,
    selected_slice_id: str | None,
) -> dict[str, Any]:
    selected = None
    for item in remediation_plan.get("slices", []):
        if str(item.get("id")) == selected_slice_id:
            selected = item
            break
    return {
        "schema": IMPLEMENTATION_HANDOFF_SCHEMA,
        "run_id": run_id,
        "selected_slice_id": selected_slice_id,
        "requires_user_approval": True,
        "follow_up_workflow": "implementation-delivery",
        "selected_slice": selected,
        "artifact_inputs": [
            "expertise-packet.json",
            "rubric.json",
            "audit-report.json",
            "remediation-plan.json",
        ],
    }
```

- [ ] **Step 5: Run fixture tests**

Run:

```bash
uv run pytest tests/test_expert_rubric_remediation.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit fixture and builders**

```bash
git add services/expert_rubric_remediation.py tests/test_expert_rubric_remediation.py tests/fixtures/expert-rubric-remediation/soundscape-visual-polish-evidence.json
git commit -m "Add expert review fixture builders"
```

## Task 3: Workflow Skill Dispatch And Report Artifacts

**Files:**
- Modify: `services/workflow_orchestration.py`
- Modify: `tests/test_workflow_orchestration.py`

- [ ] **Step 1: Write failing executor test**

Append to `tests/test_workflow_orchestration.py`:

```python
def test_expert_review_workflow_executes_with_artifacts(tmp_path: Path) -> None:
    packet = compile_tmcp_packet(
        objective="Review UI polish with TMCP and create a rubric remediation plan",
        project_path=str(tmp_path),
        phase="planning",
        domain="ui_polish",
    )
    context = WorkflowExecutionContext(
        objective="Review UI polish with TMCP and create a rubric remediation plan",
        workflow_key="expert_rubric_remediation_v1",
        repo_path=str(tmp_path),
        run_id="review-run-workflow",
        tmcp_packet=packet,
        evidence_items=(
            {
                "dimension_id": "source_grounding",
                "severity": "warning",
                "summary": "Review needs evidence-backed findings.",
                "evidence": ["docs/superpowers/specs/2026-06-24-expert-rubric-remediation-design.md:1"],
                "recommended_fix": "Keep all findings tied to local evidence.",
            },
        ),
        selected_slice_id="slice-1",
    )

    report = execute_workflow(context)

    assert report["status"] == "completed"
    artifacts = report["artifacts"]
    assert artifacts["expert_rubric"]["schema"] == "aios-expert-rubric-v0.1"
    assert artifacts["expert_audit_report"]["findings"][0]["evidence"]
    assert artifacts["expert_remediation_plan"]["slices"][0]["verification"]
    assert artifacts["expert_implementation_handoff"]["requires_user_approval"] is True
    assert Path(artifacts["expert_review_artifact_paths"]["rubric_json"]).exists()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q
```

Expected: FAIL because `WorkflowExecutionContext` does not accept `evidence_items`.

- [ ] **Step 3: Extend context and imports**

In `services/workflow_orchestration.py`, add this import block:

```python
from services.expert_rubric_remediation import (
    build_audit_report,
    build_implementation_handoff,
    build_remediation_plan,
    synthesize_rubric,
    validate_audit_report,
    validate_remediation_plan,
    validate_rubric,
    write_review_artifacts,
)
```

Extend `WorkflowExecutionContext`:

```python
@dataclass(frozen=True)
class WorkflowExecutionContext:
    objective: str
    workflow_key: str
    surface: str = "codex"
    repo_path: str | None = None
    vault_root: str | None = None
    prompt_registry_path: str | None = None
    run_id: str | None = None
    invocation_id: str | None = None
    session_id: str | None = None
    tmcp_packet: dict[str, Any] | None = None
    evidence_items: tuple[dict[str, Any], ...] = ()
    selected_slice_id: str | None = None
```

Seed `run_state` in `execute_workflow`:

```python
        "tmcp_packet": context.tmcp_packet,
        "review_evidence_items": list(context.evidence_items),
        "selected_slice_id": context.selected_slice_id,
```

- [ ] **Step 4: Add expert skill dispatch**

Inside `_execute_skill`, before the `scope_check` branch, add:

```python
    if skill.key == "tmcp_expertise_compiler":
        packet = state.get("tmcp_packet")
        if not isinstance(packet, dict):
            raise ValueError("tmcp_expertise_compiler requires context.tmcp_packet")
        state["expertise_packet"] = packet
        return {"expertise_packet": packet}, {"validation_key": "tmcp_packet_compiled", "passed": True, "issues": []}

    if skill.key == "expert_rubric_synthesizer":
        packet = state.get("expertise_packet") or state.get("tmcp_packet")
        if not isinstance(packet, dict):
            raise ValueError("expert_rubric_synthesizer requires expertise_packet")
        rubric = synthesize_rubric(
            packet=packet,
            run_id=context.run_id or "expert-review-preview",
            objective=context.objective,
        )
        state["expert_rubric"] = rubric
        return {"rubric": rubric}, None

    if skill.key == "expert_evidence_auditor":
        rubric = state.get("expert_rubric")
        if not isinstance(rubric, dict):
            raise ValueError("expert_evidence_auditor requires expert_rubric")
        audit_report = build_audit_report(
            rubric=rubric,
            evidence_items=list(state.get("review_evidence_items", [])),
            run_id=context.run_id or "expert-review-preview",
        )
        state["expert_audit_report"] = audit_report
        return {"audit_report": audit_report}, None

    if skill.key == "expert_remediation_planner":
        audit_report = state.get("expert_audit_report")
        if not isinstance(audit_report, dict):
            raise ValueError("expert_remediation_planner requires expert_audit_report")
        remediation_plan = build_remediation_plan(
            audit_report=audit_report,
            run_id=context.run_id or "expert-review-preview",
        )
        state["expert_remediation_plan"] = remediation_plan
        return {"remediation_plan": remediation_plan}, None

    if skill.key == "expert_implementation_handoff_builder":
        remediation_plan = state.get("expert_remediation_plan")
        if not isinstance(remediation_plan, dict):
            raise ValueError("expert_implementation_handoff_builder requires expert_remediation_plan")
        handoff = build_implementation_handoff(
            remediation_plan=remediation_plan,
            run_id=context.run_id or "expert-review-preview",
            selected_slice_id=context.selected_slice_id,
        )
        output_dir = Path(context.repo_path or ".") / ".aios" / "reviews" / (context.run_id or "expert-review-preview")
        paths = write_review_artifacts(
            output_dir=output_dir,
            expertise_packet=state.get("expertise_packet") or state.get("tmcp_packet") or {},
            rubric=state.get("expert_rubric") or {},
            audit_report=state.get("expert_audit_report") or {},
            remediation_plan=remediation_plan,
            implementation_handoff=handoff,
        )
        state["expert_implementation_handoff"] = handoff
        state["expert_review_artifact_paths"] = {key: str(path) for key, path in paths.items()}
        return {"implementation_handoff": handoff, "artifact_paths": state["expert_review_artifact_paths"]}, None

    if skill.key == "tmcp_packet_compiled":
        packet = state.get("expertise_packet") or state.get("tmcp_packet")
        passed = isinstance(packet, dict) and bool(packet.get("selected_nodes"))
        issues = [] if passed else ["TMCP expertise packet is missing selected nodes."]
        return {}, {"validation_key": "tmcp_packet_compiled", "passed": passed, "issues": issues}

    if skill.key == "rubric_dimensions_present":
        rubric = state.get("expert_rubric")
        return {}, validate_rubric(rubric if isinstance(rubric, dict) else {})

    if skill.key == "findings_have_evidence":
        audit_report = state.get("expert_audit_report")
        return {}, validate_audit_report(audit_report if isinstance(audit_report, dict) else {})

    if skill.key == "remediation_has_verification":
        remediation_plan = state.get("expert_remediation_plan")
        return {}, validate_remediation_plan(remediation_plan if isinstance(remediation_plan, dict) else {})
```

- [ ] **Step 5: Expose expert artifacts in execution report**

In the report `artifacts` dict inside `execute_workflow`, add:

```python
            "expertise_packet": run_state.get("expertise_packet"),
            "expert_rubric": run_state.get("expert_rubric"),
            "expert_audit_report": run_state.get("expert_audit_report"),
            "expert_remediation_plan": run_state.get("expert_remediation_plan"),
            "expert_implementation_handoff": run_state.get("expert_implementation_handoff"),
            "expert_review_artifact_paths": run_state.get("expert_review_artifact_paths", {}),
```

- [ ] **Step 6: Run focused executor test**

Run:

```bash
uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q
```

Expected: FAIL with `Unknown workflow key: expert_rubric_remediation_v1`. That confirms dispatch exists and registry work is next.

- [ ] **Step 7: Commit dispatch changes**

```bash
git add services/workflow_orchestration.py tests/test_workflow_orchestration.py
git commit -m "Wire expert review workflow dispatch"
```

## Task 4: Workflow And Skill Registry Entries

**Files:**
- Modify: `config/workflows/registry.json`
- Modify: `config/workflows/skills.json`
- Modify: `tests/test_workflow_orchestration.py`

- [ ] **Step 1: Add registry tests**

Append to `tests/test_workflow_orchestration.py`:

```python
def test_expert_review_workflow_registry_contract() -> None:
    workflows = load_workflow_registry(ROOT / "config" / "workflows" / "registry.json")
    skills = load_skill_registry(ROOT / "config" / "workflows" / "skills.json")
    workflow = workflows["expert_rubric_remediation_v1"]

    assert validate_workflow_bindings(workflows, skills) == []
    assert workflow.workflow_family == "audit_and_plan"
    assert [stage.key for stage in workflow.stages] == [
        "expertise_compile",
        "rubric_synthesize",
        "evidence_audit",
        "remediation_plan",
        "implementation_handoff",
        "artifact_validate",
    ]
    assert workflow.required_validations == (
        "tmcp_packet_compiled",
        "rubric_dimensions_present",
        "findings_have_evidence",
        "remediation_has_verification",
    )
```

- [ ] **Step 2: Run registry test to verify failure**

Run:

```bash
uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract -q
```

Expected: FAIL with `KeyError: 'expert_rubric_remediation_v1'`.

- [ ] **Step 3: Add skill registry entries**

Append these entries to `config/workflows/skills.json` inside the `skills` array:

```json
{
  "key": "tmcp_expertise_compiler",
  "purpose": "Use a compiled TMCP packet as the explicit expertise source for expert rubric remediation workflows.",
  "allowed_stages": ["enrich_context"],
  "input_schema": {"tmcp_packet": "object"},
  "output_schema": {"expertise_packet": "object"},
  "invariants": ["Preserve TMCP selected nodes, skipped nodes, behavior atoms, source hashes, and traversal fingerprint."],
  "failure_conditions": ["TMCP packet is missing."],
  "side_effects": ["Writes review artifacts under the target repo when paired with the handoff builder."],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "enrich_context"],
  "purpose_long": "Use a compiled TMCP packet as the explicit expertise source for expert rubric remediation workflows."
},
{
  "key": "expert_rubric_synthesizer",
  "purpose": "Synthesize a weighted, evidence-oriented rubric from a TMCP expertise packet.",
  "allowed_stages": ["generate"],
  "input_schema": {"expertise_packet": "object", "objective": "string"},
  "output_schema": {"rubric": "object"},
  "invariants": ["Rubric dimensions must preserve TMCP provenance.", "Rubric dimensions must include evidence expectations."],
  "failure_conditions": ["No rubric dimensions are produced."],
  "side_effects": [],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "generate"],
  "purpose_long": "Synthesize a weighted, evidence-oriented rubric from a TMCP expertise packet."
},
{
  "key": "expert_evidence_auditor",
  "purpose": "Convert supplied evidence items into scored rubric findings and explicit evidence gaps.",
  "allowed_stages": ["generate"],
  "input_schema": {"rubric": "object", "evidence_items": "object[]"},
  "output_schema": {"audit_report": "object"},
  "invariants": ["Findings must cite evidence or be represented as explicit gaps.", "Scores must map to rubric dimensions."],
  "failure_conditions": ["A finding has no evidence."],
  "side_effects": [],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "generate"],
  "purpose_long": "Convert supplied evidence items into scored rubric findings and explicit evidence gaps."
},
{
  "key": "expert_remediation_planner",
  "purpose": "Convert audit findings into independently verifiable remediation slices.",
  "allowed_stages": ["finalize"],
  "input_schema": {"audit_report": "object"},
  "output_schema": {"remediation_plan": "object"},
  "invariants": ["Each remediation slice must include verification.", "Slices must preserve source finding IDs."],
  "failure_conditions": ["A remediation slice lacks verification."],
  "side_effects": [],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "finalize"],
  "purpose_long": "Convert audit findings into independently verifiable remediation slices."
},
{
  "key": "expert_implementation_handoff_builder",
  "purpose": "Create an approval-gated handoff from a selected remediation slice into implementation-delivery.",
  "allowed_stages": ["finalize"],
  "input_schema": {"remediation_plan": "object", "selected_slice_id": "string|null"},
  "output_schema": {"implementation_handoff": "object", "artifact_paths": "object"},
  "invariants": ["Handoff must require user approval.", "Handoff must not execute implementation."],
  "failure_conditions": ["Remediation plan is missing."],
  "side_effects": ["Writes review artifacts under .aios/reviews/{run_id} in the target repository."],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "finalize"],
  "purpose_long": "Create an approval-gated handoff from a selected remediation slice into implementation-delivery."
},
{
  "key": "tmcp_packet_compiled",
  "purpose": "Validate that the expert workflow has a compiled TMCP expertise packet.",
  "allowed_stages": ["validate"],
  "input_schema": {"tmcp_packet": "object"},
  "output_schema": {"passed": "boolean", "issues": "string[]"},
  "invariants": ["Validation output must be explicit pass/fail."],
  "failure_conditions": ["TMCP packet is missing."],
  "side_effects": [],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "validate"],
  "purpose_long": "Validate that the expert workflow has a compiled TMCP expertise packet."
},
{
  "key": "rubric_dimensions_present",
  "purpose": "Validate that the synthesized rubric contains dimensions with provenance and evidence expectations.",
  "allowed_stages": ["validate"],
  "input_schema": {"rubric": "object"},
  "output_schema": {"passed": "boolean", "issues": "string[]"},
  "invariants": ["Validation output must be explicit pass/fail."],
  "failure_conditions": ["Rubric dimensions are missing or lack provenance."],
  "side_effects": [],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "validate"],
  "purpose_long": "Validate that the synthesized rubric contains dimensions with provenance and evidence expectations."
},
{
  "key": "findings_have_evidence",
  "purpose": "Validate that audit findings cite evidence references.",
  "allowed_stages": ["validate"],
  "input_schema": {"audit_report": "object"},
  "output_schema": {"passed": "boolean", "issues": "string[]"},
  "invariants": ["Validation output must be explicit pass/fail."],
  "failure_conditions": ["An audit finding lacks evidence."],
  "side_effects": [],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "validate"],
  "purpose_long": "Validate that audit findings cite evidence references."
},
{
  "key": "remediation_has_verification",
  "purpose": "Validate that remediation slices include verification expectations.",
  "allowed_stages": ["validate"],
  "input_schema": {"remediation_plan": "object"},
  "output_schema": {"passed": "boolean", "issues": "string[]"},
  "invariants": ["Validation output must be explicit pass/fail."],
  "failure_conditions": ["A remediation slice lacks verification."],
  "side_effects": [],
  "execution_mode": "deterministic",
  "lifecycle_state": "active",
  "applicability": ["expert_rubric_remediation", "validate"],
  "purpose_long": "Validate that remediation slices include verification expectations."
}
```

- [ ] **Step 4: Add workflow registry entry**

Append this workflow object to `config/workflows/registry.json` inside the `workflows` array:

```json
{
  "key": "expert_rubric_remediation_v1",
  "name": "Expert Rubric Remediation v1",
  "workflow_family": "audit_and_plan",
  "purpose": "Compile domain expertise into an explicit rubric, audit concrete evidence, and produce an ordered remediation plan.",
  "trigger_hints": [
    "review using tmcp",
    "create a rubric",
    "remediation plan",
    "expert rubric",
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
  ],
  "stages": [
    {
      "key": "expertise_compile",
      "kind": "enrich_context",
      "required_skills": ["tmcp_expertise_compiler"],
      "required_inputs": [{"key": "tmcp_packet", "source": "packet", "required": true}],
      "required_outputs": [{"key": "expertise_packet", "target": "artifact", "required": true}],
      "expected_artifacts": [{"artifact_kind": "evidence", "path_template": ".aios/reviews/{run_id}/expertise-packet.json"}],
      "writeback_behavior": {"on_success": ["workflow_learning_event"], "on_failure": ["workflow_learning_event"], "no_learning_evidence_required": false}
    },
    {
      "key": "rubric_synthesize",
      "kind": "generate",
      "required_skills": ["expert_rubric_synthesizer"],
      "required_outputs": [{"key": "rubric", "target": "artifact", "required": true}],
      "expected_artifacts": [{"artifact_kind": "report", "path_template": ".aios/reviews/{run_id}/rubric.md"}],
      "writeback_behavior": {"on_success": ["workflow_learning_event"], "on_failure": ["workflow_learning_event"], "no_learning_evidence_required": false}
    },
    {
      "key": "evidence_audit",
      "kind": "generate",
      "required_skills": ["expert_evidence_auditor"],
      "required_outputs": [{"key": "audit_report", "target": "artifact", "required": true}],
      "expected_artifacts": [{"artifact_kind": "report", "path_template": ".aios/reviews/{run_id}/audit-report.md"}],
      "writeback_behavior": {"on_success": ["workflow_learning_event"], "on_failure": ["workflow_learning_event"], "no_learning_evidence_required": false}
    },
    {
      "key": "remediation_plan",
      "kind": "finalize",
      "required_skills": ["expert_remediation_planner"],
      "required_outputs": [{"key": "remediation_plan", "target": "artifact", "required": true}],
      "expected_artifacts": [{"artifact_kind": "summary", "path_template": ".aios/reviews/{run_id}/remediation-plan.md"}],
      "writeback_behavior": {"on_success": ["workflow_learning_event"], "on_failure": ["workflow_learning_event"], "no_learning_evidence_required": false}
    },
    {
      "key": "implementation_handoff",
      "kind": "finalize",
      "required_skills": ["expert_implementation_handoff_builder"],
      "required_outputs": [{"key": "implementation_handoff", "target": "artifact", "required": false}],
      "approval_gates": [
        {
          "impact_scope": "workflow-default",
          "condition": "always",
          "rationale_template": "Implementation handoff from expert review requires explicit user approval before execution."
        }
      ],
      "expected_artifacts": [{"artifact_kind": "summary", "path_template": ".aios/reviews/{run_id}/implementation-handoff.md"}],
      "writeback_behavior": {"on_success": ["workflow_learning_event"], "on_failure": ["workflow_learning_event"], "no_learning_evidence_required": false}
    },
    {
      "key": "artifact_validate",
      "kind": "validate",
      "required_skills": [
        "tmcp_packet_compiled",
        "rubric_dimensions_present",
        "findings_have_evidence",
        "remediation_has_verification"
      ],
      "validations": [{"criterion_id": "agent-claim-verification", "blocking": true}],
      "required_evidence": ["expert_review_artifacts"],
      "writeback_behavior": {"on_success": ["workflow_learning_event"], "on_failure": ["workflow_learning_event"], "no_learning_evidence_required": false}
    }
  ],
  "lifecycle_state": "active",
  "applicability": [
    "audit_and_plan",
    "expert_review",
    "tmcp",
    "rubric",
    "remediation"
  ],
  "purpose_long": "Compile TMCP expertise into an explicit rubric, audit concrete evidence, produce ordered remediation slices, and stop before implementation until the user approves a handoff.",
  "implementation_bearing": false
}
```

- [ ] **Step 5: Run registry and executor tests**

Run:

```bash
uv run pytest tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts -q
```

Expected: PASS.

- [ ] **Step 6: Commit registry entries**

```bash
git add config/workflows/registry.json config/workflows/skills.json tests/test_workflow_orchestration.py
git commit -m "Register expert rubric remediation workflow"
```

## Task 5: Routing Support For Expert Review Objectives

**Files:**
- Modify: `services/workflow_orchestration.py`
- Modify: `tests/test_workflow_orchestration.py`

- [ ] **Step 1: Add failing routing test**

Append to `tests/test_workflow_orchestration.py`:

```python
def test_expert_review_objective_routes_to_rubric_remediation_workflow() -> None:
    candidates = rank_workflow_candidates(
        "Review this app using TMCP expertise, create a rubric, and produce a remediation plan"
    )

    assert candidates[0].workflow_key == "expert_rubric_remediation_v1"

    route = recommend_route_primitives(
        "Review this app using TMCP expertise, create a rubric, and produce a remediation plan"
    )

    assert route["selected_workflow"]["workflow_key"] == "expert_rubric_remediation_v1"
```

- [ ] **Step 2: Run routing test to verify failure**

Run:

```bash
uv run pytest tests/test_workflow_orchestration.py::test_expert_review_objective_routes_to_rubric_remediation_workflow -q
```

Expected: FAIL because current routing can select another audit or implementation workflow.

- [ ] **Step 3: Update route scoring**

In `rank_workflow_candidates`, add this term set near `analysis_terms`:

```python
    expert_review_terms = {
        "expert",
        "expertise",
        "rubric",
        "scorecard",
        "remediation",
        "tmcp",
    }
```

Add this evidence flag:

```python
    expert_review_evidence = _has_any_word(objective_text, expert_review_terms)
```

Add this branch inside the workflow loop after the `audit_only` branch:

```python
        if workflow.workflow_family == "audit_and_plan" and analysis_evidence and expert_review_evidence:
            score += 11
            evidence_reasons.append("expert rubric remediation evidence")
            if implementation_evidence:
                score -= 2
```

Add the workflow task family mapping near `WORKFLOW_TASK_FAMILIES`:

```python
    "expert_rubric_remediation_v1": "audit_and_plan",
```

- [ ] **Step 4: Run routing tests**

Run:

```bash
uv run pytest tests/test_workflow_orchestration.py::test_expert_review_objective_routes_to_rubric_remediation_workflow -q
```

Expected: PASS.

- [ ] **Step 5: Commit routing support**

```bash
git add services/workflow_orchestration.py tests/test_workflow_orchestration.py
git commit -m "Route expert rubric remediation objectives"
```

## Task 6: Read-Only TMCP Review Plan CLI

**Files:**
- Modify: `services/aios_cli.py`
- Modify: `tests/test_aios_cli.py`

- [ ] **Step 1: Write failing CLI test**

Append to `tests/test_aios_cli.py`:

```python
def test_tmcp_review_plan_cli_writes_artifacts(tmp_path: Path, capsys) -> None:
    evidence = {
        "dimension_id": "data_realism",
        "severity": "blocker",
        "summary": "Waveform bars are random during render.",
        "evidence": ["packages/web/src/components/feed/FeedItem.tsx:427"],
        "recommended_fix": "Derive waveform heights from stable input.",
    }
    output_dir = tmp_path / "review-output"

    exit_code = run_cli(
        [
            "--json",
            "tmcp",
            "review-plan",
            "Review Soundscape UI polish with TMCP expertise and create a rubric remediation plan",
            "--project-path",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--evidence-json",
            json.dumps(evidence),
            "--selected-slice-id",
            "slice-1",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    data = payload["data"]
    assert exit_code == EXIT_OK
    assert data["workflow_key"] == "expert_rubric_remediation_v1"
    assert data["status"] == "completed"
    assert Path(data["artifact_paths"]["rubric_json"]).exists()
    assert Path(data["artifact_paths"]["remediation_plan_markdown"]).exists()
```

- [ ] **Step 2: Run CLI test to verify failure**

Run:

```bash
uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_cli_writes_artifacts -q
```

Expected: FAIL because `review-plan` is not a TMCP subcommand.

- [ ] **Step 3: Add CLI parser arguments**

In `services/aios_cli.py`, after the `tmcp_explain` parser block, add:

```python
    tmcp_review_plan = tmcp_subparsers.add_parser(
        "review-plan",
        help="Compile TMCP expertise into a rubric, audit report, and remediation plan",
    )
    tmcp_review_plan.add_argument("objective", help="Natural language review objective")
    tmcp_review_plan.add_argument("--project-path", required=True, help="Target repository or artifact path")
    tmcp_review_plan.add_argument("--phase", default="planning", help="Optional TMCP phase hint")
    tmcp_review_plan.add_argument("--domain", default=None, help="Optional TMCP domain hint")
    tmcp_review_plan.add_argument(
        "--skills-library",
        default=str(REPO_ROOT / "skills-library"),
        help="Skills library path containing skills.tmcp",
    )
    tmcp_review_plan.add_argument(
        "--output-dir",
        default=None,
        help="Artifact output directory; defaults to <project-path>/.aios/reviews/<run-id>",
    )
    tmcp_review_plan.add_argument(
        "--evidence-json",
        action="append",
        default=[],
        help="JSON evidence item with dimension_id, severity, summary, evidence, and recommended_fix",
    )
    tmcp_review_plan.add_argument("--selected-slice-id", default=None)
    tmcp_review_plan.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
```

- [ ] **Step 4: Add CLI execution branch**

In the CLI `run_cli` TMCP branches, add before `tmcp learning-summary`:

```python
        elif args.command == "tmcp" and args.tmcp_command == "review-plan":
            run_id = f"expert-review-{uuid.uuid4()}"
            packet = compile_tmcp_packet(
                objective=args.objective,
                project_path=args.project_path,
                skills_library_path=Path(args.skills_library).expanduser().resolve(),
                phase=args.phase,
                domain=args.domain,
            )
            output_dir = (
                Path(args.output_dir).expanduser().resolve()
                if args.output_dir
                else Path(args.project_path).expanduser().resolve() / ".aios" / "reviews" / run_id
            )
            context = WorkflowExecutionContext(
                objective=args.objective,
                workflow_key="expert_rubric_remediation_v1",
                repo_path=args.project_path,
                run_id=run_id,
                tmcp_packet=packet,
                evidence_items=tuple(_parse_json_object(raw) for raw in args.evidence_json),
                selected_slice_id=args.selected_slice_id,
            )
            report = execute_workflow(context)
            artifact_paths = report.get("artifacts", {}).get("expert_review_artifact_paths", {})
            if args.output_dir and artifact_paths:
                source_root = Path(args.project_path).expanduser().resolve() / ".aios" / "reviews" / run_id
                if source_root != output_dir:
                    source_paths = {key: Path(value) for key, value in artifact_paths.items()}
                    output_dir.mkdir(parents=True, exist_ok=True)
                    artifact_paths = {}
                    for key, source_path in source_paths.items():
                        target = output_dir / source_path.name
                        target.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
                        artifact_paths[key] = str(target)
            data = {
                "schema": "aios-tmcp-review-plan-result-v0.1",
                "workflow_key": report["workflow_key"],
                "status": report["status"],
                "run_id": run_id,
                "artifact_paths": artifact_paths,
                "summary": summarize_execution_report(report),
            }
```

`uuid` is already imported in `services/aios_cli.py`. Extend the existing `from services.workflow_orchestration import (...)` block with these names:

```python
    WorkflowExecutionContext,
    execute_workflow,
    summarize_execution_report,
```

- [ ] **Step 5: Run CLI test**

Run:

```bash
uv run pytest tests/test_aios_cli.py::test_tmcp_review_plan_cli_writes_artifacts -q
```

Expected: PASS.

- [ ] **Step 6: Commit CLI command**

```bash
git add services/aios_cli.py tests/test_aios_cli.py
git commit -m "Add TMCP review plan CLI"
```

## Task 7: Focused Quality Gates And Truth Update

**Files:**
- Modify: `.tracker/PROJECT_TRUTH.md`

- [ ] **Step 1: Run focused tests**

Run:

```bash
uv run pytest tests/test_expert_rubric_remediation.py tests/test_workflow_orchestration.py::test_expert_review_workflow_registry_contract tests/test_workflow_orchestration.py::test_expert_review_workflow_executes_with_artifacts tests/test_workflow_orchestration.py::test_expert_review_objective_routes_to_rubric_remediation_workflow tests/test_aios_cli.py::test_tmcp_review_plan_cli_writes_artifacts -q
```

Expected: PASS.

- [ ] **Step 2: Run targeted lint and type checks**

Run:

```bash
uv run ruff check services/expert_rubric_remediation.py services/workflow_orchestration.py services/aios_cli.py tests/test_expert_rubric_remediation.py tests/test_workflow_orchestration.py tests/test_aios_cli.py
uv run ruff format --check services/expert_rubric_remediation.py services/workflow_orchestration.py services/aios_cli.py tests/test_expert_rubric_remediation.py tests/test_workflow_orchestration.py tests/test_aios_cli.py
uv run basedpyright services/expert_rubric_remediation.py services/workflow_orchestration.py services/aios_cli.py tests/test_expert_rubric_remediation.py tests/test_workflow_orchestration.py tests/test_aios_cli.py
```

Expected: targeted Ruff and format pass. BasedPyright may surface existing errors in shared files; fix errors introduced by this work and record existing unrelated failures in the truth file.

- [ ] **Step 3: Run full quality ladder**

Run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv run vulture . --min-confidence 70
uv run pytest -q
```

Expected: current repo truth says full Ruff, format, BasedPyright, and pytest baselines are already failing. Do not claim repo-level quality green unless these pass. Record exact results in `.tracker/PROJECT_TRUTH.md`.

- [ ] **Step 4: Update project truth**

Update `.tracker/PROJECT_TRUTH.md`:

```markdown
- Add a Recent Progress bullet for implemented `expert_rubric_remediation_v1`.
- Update `summary` to mention the implemented workflow if all focused checks pass.
- Keep existing repo-level quality fields as fail/warning unless full quality commands pass.
- Add Quality Ladder Notes with the exact focused and full command results.
- Set `lastUpdated` to `2026-06-24`.
```

- [ ] **Step 5: Commit truth update**

```bash
git add .tracker/PROJECT_TRUTH.md
git commit -m "Update project truth for expert review workflow"
```

## Task 8: Final Verification And Handoff

**Files:**
- No new files unless verification exposes a real defect.

- [ ] **Step 1: Verify CLI manually with temp output**

Run:

```bash
uv run python bin/aios.py --json tmcp review-plan "Review Soundscape UI polish with TMCP expertise and create a rubric remediation plan" --project-path /Users/jakyeamos/projects/soundscape-app --output-dir /tmp/aios-expert-review-smoke --evidence-json '{"dimension_id":"data_realism","severity":"blocker","summary":"Feed waveform uses random visual data.","evidence":["packages/web/src/components/feed/FeedItem.tsx:427"],"recommended_fix":"Derive waveform heights from stable input."}' --selected-slice-id slice-1
```

Expected: JSON payload with `workflow_key` equal to `expert_rubric_remediation_v1`, `status` equal to `completed`, and artifact paths under `/tmp/aios-expert-review-smoke`.

- [ ] **Step 2: Inspect generated artifacts**

Run:

```bash
ls -1 /tmp/aios-expert-review-smoke
sed -n '1,120p' /tmp/aios-expert-review-smoke/rubric.md
sed -n '1,160p' /tmp/aios-expert-review-smoke/remediation-plan.md
```

Expected: files include `expertise-packet.json`, `rubric.json`, `rubric.md`, `audit-report.json`, `audit-report.md`, `remediation-plan.json`, `remediation-plan.md`, `implementation-handoff.json`, and `implementation-handoff.md`.

- [ ] **Step 3: Check final staged state**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: only unrelated pre-existing dirty files remain outside the committed implementation slices, or the working tree is clean if those unrelated changes were resolved separately.

- [ ] **Step 4: Final response content**

Report:

```text
Implemented expert_rubric_remediation_v1.
Artifacts:
- services/expert_rubric_remediation.py
- config/workflows/registry.json
- config/workflows/skills.json
- aios tmcp review-plan

Verification:
- focused pytest command result
- targeted Ruff result
- targeted BasedPyright result
- full quality ladder result or existing blockers

Commits:
- list task commits
```

## Plan Self-Review

Spec coverage:

- Expertise packet: covered by Task 3 dispatch and Task 4 registry stage `expertise_compile`.
- Rubric artifacts: covered by Task 1 service writers, Task 3 executor artifacts, and Task 4 workflow stage `rubric_synthesize`.
- Evidence-backed audit: covered by Task 2 fixture builders, Task 3 executor artifacts, and Task 4 workflow stage `evidence_audit`.
- Remediation plan: covered by Task 1/2 service functions, Task 3 executor artifacts, and Task 4 workflow stage `remediation_plan`.
- Optional implementation handoff: covered by Task 2 handoff builder, Task 3 executor artifacts, Task 4 workflow stage `implementation_handoff`, and Task 8 manual artifact inspection.
- Hard failures and validations: covered by service validation tests, final `artifact_validate` stage, and required validation skills.
- Initial profiles: covered by deterministic profile selection in Task 1 and the Soundscape visual-polish fixture in Task 2; security/privacy and developer-experience dimensions are included in the same service profile table.
- CLI preview: covered by Task 6.
- Truth maintenance and quality reporting: covered by Task 7.

Placeholder scan: passed with no blocked patterns.

Type/signature consistency: public functions introduced in Task 1 are used by later tasks with matching names and argument names; `WorkflowExecutionContext.evidence_items` and `selected_slice_id` are introduced before CLI usage; registry validation keeps required validations in the final validate stage.

Scope check: this is one workflow subsystem with a service module, registry entries, executor dispatch, routing, CLI, tests, and truth update. It does not need to be split into multiple implementation plans.
