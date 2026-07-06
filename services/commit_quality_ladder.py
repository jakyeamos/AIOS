from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from services.evidence_artifacts import validate_fresh_evidence
from services.quality_gate_audit import (
    GateDecision,
    build_gate_audit_event,
    quality_gate_decision,
    safe_append_gate_audit_event,
)
from services.verifier_artifacts import fresh_verifier_refs

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_ROOT = REPO_ROOT / "aios" / "context"
SUCCESS_CRITERIA_REGISTRY = REPO_ROOT / "config" / "success-criteria" / "registry.json"
QUALITY_PIPELINE_CONFIG = REPO_ROOT / "config" / "quality-pipeline.json"
QUALITY_GATES_CONFIG = REPO_ROOT / "config" / "quality-gates.json"
STANDARDS_REGISTRY = REPO_ROOT / "config" / "standards" / "registry.json"

CHECK_STATUS = Literal["pass", "fail", "skip"]
CODE_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
HANDLER_PATTERNS = (
    'addEventListener("message"',
    "addEventListener('message'",
    '.on("message"',
    ".on('message'",
    '.once("message"',
    ".once('message'",
    ".onmessage",
)
SEND_PATTERNS = (".postMessage(", "postMessage(")
ALLOW_MARKER = "aios-quality: allow handler-before-send"


@dataclass(frozen=True)
class LadderCheck:
    key: str
    label: str
    status: CHECK_STATUS
    detail: str
    evidence: tuple[str, ...] = ()


def run_ladder(
    *,
    repo_root: Path = REPO_ROOT,
    staged_files: Sequence[str] | None = None,
    run_context_validation: bool = True,
) -> list[LadderCheck]:
    files = list(staged_files) if staged_files is not None else staged_paths(repo_root)
    checks = [
        check_hook_scope(repo_root, files),
        check_global_standards_inventory(repo_root),
        check_standards_health_registry(repo_root),
        check_success_criteria_registry(repo_root),
        check_quality_pipeline_includes_aios(repo_root),
        check_quality_gate_registry(repo_root),
        check_confident_event_loop_ordering(repo_root, files),
    ]
    if run_context_validation:
        checks.insert(2, check_context_validation(repo_root))
    run_id = os.environ.get("AIOS_RUN_ID")
    session_id = os.environ.get("AIOS_SESSION_ID")
    if run_id or session_id:
        checks.append(
            check_aios_evidence_artifacts(
                db_path=Path(os.environ.get("AIOS_DB", "~/AIOS/data/aios.db")).expanduser(),
                run_id=run_id,
                session_id=session_id,
            )
        )
        checks.append(
            check_aios_verifier_artifacts(
                db_path=Path(os.environ.get("AIOS_DB", "~/AIOS/data/aios.db")).expanduser(),
                run_id=run_id,
                session_id=session_id,
            )
        )
    return checks


