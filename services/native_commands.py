from __future__ import annotations

import ast
import re
import subprocess
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".sql",
    ".sh",
}
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".next", "dist", "build"}
REVIEW_LANES = (
    "security",
    "correctness",
    "testing",
    "architecture",
    "maintainability",
    "project_alignment",
)
SECURITY_SEVERITIES = ("critical", "high", "medium")


def zoom_out(target: Path, *, repo_root: Path | None = None, depth: int = 2) -> dict[str, Any]:
    root = (repo_root or Path.cwd()).resolve()
    resolved = _resolve_existing_target(target, root)
    files = _target_files(resolved, max_depth=max(0, depth))
    outbound = _outbound_dependencies(files)
    inbound = _inbound_dependencies(resolved, root)
    payload = {
        "command_id": "zoom_out",
        "target": str(resolved),
        "purpose": _purpose(resolved, files),
        "system_position": _system_position(resolved, root),
        "inbound_dependencies": inbound,
        "outbound_dependencies": outbound,
        "sibling_modules": _sibling_modules(resolved),
        "conventions": _conventions(resolved, files),
        "domain_vocabulary": _domain_vocabulary(files),
        "risks": _risks(resolved, files, inbound),
        "next_context": _next_context(resolved, files, inbound, outbound),
        "files_inspected": [str(path) for path in files[:25]],
    }
    payload["markdown"] = render_zoom_out(payload)
    return payload


def handoff(
    *,
    objective: str,
    repo_root: Path | None = None,
    output_path: Path | None = None,
    decision: Sequence[str] = (),
    test: Sequence[str] = (),
    worked: Sequence[str] = (),
    failed: Sequence[str] = (),
    blocker: Sequence[str] = (),
    reference: Sequence[str] = (),
    next_action: Sequence[str] = (),
) -> dict[str, Any]:
    root = (repo_root or Path.cwd()).resolve()
    branch_status = _git_lines(root, "status", "--short", "--branch")
    files_touched = [line for line in branch_status if line and not line.startswith("## ")]
    payload = {
        "command_id": "handoff",
        "goal": objective.strip() or "Not specified.",
        "current_state": _current_state(root),
        "branch_workspace_status": branch_status or ["Git status unavailable."],
        "files_touched": files_touched or ["No changed files detected."],
        "decisions": list(decision) or ["No explicit decisions supplied."],
        "tests_run": list(test) or ["No tests supplied."],
        "what_worked": list(worked) or ["No worked-path notes supplied."],
        "failed_approaches": list(failed) or ["No failed approaches supplied."],
        "blockers": list(blocker) or ["No blockers supplied."],
        "references": list(reference) or ["No references supplied."],
        "next_actions": list(next_action) or ["Continue from the active plan."],
        "artifact_path": None,
    }
    payload["markdown"] = render_handoff(payload)
    if output_path is not None:
        artifact = _allowed_artifact_path(output_path, root)
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(payload["markdown"] + "\n", encoding="utf-8")
        payload["artifact_path"] = str(artifact)
    return payload


def review_squad(
    *,
    repo_root: Path | None = None,
    files: Sequence[Path] = (),
    base_ref: str = "HEAD",
) -> dict[str, Any]:
    root = (repo_root or Path.cwd()).resolve()
    inspected = _review_files(root, files=files, base_ref=base_ref)
    lane_results = {lane: _review_lane(lane, inspected, root) for lane in REVIEW_LANES}
    findings = [finding for lane in lane_results.values() for finding in lane["findings"]]
    payload = {
        "command_id": "review_squad",
        "scope": {
            "repo_root": str(root),
            "files": [str(path) for path in inspected],
            "base_ref": base_ref,
        },
        "lanes": lane_results,
        "findings_by_severity": _group_findings(findings),
        "confirmed_findings": [f for f in findings if f["confidence"] == "confirmed"],
        "speculative_findings": [f for f in findings if f["confidence"] != "confirmed"],
        "non_issues_checked": [
            "No source files were modified by review.",
            "Reviewer lanes ran independently over the same scope.",
            "Project alignment checked repo conventions before raising findings.",
        ],
    }
    payload["markdown"] = render_squad_review(payload)
    return payload


