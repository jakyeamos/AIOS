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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _selected_nodes(packet: dict[str, Any]) -> list[str]:
    return _string_list(packet.get("selected_nodes", []))


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


def _visual_polish_dimensions(source_nodes: list[str]) -> list[dict[str, Any]]:
    fallback_nodes = source_nodes or ["@task:visual_polish"]
    return [
        _dimension(
            dimension_id="surface_hierarchy",
            name="Surface Hierarchy",
            weight=4,
            expectations=[
                "File, screen, or screenshot evidence showing dominant and supporting regions."
            ],
            questions=[
                "Is there one dominant work region?",
                "Are cards used only where they frame real repeated objects?",
            ],
            source_nodes=[node for node in fallback_nodes if "visual" in node or "saas" in node]
            or fallback_nodes,
        ),
        _dimension(
            dimension_id="interaction_architecture",
            name="Interaction Architecture",
            weight=4,
            expectations=[
                "Evidence for containers, loading states, empty states, overlays, and actions."
            ],
            questions=[
                "Does the container match the user task?",
                "Are empty/loading/error states decision-useful?",
            ],
            source_nodes=[
                node for node in fallback_nodes if "interaction" in node or "saas" in node
            ]
            or fallback_nodes,
        ),
        _dimension(
            dimension_id="data_realism",
            name="Data Realism",
            weight=4,
            expectations=[
                "Evidence for source, freshness, deterministic data, and non-vanity metrics."
            ],
            questions=[
                "Are metrics credible?",
                "Are visualizations driven by stable data rather than decoration?",
            ],
            source_nodes=[node for node in fallback_nodes if "data_realism" in node]
            or fallback_nodes,
        ),
        _dimension(
            dimension_id="product_evidence",
            name="Product Evidence",
            weight=3,
            expectations=[
                "Evidence that the first screen shows product, media, object, or real state."
            ],
            questions=[
                "Can a viewer understand the actual product from the first screen?",
                "Is decoration replacing product proof?",
            ],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="design_system_fit",
            name="Design System Fit",
            weight=3,
            expectations=[
                "Evidence for tokens, component conventions, typography, spacing, and states."
            ],
            questions=[
                "Does the surface follow local tokens?",
                "Are raw utility colors or decorative defaults leaking through?",
            ],
            source_nodes=fallback_nodes,
        ),
    ]


