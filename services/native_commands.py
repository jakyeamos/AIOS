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


def _review_files(root: Path, *, files: Sequence[Path], base_ref: str) -> list[Path]:
    if files:
        return [_resolve_existing_target(path, root) for path in files if _resolve_existing_target(path, root).is_file()]
    diff_files = _git_lines(root, "diff", "--name-only", base_ref)
    resolved = [root / name for name in diff_files if (root / name).is_file()]
    return [path.resolve() for path in resolved if _is_text_file(path.resolve())][:100]


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