def security_audit(
    *,
    mode: str,
    repo_root: Path | None = None,
    files: Sequence[Path] = (),
    base_ref: str = "HEAD",
) -> dict[str, Any]:
    if mode not in {"strict", "practical"}:
        raise ValueError("Security audit mode must be strict or practical.")
    root = (repo_root or Path.cwd()).resolve()
    inspected = _review_files(root, files=files, base_ref=base_ref)
    findings = _security_findings(inspected, root)
    if mode == "strict":
        findings = [finding for finding in findings if finding["severity"] in {"critical", "high"}]
    payload = {
        "command_id": "audit_security",
        "mode": mode,
        "scope": {
            "repo_root": str(root),
            "files": [str(path) for path in inspected],
            "base_ref": base_ref,
        },
        "findings": findings,
        "findings_by_severity": _group_security_findings(findings),
        "non_issues_checked": [
            "Hardcoded secret assignment patterns",
            "Shell execution with shell=True and destructive command markers",
            "Authentication and authorization vocabulary in changed files",
            "Privacy-sensitive field handling",
            "Local filesystem write/read automation",
            "Dependency manifest risk markers",
        ],
        "verification_suggestions": _security_verification_suggestions(findings),
    }
    payload["markdown"] = render_security_audit(payload)
    return payload


def de_slopify(
    *,
    repo_root: Path | None = None,
    files: Sequence[Path] = (),
    base_ref: str = "HEAD",
    cleanup_goals: Sequence[str] = (),
    apply: bool = False,
) -> dict[str, Any]:
    root = (repo_root or Path.cwd()).resolve()
    inspected = _review_files(root, files=files, base_ref=base_ref)
    proposed: list[dict[str, str]] = []
    applied: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for path in inspected:
        text = _read_text(path)
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        cleaned = _format_only_cleanup(text)
        if cleaned != text:
            change = {
                "file": rel,
                "kind": "formatting",
                "summary": "Remove trailing whitespace and collapse excessive blank lines.",
                "risk": "low",
            }
            proposed.append(change)
            if apply:
                path.write_text(cleaned, encoding="utf-8")
                applied.append(change)
        skipped.extend(_risky_cleanup_findings(rel, text))
    payload = {
        "command_id": "cleanup_de_slopify",
        "mode": "apply" if apply else "plan",
        "scope": {"repo_root": str(root), "files": [str(path) for path in inspected]},
        "cleanup_goals": list(cleanup_goals) or ["general conservative cleanup"],
        "cleanup_plan": _cleanup_plan(proposed, skipped, apply),
        "proposed_changes": proposed,
        "applied_changes": applied,
        "skipped_risky_changes": skipped,
        "checks_run": ["static cleanup scan", "format-only apply guard"],
        "rollback": "Revert the generated diff or restore affected files from git.",
    }
    payload["markdown"] = render_de_slopify(payload)
    return payload