def staged_paths(repo_root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def staged_file_text(repo_root: Path, relative_path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f":{relative_path}"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        path = repo_root / relative_path
        if not path.exists() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    return result.stdout


def check_hook_scope(repo_root: Path, files: Sequence[str]) -> LadderCheck:
    hook_path = repo_root / ".githooks" / "pre-commit"
    if not hook_path.exists():
        return LadderCheck(
            "hook.installed",
            "Versioned pre-commit hook exists",
            "fail",
            ".githooks/pre-commit is missing.",
        )
    detail = f"{len(files)} staged file(s) will be checked."
    return LadderCheck("hook.scope", "Staged change scope", "pass", detail)


def check_context_validation(repo_root: Path) -> LadderCheck:
    result = subprocess.run(
        ["node", "tools/context-compile.mjs", "--validate"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return LadderCheck(
            "standards.context_validate",
            "Context standards validate",
            "pass",
            "Context compiler validation passed.",
            _tail_lines(result.stdout),
        )
    return LadderCheck(
        "standards.context_validate",
        "Context standards validate",
        "fail",
        "Context compiler validation failed.",
        _tail_lines(result.stdout + result.stderr),
    )


def check_global_standards_inventory(repo_root: Path) -> LadderCheck:
    standards_dir = repo_root / "aios" / "context" / "standards"
    files = sorted(path for path in standards_dir.glob("*.md") if path.name != "index.md")
    failures: list[str] = []
    ids: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        frontmatter = _frontmatter(text)
        standard_id = str(frontmatter.get("id", "")).strip()
        if not standard_id:
            failures.append(f"{path.relative_to(repo_root)} missing id")
        else:
            ids.append(standard_id)
        if frontmatter.get("status") != "active":
            failures.append(f"{path.relative_to(repo_root)} is not active")
        if frontmatter.get("tier") != "global":
            failures.append(f"{path.relative_to(repo_root)} is not tier=global")
        if "## Acceptance Criteria" not in text:
            failures.append(f"{path.relative_to(repo_root)} missing Acceptance Criteria")
    if failures:
        return LadderCheck(
            "standards.inventory",
            "All global standards are enforceable inputs",
            "fail",
            "Global standards inventory is incomplete.",
            tuple(failures),
        )
    return LadderCheck(
        "standards.inventory",
        "All global standards are enforceable inputs",
        "pass",
        f"{len(ids)} active global standard(s) found.",
        tuple(ids),
    )


def check_success_criteria_registry(repo_root: Path) -> LadderCheck:
    registry_path = repo_root / SUCCESS_CRITERIA_REGISTRY.relative_to(REPO_ROOT)
    payload = _json_file(registry_path)
    criteria = payload.get("criteria")
    failures: list[str] = []
    blocking_ids: list[str] = []
    if not isinstance(criteria, list) or not criteria:
        return LadderCheck(
            "criteria.registry",
            "Success criteria registry is complete",
            "fail",
            "No success criteria are registered.",
        )
    for item in criteria:
        if not isinstance(item, dict):
            failures.append("non-object criterion row")
            continue
        criterion_id = str(item.get("id", "")).strip()
        path_value = str(item.get("path", "")).strip()
        if not criterion_id:
            failures.append("criterion missing id")
        if bool(item.get("blocking")):
            blocking_ids.append(criterion_id)
        if not path_value:
            failures.append(f"{criterion_id or '<missing>'} missing path")
            continue
        if not (repo_root / path_value).exists():
            failures.append(f"{criterion_id or path_value} path missing: {path_value}")
    if not blocking_ids:
        failures.append("registry has no blocking criteria")
    if failures:
        return LadderCheck(
            "criteria.registry",
            "Success criteria registry is complete",
            "fail",
            "Success criteria registry has invalid rows.",
            tuple(failures),
        )
    return LadderCheck(
        "criteria.registry",
        "Success criteria registry is complete",
        "pass",
        f"{len(criteria)} criteria registered; {len(blocking_ids)} blocking.",
        tuple(blocking_ids),
    )


def check_standards_health_registry(repo_root: Path) -> LadderCheck:
    registry_path = repo_root / STANDARDS_REGISTRY.relative_to(REPO_ROOT)
    payload = _json_file(registry_path)
    profile_raw = payload.get("profile")
    profile = profile_raw if isinstance(profile_raw, dict) else {}
    standards_raw = payload.get("standards")
    standards = standards_raw if isinstance(standards_raw, list) else []
    failures: list[str] = []
    standard_ids: list[str] = []
    if not profile.get("id"):
        failures.append("standards registry profile missing id")
    if not standards:
        failures.append("standards registry has no standards")
    for item in standards:
        if not isinstance(item, dict):
            failures.append("non-object standard row")
            continue
        standard_id = str(item.get("id", "")).strip()
        domain = str(item.get("domain", "")).strip()
        severity = item.get("severity_if_missing")
        if not standard_id:
            failures.append("standard missing id")
        else:
            standard_ids.append(standard_id)
        if not domain:
            failures.append(f"{standard_id or '<missing>'} missing domain")
        if not isinstance(severity, int) or severity < 0 or severity > 5:
            failures.append(f"{standard_id or '<missing>'} invalid severity_if_missing: {severity}")
        if not isinstance(item.get("expected_state"), dict):
            failures.append(f"{standard_id or '<missing>'} missing expected_state")
        if not isinstance(item.get("remediation_playbook"), dict):
            failures.append(f"{standard_id or '<missing>'} missing remediation_playbook")
        if not isinstance(item.get("applicability"), dict):
            failures.append(f"{standard_id or '<missing>'} missing applicability")
    duplicates = sorted({item for item in standard_ids if standard_ids.count(item) > 1})
    if duplicates:
        failures.append(f"duplicate standards: {', '.join(duplicates)}")
    if failures:
        return LadderCheck(
            "standards.health_registry",
            "Standards health registry is complete",
            "fail",
            "Standards health registry has invalid rows.",
            tuple(failures),
        )
    return LadderCheck(
        "standards.health_registry",
        "Standards health registry is complete",
        "pass",
        f"{len(standard_ids)} standards-health rule(s) registered.",
        tuple(standard_ids[:12]),
    )


def check_quality_pipeline_includes_aios(repo_root: Path) -> LadderCheck:
    payload = _json_file(repo_root / QUALITY_PIPELINE_CONFIG.relative_to(REPO_ROOT))
    standard_raw = payload.get("standard")
    standard = standard_raw if isinstance(standard_raw, dict) else {}
    gates_raw = standard.get("gates")
    gates = gates_raw if isinstance(gates_raw, list) else []
    projects_raw = payload.get("projects")
    projects = projects_raw if isinstance(projects_raw, list) else []
    gate_keys = [str(gate.get("key", "")).strip() for gate in gates if isinstance(gate, dict)]
    duplicate_keys = sorted({key for key in gate_keys if key and gate_keys.count(key) > 1})
    aios_project = next(
        (
            project
            for project in projects
            if isinstance(project, dict) and str(project.get("project_id")) == "aios"
        ),
        None,
    )
    failures: list[str] = []
    if duplicate_keys:
        failures.append(f"duplicate gate keys: {', '.join(duplicate_keys)}")
    if aios_project is None:
        failures.append("quality pipeline has no project_id=aios entry")
    else:
        configured_raw = aios_project.get("gates")
        configured = configured_raw if isinstance(configured_raw, dict) else {}
        for required in (
            "lint",
            "test",
            "architecture",
            "pre_pr_readiness",
            "thermo_nuclear_simplification",
        ):
            if required not in configured:
                failures.append(f"aios gate not configured: {required}")
    if failures:
        return LadderCheck(
            "quality_pipeline.aios",
            "AIOS quality pipeline covers required gates",
            "fail",
            "Quality pipeline registry is not strong enough for commit gating.",
            tuple(failures),
        )
    return LadderCheck(
        "quality_pipeline.aios",
        "AIOS quality pipeline covers required gates",
        "pass",
        f"{len(gate_keys)} quality gate(s) registered.",
    )


def check_quality_gate_registry(repo_root: Path) -> LadderCheck:
    registry_path = repo_root / QUALITY_GATES_CONFIG.relative_to(REPO_ROOT)
    contract_path = repo_root / ".aios-quality-gate.json"
    if not registry_path.exists():
        return LadderCheck(
            "quality_gates.registry",
            "AIOS allowlisted quality gates are registered",
            "fail",
            "config/quality-gates.json is missing.",
        )
    if not contract_path.exists():
        return LadderCheck(
            "quality_gates.registry",
            "AIOS allowlisted quality gates are registered",
            "fail",
            ".aios-quality-gate.json is missing.",
        )
    registry = _json_file(registry_path)
    contract = _json_file(contract_path)
    known_gates_raw = registry.get("knownGates")
    known_gates = known_gates_raw if isinstance(known_gates_raw, list) else []
    projects_raw = registry.get("projects")
    projects = projects_raw if isinstance(projects_raw, list) else []
    failures: list[str] = []
    for required in ("test_quality", "architecture", "pre_cr", "thermo_nuclear_simplification"):
        if required not in known_gates:
            failures.append(f"known gate missing: {required}")
    aios_project = next(
        (
            project
            for project in projects
            if isinstance(project, dict) and project.get("projectId") == "aios"
        ),
        None,
    )
    if aios_project is None:
        failures.append("quality gate registry has no projectId=aios entry")
    else:
        configured_raw = aios_project.get("gates")
        configured = configured_raw if isinstance(configured_raw, dict) else {}
        for required in ("test_quality", "architecture", "pre_cr", "thermo_nuclear_simplification"):
            gate_raw = configured.get(required)
            gate = gate_raw if isinstance(gate_raw, dict) else None
            if gate is None:
                failures.append(f"aios gate not configured: {required}")
                continue
            if not isinstance(gate.get("preCommitCommands"), list):
                failures.append(f"aios gate missing preCommitCommands: {required}")
    if contract.get("projectId") != "aios":
        failures.append(".aios-quality-gate.json projectId must be aios")
    declared = contract.get("preCommitGates")
    if not isinstance(declared, list):
        failures.append(".aios-quality-gate.json preCommitGates must be a list")
    else:
        for required in ("test_quality", "architecture", "pre_cr", "thermo_nuclear_simplification"):
            if required not in declared:
                failures.append(f".aios-quality-gate.json missing preCommit gate: {required}")
    if failures:
        return LadderCheck(
            "quality_gates.registry",
            "AIOS allowlisted quality gates are registered",
            "fail",
            "AIOS quality gate registry is incomplete.",
            tuple(failures),
        )
    return LadderCheck(
        "quality_gates.registry",
        "AIOS allowlisted quality gates are registered",
        "pass",
        "AIOS quality gates require named allowlisted adapters.",
        tuple(str(gate) for gate in known_gates),
    )


def check_confident_event_loop_ordering(repo_root: Path, files: Sequence[str]) -> LadderCheck:
    findings: list[str] = []
    for relative_path in files:
        if Path(relative_path).suffix not in CODE_EXTENSIONS:
            continue
        text = staged_file_text(repo_root, relative_path)
        if text is None:
            continue
        findings.extend(_handler_before_send_findings(relative_path, text))
    if findings:
        return LadderCheck(
            "confident_code.event_loop_ordering",
            "No impossible handler-before-send races",
            "fail",
            "Message response handlers are registered before the send without an explicit runtime reason.",
            tuple(findings),
        )
    return LadderCheck(
        "confident_code.event_loop_ordering",
        "No impossible handler-before-send races",
        "pass",
        "No staged handler-before-send violations found.",
    )


def check_aios_evidence_artifacts(
    *,
    db_path: Path | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
) -> LadderCheck:
    if not run_id and not session_id:
        return LadderCheck(
            "aios.evidence_artifacts",
            "Fresh AIOS evidence artifacts are available",
            "skip",
            "AIOS evidence check unknown outside a managed run/session.",
        )
    resolved_db = db_path or Path("~/AIOS/data/aios.db").expanduser()
    if not resolved_db.exists():
        return LadderCheck(
            "aios.evidence_artifacts",
            "Fresh AIOS evidence artifacts are available",
            "skip",
            f"AIOS evidence check unknown; database missing at {resolved_db}.",
        )
    try:
        with sqlite3.connect(resolved_db) as conn:
            validation = validate_fresh_evidence(conn, run_id=run_id, session_id=session_id)
    except sqlite3.Error as exc:
        return LadderCheck(
            "aios.evidence_artifacts",
            "Fresh AIOS evidence artifacts are available",
            "skip",
            f"AIOS evidence check unknown; database query failed: {exc}.",
        )
    evidence = tuple(str(item) for item in validation.get("evidence", []))
    if evidence:
        return LadderCheck(
            "aios.evidence_artifacts",
            "Fresh AIOS evidence artifacts are available",
            "pass",
            f"{validation.get('usable_count', len(evidence))} fresh evidence artifact(s) found.",
            evidence,
        )
    return LadderCheck(
        "aios.evidence_artifacts",
        "Fresh AIOS evidence artifacts are available",
        "skip",
        "AIOS evidence check unknown; no fresh usable evidence artifacts found.",
    )


def check_aios_verifier_artifacts(
    *,
    db_path: Path | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
) -> LadderCheck:
    if not run_id and not session_id:
        return LadderCheck(
            "aios.verifier_artifacts",
            "Fresh AIOS verifier artifact is available",
            "skip",
            "AIOS verifier check unknown outside a managed run/session.",
        )
    resolved_db = db_path or Path("~/AIOS/data/aios.db").expanduser()
    if not resolved_db.exists():
        return LadderCheck(
            "aios.verifier_artifacts",
            "Fresh AIOS verifier artifact is available",
            "skip",
            f"AIOS verifier check unknown; database missing at {resolved_db}.",
        )
    try:
        with sqlite3.connect(resolved_db) as conn:
            refs = tuple(fresh_verifier_refs(conn, run_id=run_id, session_id=session_id))
    except sqlite3.Error as exc:
        return LadderCheck(
            "aios.verifier_artifacts",
            "Fresh AIOS verifier artifact is available",
            "skip",
            f"AIOS verifier check unknown; database query failed: {exc}.",
        )
    if refs:
        return LadderCheck(
            "aios.verifier_artifacts",
            "Fresh AIOS verifier artifact is available",
            "pass",
            f"{len(refs)} fresh verifier artifact(s) found for fail-closed eligibility.",
            refs,
        )
    return LadderCheck(
        "aios.verifier_artifacts",
        "Fresh AIOS verifier artifact is available",
        "skip",
        "AIOS verifier check unknown; verifier-dependent standards remain warn-only.",
    )


def _handler_before_send_findings(relative_path: str, text: str) -> list[str]:
    lines = text.splitlines()
    findings: list[str] = []
    for index, line in enumerate(lines):
        if not any(pattern in line for pattern in HANDLER_PATTERNS):
            continue
        if _has_allow_marker(lines, index):
            continue
        window = lines[index : index + 41]
        if any(any(pattern in candidate for pattern in SEND_PATTERNS) for candidate in window):
            findings.append(
                f"{relative_path}:{index + 1} registers a message handler before postMessage; "
                f"send first or add `{ALLOW_MARKER}: <reason>`."
            )
    return findings


def _has_allow_marker(lines: Sequence[str], index: int) -> bool:
    start = max(0, index - 3)
    end = min(len(lines), index + 1)
    return any(ALLOW_MARKER in line for line in lines[start:end])


def _json_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for raw_line in text[4:end].splitlines():
        if not raw_line or raw_line.startswith(" ") or raw_line.lstrip().startswith("- "):
            continue
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def _tail_lines(text: str, limit: int = 8) -> tuple[str, ...]:
    lines = [line for line in text.splitlines() if line.strip()]
    return tuple(lines[-limit:])


def print_report(checks: Sequence[LadderCheck], *, decision: GateDecision = "block") -> None:
    for check in checks:
        marker = {"pass": "PASS", "fail": "WARN" if decision == "warn" else "FAIL", "skip": "SKIP"}[
            check.status
        ]
        print(f"[{marker}] {check.label}: {check.detail}")
        for evidence in check.evidence:
            print(f"  - {evidence}")


def exit_code(checks: Sequence[LadderCheck], *, decision: GateDecision = "block") -> int:
    return 1 if decision == "block" and any(check.status == "fail" for check in checks) else 0


def emit_ladder_audit(
    repo_root: Path,
    checks: Sequence[LadderCheck],
    *,
    decision: GateDecision = "block",
) -> None:
    is_blocking = decision == "block"
    for check in checks:
        if check.status != "fail":
            continue
        disposition = "blocked commit" if is_blocking else "warning only"
        event = build_gate_audit_event(
            repo_root=repo_root,
            gate="AIOS",
            event_type="commit_blocked",
            severity="error" if is_blocking else "warning",
            category=_ladder_category(check.key),
            rule_id=check.key,
            rule_name=check.label,
            decision=decision,
            summary=f"AIOS quality ladder {disposition}: {check.detail}",
            evidence=[
                {
                    "file": _evidence_file(item),
                    "line_start": 1,
                    "reason": item,
                }
                for item in check.evidence[:10]
            ],
            failure_pattern=f"aios ladder failure: {check.key}",
            root_cause_hypothesis="The staged change reached commit readiness before the AIOS quality ladder was satisfied.",
            required_fix=check.detail,
            learning_lesson=f"Resolve `{check.label}` before committing AIOS changes.",
        )
        safe_append_gate_audit_event(repo_root, event)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AIOS commit quality ladder.")
    parser.add_argument("--no-context-validation", action="store_true")
    parser.add_argument("--staged-file", action="append", default=[])
    args = parser.parse_args(argv)
    checks = run_ladder(
        staged_files=args.staged_file or None,
        run_context_validation=not args.no_context_validation,
    )
    decision = (
        quality_gate_decision(REPO_ROOT)
        if any(check.status == "fail" for check in checks)
        else "block"
    )
    print_report(checks, decision=decision)
    emit_ladder_audit(REPO_ROOT, checks, decision=decision)
    return exit_code(checks, decision=decision)


def _ladder_category(key: str):
    if "test" in key or "criteria" in key:
        return "test"
    if "context" in key or "standards" in key:
        return "documentation"
    if "quality" in key or "hook" in key:
        return "process"
    if "event_loop" in key:
        return "maintainability"
    return "unknown"


def _evidence_file(evidence: str) -> str:
    candidate = evidence.split(":", 1)[0].strip()
    return candidate if candidate else "."