def _security_privacy_dimensions(source_nodes: list[str]) -> list[dict[str, Any]]:
    fallback_nodes = source_nodes or ["@task:security_review"]
    return [
        _dimension(
            dimension_id="secret_exposure",
            name="Secret Exposure",
            weight=4,
            expectations=["Evidence for env, logs, fixtures, configs, and generated artifacts."],
            questions=["Can credentials leak through logs?", "Are sensitive values redacted?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="permission_boundary",
            name="Permission Boundary",
            weight=4,
            expectations=["Evidence for file, network, auth, database, and tool side effects."],
            questions=["Are mutations explicit?", "Are privileged operations approval-gated?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="data_flow_privacy",
            name="Data Flow Privacy",
            weight=4,
            expectations=["Evidence for inputs, persistence, retention, and outbound data flow."],
            questions=["Is sensitive data minimized?", "Can retained data be audited?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="supply_chain",
            name="Supply Chain",
            weight=3,
            expectations=["Evidence for dependency changes, lockfiles, and provenance."],
            questions=["Are dependencies justified?", "Do lockfiles match repo policy?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="security_verification",
            name="Security Verification",
            weight=3,
            expectations=["Evidence for tests, scans, or review commands tied to the risk."],
            questions=["Was the risky path checked?", "Are residual risks documented?"],
            source_nodes=fallback_nodes,
        ),
    ]


def _developer_experience_dimensions(source_nodes: list[str]) -> list[dict[str, Any]]:
    fallback_nodes = source_nodes or ["@task:developer_experience"]
    return [
        _dimension(
            dimension_id="command_discoverability",
            name="Command Discoverability",
            weight=4,
            expectations=["Evidence for setup, test, lint, typecheck, build, and run commands."],
            questions=["Can a developer find the right commands?", "Do docs match scripts?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="validation_loop",
            name="Validation Loop",
            weight=4,
            expectations=["Evidence for fast targeted checks and complete release checks."],
            questions=["Is the inner loop fast?", "Are failures actionable?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="interface_clarity",
            name="Interface Clarity",
            weight=3,
            expectations=["Evidence for API, CLI, schema, errors, and examples."],
            questions=["Are public interfaces predictable?", "Can errors guide next action?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="onboarding_path",
            name="Onboarding Path",
            weight=3,
            expectations=["Evidence for README, examples, seed data, fixtures, or first run."],
            questions=["Can a first run succeed?", "Are setup assumptions explicit?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="maintenance_signal",
            name="Maintenance Signal",
            weight=3,
            expectations=["Evidence for ownership, freshness, health notes, and blockers."],
            questions=["Can maintainers see health?", "Are stale or failing checks disclosed?"],
            source_nodes=fallback_nodes,
        ),
    ]


def _general_review_dimensions(source_nodes: list[str]) -> list[dict[str, Any]]:
    fallback_nodes = source_nodes or ["@task:agent_workflow"]
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
            questions=["Are correctness risks first?", "Are preferences separate from defects?"],
            source_nodes=fallback_nodes,
        ),
        _dimension(
            dimension_id="verification_readiness",
            name="Verification Readiness",
            weight=4,
            expectations=["Evidence that remediation can be verified by commands or checks."],
            questions=["Can the next worker know when a slice is done?"],
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
            expectations=["Evidence that fixes are ordered into coherent slices."],
            questions=[
                "Can slices be committed independently?",
                "Does sequence reduce risk first?",
            ],
            source_nodes=fallback_nodes,
        ),
    ]


def _profile_dimensions(profile_id: str, source_nodes: list[str]) -> list[dict[str, Any]]:
    if profile_id == "visual_polish":
        return _visual_polish_dimensions(source_nodes)
    if profile_id == "security_privacy":
        return _security_privacy_dimensions(source_nodes)
    if profile_id == "developer_experience":
        return _developer_experience_dimensions(source_nodes)
    return _general_review_dimensions(source_nodes)


def synthesize_rubric(*, packet: dict[str, Any], run_id: str, objective: str) -> dict[str, Any]:
    selected_nodes = _selected_nodes(packet)
    profile_id = _profile_id(packet)
    return {
        "schema": RUBRIC_SCHEMA,
        "run_id": run_id,
        "objective": objective,
        "source_packet": "expertise-packet.json",
        "profile": profile_id,
        "selected_nodes": selected_nodes,
        "skipped_nodes": packet.get("skipped_nodes", []),
        "dimensions": _profile_dimensions(profile_id, selected_nodes),
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


def _severity_rank(severity: str) -> int:
    return {"blocker": 0, "warning": 1, "observation": 2}.get(severity, 1)


def _severity_score(severity: str) -> int:
    return {"blocker": 1, "warning": 2, "observation": 3}.get(severity, 2)


def _rubric_dimensions(rubric: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions = rubric.get("dimensions", [])
    if not isinstance(dimensions, list):
        return []
    return [dimension for dimension in dimensions if isinstance(dimension, dict)]


def _coerce_dimension_id(dimension_id: object, dimensions: list[dict[str, Any]]) -> str:
    known_ids = [str(dimension.get("id", "")) for dimension in dimensions]
    candidate = str(dimension_id)
    if candidate in known_ids:
        return candidate
    return next((known_id for known_id in known_ids if known_id), "general_review")


def build_audit_report(
    *,
    rubric: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    dimensions = _rubric_dimensions(rubric)
    evidence_by_dimension: dict[str, list[str]] = {}
    gaps_by_dimension: dict[str, list[str]] = {}
    findings: list[dict[str, Any]] = []
    sorted_items = sorted(
        enumerate(evidence_items),
        key=lambda indexed_item: _severity_rank(str(indexed_item[1].get("severity", "warning"))),
    )

    for finding_index, (_, item) in enumerate(sorted_items, start=1):
        dimension_id = _coerce_dimension_id(item.get("dimension_id", ""), dimensions)
        severity = str(item.get("severity", "warning"))
        if severity not in {"blocker", "warning", "observation"}:
            severity = "warning"
        evidence = _string_list(item.get("evidence", []))
        evidence_by_dimension.setdefault(dimension_id, []).extend(evidence)
        findings.append(
            {
                "id": f"finding-{dimension_id}-{finding_index}",
                "severity": severity,
                "dimension_id": dimension_id,
                "summary": str(item.get("summary", "")),
                "evidence": evidence,
                "recommended_fix": str(item.get("recommended_fix", "")),
            }
        )

    scores: list[dict[str, Any]] = []
    for dimension in dimensions:
        dimension_id = str(dimension.get("id", ""))
        matching_findings = [
            finding for finding in findings if finding.get("dimension_id") == dimension_id
        ]
        evidence = evidence_by_dimension.get(dimension_id, [])
        if matching_findings:
            score = min(_severity_score(str(finding["severity"])) for finding in matching_findings)
            confidence = "high" if evidence else "low"
            gaps = gaps_by_dimension.get(dimension_id, [])
        else:
            score = 0
            confidence = "low"
            gaps = [f"No evidence supplied for {dimension_id}."]
        scores.append(
            {
                "dimension_id": dimension_id,
                "score": score,
                "confidence": confidence,
                "evidence": evidence,
                "gaps": gaps,
            }
        )

    return {
        "schema": AUDIT_REPORT_SCHEMA,
        "run_id": run_id,
        "rubric": "rubric.json",
        "scores": scores,
        "findings": findings,
        "deferred_scope": [],
    }


def build_remediation_plan(*, audit_report: dict[str, Any], run_id: str) -> dict[str, Any]:
    slices: list[dict[str, Any]] = []
    for index, finding in enumerate(audit_report.get("findings", []), start=1):
        finding_id = str(finding.get("id", f"finding-{index}"))
        evidence = _string_list(finding.get("evidence", []))
        slices.append(
            {
                "id": f"slice-{index}",
                "title": str(finding.get("summary", finding_id))[:80],
                "scope": evidence,
                "rationale": str(finding.get("summary", "")),
                "expected_impact": str(finding.get("recommended_fix", "")),
                "risk": (
                    "Review scope is limited to cited evidence; verify neighboring call "
                    "sites before editing."
                ),
                "verification": [
                    "Run targeted tests or manual checks covering the cited evidence."
                ],
                "follow_up_workflow": "implementation-delivery",
                "source_findings": [finding_id],
            }
        )
    return {
        "schema": REMEDIATION_PLAN_SCHEMA,
        "run_id": run_id,
        "slices": slices,
        "deferred_scope": _string_list(audit_report.get("deferred_scope", [])),
    }


def build_implementation_handoff(
    *,
    remediation_plan: dict[str, Any],
    run_id: str,
    selected_slice_id: str | None,
) -> dict[str, Any]:
    slices = remediation_plan.get("slices", [])
    remediation_slices = (
        [item for item in slices if isinstance(item, dict)] if isinstance(slices, list) else []
    )
    selected_slice = next(
        (
            item
            for item in remediation_slices
            if selected_slice_id is not None and item.get("id") == selected_slice_id
        ),
        remediation_slices[0] if remediation_slices else {},
    )
    resolved_slice_id = (
        selected_slice.get("id") if isinstance(selected_slice, dict) else selected_slice_id
    )
    target_files = _string_list(selected_slice.get("scope", [])) if selected_slice else []
    verification = _string_list(selected_slice.get("verification", [])) if selected_slice else []
    risk = str(selected_slice.get("risk", "")) if selected_slice else ""
    return {
        "schema": IMPLEMENTATION_HANDOFF_SCHEMA,
        "run_id": run_id,
        "remediation_plan": "remediation-plan.json",
        "selected_slice_id": resolved_slice_id,
        "selected_slice": selected_slice,
        "requires_user_approval": True,
        "follow_up_workflow": "implementation-delivery",
        "artifact_inputs": [
            "expertise-packet.json",
            "rubric.json",
            "audit-report.json",
            "remediation-plan.json",
        ],
        "target_files": target_files,
        "acceptance_criteria": verification,
        "known_risks": [risk] if risk else [],
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
    return {
        "validation_key": "remediation_has_verification",
        "passed": not issues,
        "issues": issues,
    }


def render_rubric_markdown(rubric: dict[str, Any]) -> str:
    lines = [
        f"# Expert Rubric: {rubric['objective']}",
        "",
        f"Profile: `{rubric['profile']}`",
        "",
    ]
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
    lines = [f"# Expert Audit Report: {report['run_id']}", "", "## Scores"]
    for score in report.get("scores", []):
        lines.append(
            f"- `{score['dimension_id']}`: {score['score']}/4 ({score['confidence']} confidence)"
        )
    lines.extend(["", "## Findings"])
    for finding in report.get("findings", []):
        evidence = ", ".join(_string_list(finding.get("evidence", [])))
        lines.append(f"- [{finding['severity']}] {finding['summary']} Evidence: {evidence}")
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
                f"- Scope: {', '.join(_string_list(item.get('scope', [])))}",
                f"- Rationale: {item['rationale']}",
                f"- Expected impact: {item['expected_impact']}",
                f"- Risk: {item['risk']}",
                f"- Verification: {', '.join(_string_list(item.get('verification', [])))}",
                f"- Follow-up workflow: `{item['follow_up_workflow']}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_handoff_markdown(handoff: dict[str, Any]) -> str:
    selected = handoff.get("selected_slice")
    selected_slice = selected if isinstance(selected, dict) else {}
    lines = [
        f"# Implementation Handoff: {handoff['run_id']}",
        "",
        f"- Requires user approval: {handoff['requires_user_approval']}",
        f"- Follow-up workflow: `{handoff['follow_up_workflow']}`",
        f"- Selected slice: `{handoff.get('selected_slice_id')}`",
        "",
    ]
    if selected_slice:
        lines.extend(
            [
                "## Selected Slice",
                "",
                f"- Title: {selected_slice.get('title')}",
                f"- Scope: {', '.join(_string_list(selected_slice.get('scope', [])))}",
                f"- Verification: {', '.join(_string_list(selected_slice.get('verification', [])))}",
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