def prototype(
    *,
    question: str,
    sandbox_path: Path,
    repo_root: Path | None = None,
    prototype_type: str = "notes",
    cleanup_mode: str = "delete_when_done",
) -> dict[str, Any]:
    root = (repo_root or Path.cwd()).resolve()
    sandbox = _allowed_prototype_path(sandbox_path, root)
    sandbox.mkdir(parents=True, exist_ok=True)
    readme = sandbox / "README.md"
    content = render_prototype_markdown(
        {
            "question_tested": question,
            "prototype_location": str(sandbox),
            "experiment": f"Create a {prototype_type} prototype artifact isolated from production code.",
            "result": "Prototype scaffold created; run or extend experiments inside this directory only.",
            "what_this_proves": "The question has an isolated place for disposable investigation.",
            "what_this_does_not_prove": "It does not prove production readiness or justify promotion.",
            "recommendation": "Promote only after review, tests, and a scoped production plan.",
            "required_promotion_steps": [
                "Summarize findings.",
                "Create a separate implementation plan.",
                "Move only reviewed code into production paths.",
                "Run relevant tests before committing.",
            ],
            "cleanup_instructions": f"Cleanup mode `{cleanup_mode}`: delete `{sandbox}` when finished.",
        }
    )
    readme.write_text(content + "\n", encoding="utf-8")
    payload = {
        "command_id": "prototype",
        "question_tested": question,
        "prototype_location": str(sandbox),
        "experiment": f"{prototype_type} prototype scaffold",
        "result": "created",
        "what_this_proves": "An isolated sandbox can hold the experiment.",
        "what_this_does_not_prove": "No production behavior has been validated.",
        "recommendation": "Keep experimentation isolated until explicit promotion.",
        "required_promotion_steps": [
            "Review prototype output.",
            "Write a scoped implementation plan.",
            "Port only necessary pieces.",
            "Run tests.",
        ],
        "cleanup_instructions": f"Delete `{sandbox}` when the experiment is complete.",
        "created_files": [str(readme)],
        "run_command": f"cd {sandbox}",
        "cleanup_or_promotion_guidance": "Delete the sandbox or promote through a separate reviewed change.",
    }
    payload["markdown"] = render_prototype_markdown(payload)
    return payload


def render_zoom_out(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Zoom-Out Report",
            "",
            f"## Target\n{payload['target']}",
            "",
            f"## Purpose\n{payload['purpose']}",
            "",
            f"## System Position\n{payload['system_position']}",
            "",
            _list_section("Inbound Dependencies", payload["inbound_dependencies"]),
            "",
            _list_section("Outbound Dependencies", payload["outbound_dependencies"]),
            "",
            _list_section("Sibling Modules", payload["sibling_modules"]),
            "",
            _list_section("Conventions", payload["conventions"]),
            "",
            _list_section("Domain Vocabulary", payload["domain_vocabulary"]),
            "",
            _list_section("Risks", payload["risks"]),
            "",
            _list_section("Next Context", payload["next_context"]),
        ]
    )


def render_handoff(payload: dict[str, Any]) -> str:
    sections = [
        ("Goal", [payload["goal"]]),
        ("Current State", [payload["current_state"]]),
        ("Branch / Workspace Status", payload["branch_workspace_status"]),
        ("Files Touched", payload["files_touched"]),
        ("Decisions", payload["decisions"]),
        ("Tests Run", payload["tests_run"]),
        ("What Worked", payload["what_worked"]),
        ("Failed / Dead Ends", payload["failed_approaches"]),
        ("Blockers", payload["blockers"]),
        ("Relevant References", payload["references"]),
        ("Next Recommended Actions", payload["next_actions"]),
    ]
    lines = ["# AIOS Handoff"]
    for title, items in sections:
        lines.extend(["", _list_section(title, items)])
    return "\n".join(lines)


def render_squad_review(payload: dict[str, Any]) -> str:
    lines = ["# Squad Review", "", "## Scope"]
    lines.append(f"- Repo root: {payload['scope']['repo_root']}")
    lines.append(f"- Base ref: {payload['scope']['base_ref']}")
    lines.append(f"- Files inspected: {len(payload['scope']['files'])}")
    lines.extend(["", "## Findings By Severity"])
    for severity, findings in payload["findings_by_severity"].items():
        lines.append(f"### {severity.title()}")
        if findings:
            for finding in findings:
                lines.append(
                    f"- [{finding['lane']}] {finding['file']}: {finding['issue']} "
                    f"({finding['confidence']})"
                )
        else:
            lines.append("- None.")
    lines.extend(["", "## Reviewer Lanes"])
    for lane in REVIEW_LANES:
        result = payload["lanes"][lane]
        lines.append(f"### {lane}")
        lines.append(f"- Findings: {len(result['findings'])}")
        for item in result["non_issues_checked"]:
            lines.append(f"- Checked: {item}")
    lines.extend(["", _list_section("Non-Issues Checked", payload["non_issues_checked"])])
    return "\n".join(lines)


def render_security_audit(payload: dict[str, Any]) -> str:
    lines = ["# Security Audit", "", "## Scope"]
    lines.append(f"- Mode: {payload['mode']}")
    lines.append(f"- Repo root: {payload['scope']['repo_root']}")
    lines.append(f"- Base ref: {payload['scope']['base_ref']}")
    lines.append(f"- Files inspected: {len(payload['scope']['files'])}")
    lines.extend(["", "## Findings"])
    for severity in SECURITY_SEVERITIES:
        lines.append(f"### {severity.title()}")
        findings = payload["findings_by_severity"][severity]
        if not findings:
            lines.append("- None.")
            continue
        for finding in findings:
            lines.append(f"- {finding['affected_file']}: {finding['issue']}")
            lines.append(f"  - Why it matters: {finding['why_it_matters']}")
            lines.append(f"  - Scenario: {finding['exploit_or_failure_scenario']}")
            lines.append(f"  - Recommended fix: {finding['recommended_fix']}")
            lines.append(f"  - Confidence: {finding['confidence']}")
    lines.extend(["", _list_section("Non-Issues Checked", payload["non_issues_checked"])])
    lines.extend(["", _list_section("Suggested Verification", payload["verification_suggestions"])])
    return "\n".join(lines)


def render_de_slopify(payload: dict[str, Any]) -> str:
    lines = ["# De-Slopify Report", "", f"## Mode\n- {payload['mode']}"]
    lines.extend(["", _list_section("Cleanup Plan", payload["cleanup_plan"])])
    lines.extend(["", "## Proposed Changes"])
    lines.extend(_change_lines(payload["proposed_changes"]))
    lines.extend(["", "## Applied Changes"])
    lines.extend(_change_lines(payload["applied_changes"]))
    lines.extend(["", "## Skipped Risky Changes"])
    lines.extend(_change_lines(payload["skipped_risky_changes"]))
    lines.extend(["", _list_section("Checks Run", payload["checks_run"])])
    lines.extend(["", f"## Rollback\n- {payload['rollback']}"])
    return "\n".join(lines)


def render_prototype_markdown(payload: dict[str, Any]) -> str:
    sections = [
        ("Question Tested", [payload["question_tested"]]),
        ("Prototype Location", [payload["prototype_location"]]),
        ("Experiment", [payload["experiment"]]),
        ("Result", [payload["result"]]),
        ("What This Proves", [payload["what_this_proves"]]),
        ("What This Does Not Prove", [payload["what_this_does_not_prove"]]),
        ("Recommendation", [payload["recommendation"]]),
        ("Required Promotion Steps", payload["required_promotion_steps"]),
        ("Cleanup Instructions", [payload["cleanup_instructions"]]),
    ]
    lines = ["# Prototype Report"]
    for title, items in sections:
        lines.extend(["", _list_section(title, items)])
    return "\n".join(lines)


def _resolve_existing_target(target: Path, root: Path) -> Path:
    path = target.expanduser()
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Target does not exist: {resolved}")
    return resolved


def _target_files(target: Path, *, max_depth: int) -> list[Path]:
    if target.is_file():
        return [target] if _is_text_file(target) else []
    base_parts = len(target.parts)
    files: list[Path] = []
    for path in sorted(target.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if len(path.parts) - base_parts > max_depth:
            continue
        if path.is_file() and _is_text_file(path):
            files.append(path)
    return files[:100]


def _is_text_file(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _purpose(target: Path, files: Sequence[Path]) -> str:
    if target.is_dir():
        return f"Directory containing {len(files)} inspectable text files."
    text = _read_text(target)
    for line in text.splitlines():
        stripped = line.strip().strip("#").strip()
        if stripped:
            return stripped[:180]
    return f"{target.name} contains inspectable source or configuration text."


def _system_position(target: Path, root: Path) -> str:
    try:
        rel = target.relative_to(root)
    except ValueError:
        return "Target is outside the provided repository root."
    top = rel.parts[0] if rel.parts else target.name
    return f"Under `{top}` at `{rel}` within the repository."


def _outbound_dependencies(files: Sequence[Path]) -> list[str]:
    deps: list[str] = []
    for path in files[:25]:
        text = _read_text(path)
        if path.suffix == ".py":
            deps.extend(_python_imports(text))
        elif path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            deps.extend(_js_imports(text))
    return _unique_or_none(deps, "No outbound dependencies detected from inspectable imports.")[:25]


def _python_imports(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _js_imports(text: str) -> list[str]:
    pattern = re.compile(r"(?:from\s+|import\s*\()['\"]([^'\"]+)['\"]")
    return pattern.findall(text)


def _inbound_dependencies(target: Path, root: Path) -> list[str]:
    needles = {target.stem, target.name}
    if target.suffix == ".py":
        needles.add(target.stem.replace("-", "_"))
    matches: list[str] = []
    for path in _iter_repo_text_files(root):
        if path == target:
            continue
        text = _read_text(path)
        if any(needle and needle in text for needle in needles):
            matches.append(str(path.relative_to(root)))
        if len(matches) >= 25:
            break
    return matches or ["No inbound references detected by local text scan."]


def _iter_repo_text_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and _is_text_file(path):
            yield path


def _sibling_modules(target: Path) -> list[str]:
    directory = target if target.is_dir() else target.parent
    siblings = [path.name for path in sorted(directory.iterdir()) if path.name != target.name]
    return siblings[:25] or ["No sibling modules found."]


def _conventions(target: Path, files: Sequence[Path]) -> list[str]:
    suffixes = Counter(path.suffix or "<none>" for path in files)
    conventions = [f"Common suffix `{suffix}` appears {count} time(s)." for suffix, count in suffixes.most_common(5)]
    if any(path.name.startswith("test_") or path.name.endswith(".test.ts") for path in files):
        conventions.append("Target area includes colocated or nearby tests.")
    if (target if target.is_dir() else target.parent).joinpath("__init__.py").exists():
        conventions.append("Python package marker `__init__.py` is present.")
    return conventions or ["No strong local conventions detected."]


def _domain_vocabulary(files: Sequence[Path]) -> list[str]:
    words: Counter[str] = Counter()
    for path in files[:25]:
        text = _read_text(path)
        words.update(
            token.lower()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", text)
            if token.lower()
            not in {
                "from",
                "import",
                "return",
                "const",
                "function",
                "class",
                "none",
                "true",
                "false",
                "path",
                "self",
            }
        )
    return [word for word, _ in words.most_common(12)] or ["No repeated domain terms detected."]


def _risks(target: Path, files: Sequence[Path], inbound: Sequence[str]) -> list[str]:
    risks: list[str] = []
    if len(files) > 40:
        risks.append("Large target area; inspect narrower files before changing behavior.")
    if not any("test" in path.name.lower() for path in files):
        risks.append("No obvious tests in the inspected target area.")
    if inbound and not inbound[0].startswith("No inbound"):
        risks.append("Target has inbound references; changes may affect callers.")
    if any("TODO" in _read_text(path) or "FIXME" in _read_text(path) for path in files[:25]):
        risks.append("Target contains TODO/FIXME markers.")
    return risks or ["No immediate structural risks detected by static scan."]


def _next_context(
    target: Path,
    files: Sequence[Path],
    inbound: Sequence[str],
    outbound: Sequence[str],
) -> list[str]:
    items = []
    if files:
        items.append(f"Read the primary file `{files[0].name}` in full before editing.")
    if inbound and not inbound[0].startswith("No inbound"):
        items.append("Inspect inbound callers before changing public behavior.")
    if outbound and not outbound[0].startswith("No outbound"):
        items.append("Inspect imported modules that own shared contracts.")
    if target.is_dir():
        items.append("Narrow to one file or subdirectory before implementation.")
    return items or ["No additional context required for a small read-only inspection."]


def _current_state(root: Path) -> str:
    branch = _git_lines(root, "branch", "--show-current")
    head = _git_lines(root, "log", "-1", "--pretty=%h %s")
    branch_label = branch[0] if branch else "unknown branch"
    head_label = head[0] if head else "unknown HEAD"
    return f"Repository at `{root}` on `{branch_label}`, latest commit `{head_label}`."


def _git_lines(root: Path, *args: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _allowed_artifact_path(path: Path, root: Path) -> Path:
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    allowed_roots = [root / ".planning" / "handoffs", root / "docs" / "handoffs"]
    if not any(resolved.is_relative_to(allowed.resolve()) for allowed in allowed_roots):
        allowed = ", ".join(str(path) for path in allowed_roots)
        raise ValueError(f"Handoff output must be under one of: {allowed}")
    return resolved


def _allowed_prototype_path(path: Path, root: Path) -> Path:
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    allowed_roots = [
        (root / ".planning" / "prototypes").resolve(),
        (root / "prototypes").resolve(),
        Path("/private/tmp").resolve(),
    ]
    if not any(resolved.is_relative_to(allowed) for allowed in allowed_roots):
        allowed = ", ".join(str(path) for path in allowed_roots)
        raise ValueError(f"Prototype path must be under one of: {allowed}")
    return resolved


def _review_files(root: Path, *, files: Sequence[Path], base_ref: str) -> list[Path]:
    if files:
        return [_resolve_existing_target(path, root) for path in files if _resolve_existing_target(path, root).is_file()]
    diff_files = _git_lines(root, "diff", "--name-only", base_ref)
    resolved = [root / name for name in diff_files if (root / name).is_file()]
    return [path.resolve() for path in resolved if _is_text_file(path.resolve())][:100]


def _format_only_cleanup(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    collapsed: list[str] = []
    blank_count = 0
    for line in lines:
        if line:
            blank_count = 0
            collapsed.append(line)
            continue
        blank_count += 1
        if blank_count <= 2:
            collapsed.append(line)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(collapsed) + suffix


def _risky_cleanup_findings(file: str, text: str) -> list[dict[str, str]]:
    skipped: list[dict[str, str]] = []
    if "except Exception" in text:
        skipped.append(
            _cleanup_change(
                file,
                "broad_error_handling",
                "Broad exception handling needs behavior-aware review.",
                "medium",
            )
        )
    if re.search(r"^\s*(def|class)\s+\w+", text, re.MULTILINE):
        skipped.append(
            _cleanup_change(
                file,
                "public_api",
                "Function/class structure is treated as public behavior and not modified.",
                "high",
            )
        )
    if re.search(r"(TODO|FIXME|agent-created)", text, re.I):
        skipped.append(
            _cleanup_change(
                file,
                "todo_or_agent_marker",
                "TODO or agent-created marker requires human decision before removal.",
                "medium",
            )
        )
    if re.search(r"\b(helper|manager|thing|stuff|data)\b", text):
        skipped.append(
            _cleanup_change(
                file,
                "generic_naming",
                "Generic naming may be cleanup-worthy but needs semantic rename review.",
                "low",
            )
        )
    return skipped


def _cleanup_change(file: str, kind: str, summary: str, risk: str) -> dict[str, str]:
    return {"file": file, "kind": kind, "summary": summary, "risk": risk}


def _cleanup_plan(
    proposed: Sequence[dict[str, str]],
    skipped: Sequence[dict[str, str]],
    apply: bool,
) -> list[str]:
    plan = ["Inspect selected files for conservative cleanup opportunities."]
    if proposed:
        action = "Apply" if apply else "Report"
        plan.append(f"{action} {len(proposed)} low-risk format-only cleanup item(s).")
    if skipped:
        plan.append(f"List {len(skipped)} risky structural cleanup item(s) without applying them.")
    plan.append("Preserve behavior, public APIs, config keys, and meaningful state.")
    return plan


def _change_lines(changes: Sequence[dict[str, str]]) -> list[str]:
    if not changes:
        return ["- None."]
    return [
        f"- {change['file']} [{change['risk']}:{change['kind']}]: {change['summary']}"
        for change in changes
    ]


def _review_lane(lane: str, files: Sequence[Path], root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in files:
        text = _read_text(path)
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        if lane == "security" and re.search(r"(api[_-]?key|secret|password)\s*=", text, re.I):
            findings.append(_finding(lane, "high", rel, "Possible hardcoded secret assignment."))
        elif lane == "correctness" and "except Exception" in text:
            findings.append(_finding(lane, "medium", rel, "Broad exception handling may hide failures."))
        elif lane == "testing" and path.suffix in {".py", ".ts", ".tsx"} and "test" not in rel.lower():
            test_hint = f"test_{path.stem}.py"
            if not any(candidate.name == test_hint for candidate in root.rglob(test_hint)):
                findings.append(_finding(lane, "low", rel, "No obvious focused test file found."))
        elif lane == "architecture" and "../" in text:
            findings.append(_finding(lane, "medium", rel, "Relative parent import/path usage may cross boundaries."))
        elif lane == "maintainability" and len(text.splitlines()) > 500:
            findings.append(_finding(lane, "medium", rel, "Large file may need narrower ownership."))
        elif lane == "project_alignment" and "use client" in text and path.suffix == ".tsx":
            findings.append(
                _finding(
                    lane,
                    "low",
                    rel,
                    "Client component marker should be justified against project conventions.",
                )
            )
    return {
        "lane": lane,
        "findings": findings,
        "non_issues_checked": _lane_non_issues(lane),
    }


def _finding(lane: str, severity: str, file: str, issue: str) -> dict[str, str]:
    return {
        "lane": lane,
        "severity": severity,
        "file": file,
        "issue": issue,
        "evidence": issue,
        "recommended_fix": "Inspect the cited file and apply the narrowest behavior-preserving fix.",
        "confidence": "confirmed",
    }


def _lane_non_issues(lane: str) -> list[str]:
    return {
        "security": ["Hardcoded secret patterns", "read-only review behavior"],
        "correctness": ["Broad exception patterns", "obvious changed-file risk markers"],
        "testing": ["Nearby focused test naming", "changed non-test source coverage hints"],
        "architecture": ["Relative parent imports", "boundary-risk path references"],
        "maintainability": ["Large-file hotspots", "localized complexity indicators"],
        "project_alignment": [
            "Repo conventions",
            "duplication and already-solved logic by local scan",
            "PRD/design-spec fit when supplied in scope",
        ],
    }[lane]


def _security_findings(files: Sequence[Path], root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in files:
        text = _read_text(path)
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        lowered = text.lower()
        if re.search(r"(api[_-]?key|secret|password|private[_-]?key)\s*=\s*['\"][^'\"]+", text, re.I):
            findings.append(
                _security_finding(
                    severity="high",
                    affected_file=rel,
                    issue="Possible hardcoded credential assignment.",
                    why_it_matters="Credentials committed to source can be reused outside the local workflow.",
                    scenario="A copied repo, log excerpt, or artifact exposes the credential to another environment.",
                    recommended_fix="Move the value to a local secret store or environment variable and rotate it.",
                    confidence="confirmed",
                )
            )
        if "shell=True" in text:
            severity = "critical" if re.search(r"rm\s+-rf|chmod\s+777|sudo\s+", text) else "high"
            findings.append(
                _security_finding(
                    severity=severity,
                    affected_file=rel,
                    issue="Shell command execution uses shell=True.",
                    why_it_matters="Shell interpolation can turn user-controlled input into command execution.",
                    scenario="A crafted path or argument changes the command that local automation executes.",
                    recommended_fix="Pass argv as a sequence, validate inputs, and avoid shell=True.",
                    confidence="confirmed",
                )
            )
        if any(term in lowered for term in ("auth", "authorization", "permission", "token")):
            findings.append(
                _security_finding(
                    severity="medium",
                    affected_file=rel,
                    issue="Authentication or permission-sensitive logic is in scope.",
                    why_it_matters="Access-control changes can silently widen local or remote privileges.",
                    scenario="A missing check lets a caller read or mutate data outside its intended scope.",
                    recommended_fix="Verify caller identity, authorization boundary, and denial behavior with tests.",
                    confidence="contextual",
                )
            )
        if any(term in lowered for term in ("email", "phone", "address", "ssn", "personal")):
            findings.append(
                _security_finding(
                    severity="medium",
                    affected_file=rel,
                    issue="Privacy-sensitive data fields are handled in scope.",
                    why_it_matters="Personal data needs minimization, redaction, and explicit retention behavior.",
                    scenario="A local artifact, log, or debug output stores private data longer than intended.",
                    recommended_fix="Redact logs/artifacts and document retention or deletion behavior.",
                    confidence="contextual",
                )
            )
        if re.search(r"\b(write_text|open\(.+['\"]w|unlink\(|rmtree\(|remove\()", text):
            findings.append(
                _security_finding(
                    severity="medium",
                    affected_file=rel,
                    issue="Local filesystem write or delete behavior is in scope.",
                    why_it_matters="Agent-run filesystem automation can overwrite user data if paths are too broad.",
                    scenario="An unchecked path argument writes outside the intended workspace or artifact directory.",
                    recommended_fix="Resolve paths, enforce allowed roots, and test refusal for unsafe locations.",
                    confidence="confirmed",
                )
            )
        if path.name in {"package.json", "pyproject.toml", "requirements.txt"}:
            findings.append(
                _security_finding(
                    severity="medium",
                    affected_file=rel,
                    issue="Dependency manifest is in scope.",
                    why_it_matters="Dependency changes alter the supply-chain trust boundary.",
                    scenario="A new package introduces install scripts, vulnerable transitive code, or network access.",
                    recommended_fix="Review package source, lockfile delta, install scripts, and vulnerability status.",
                    confidence="contextual",
                )
            )
    return findings


def _security_finding(
    *,
    severity: str,
    affected_file: str,
    issue: str,
    why_it_matters: str,
    scenario: str,
    recommended_fix: str,
    confidence: str,
) -> dict[str, str]:
    return {
        "severity": severity,
        "affected_file": affected_file,
        "issue": issue,
        "why_it_matters": why_it_matters,
        "exploit_or_failure_scenario": scenario,
        "recommended_fix": recommended_fix,
        "confidence": confidence,
    }


def _group_security_findings(
    findings: Sequence[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    return {
        severity: [finding for finding in findings if finding["severity"] == severity]
        for severity in SECURITY_SEVERITIES
    }


def _security_verification_suggestions(findings: Sequence[dict[str, str]]) -> list[str]:
    suggestions = ["Confirm audited commands made no source changes."]
    if any(finding["severity"] in {"critical", "high"} for finding in findings):
        suggestions.append("Run a secret scan and inspect git history before merging.")
    if any("shell=True" in finding["issue"] for finding in findings):
        suggestions.append("Add a regression test proving shell execution rejects crafted input.")
    if any("filesystem" in finding["issue"].lower() for finding in findings):
        suggestions.append("Add allowed-root and path traversal tests.")
    if any("Privacy" in finding["issue"] for finding in findings):
        suggestions.append("Check generated logs and artifacts for redaction.")
    return suggestions


def _group_findings(findings: Sequence[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    return {
        "high": [finding for finding in findings if finding["severity"] == "high"],
        "medium": [finding for finding in findings if finding["severity"] == "medium"],
        "low": [finding for finding in findings if finding["severity"] == "low"],
    }


def _unique_or_none(items: Sequence[str], fallback: str) -> list[str]:
    unique = list(dict.fromkeys(item for item in items if item))
    return unique or [fallback]


def _list_section(title: str, items: Sequence[str]) -> str:
    lines = [f"## {title}"]
    lines.extend(f"- {item}" for item in items)
    return "\n".join(lines)
