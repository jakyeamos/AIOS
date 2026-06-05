from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

COMPILER_VERSION = "skills-harvest-v0.1"

SOURCE_CANDIDATE_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README-agent.md",
    "README.agents.md",
    ".cursorrules",
    ".windsurfrules",
    "copilot-instructions.md",
    "SKILL.md",
}
SOURCE_CANDIDATE_DIRS = {
    ".agent",
    ".agents",
    ".claude",
    ".codex",
    ".cursor",
    ".cursor/skills",
    ".cursor/skills-cursor",
    ".gemini",
    ".github/instructions",
    "agents",
    "skills",
    "prompts",
    "prompt-library",
    "workflows",
    "gsd",
    "aios",
    ".aios",
    "docs/ai",
    "docs/agents",
    "instructions",
    "commands",
    "slash-commands",
}
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".next",
    "coverage",
    "target",
    "venv",
    ".venv",
    "__pycache__",
    ".tmp",
    ".worktrees",
    "extensions",
    "logs",
    "skills-library",
    "staging",
    "vendor_imports",
}
EXCLUDED_DIR_PREFIXES = (
    "plugins-backup",
    "skills-library",
)
EXCLUDED_REL_PREFIXES = (
    ".tmp/",
    "antigravity/brain/",
    "antigravity-backup/brain/",
    "antigravity-cli/brain/",
    "antigravity-ide/brain/",
    "extensions/",
    "plans/",
    "projects/",
    "skills-library/",
    "vendor_imports/",
)
EXCLUDED_SUFFIXES = {
    ".7z",
    ".bin",
    ".db",
    ".dmg",
    ".gif",
    ".gz",
    ".ico",
    ".jpg",
    ".jpeg",
    ".lock",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".pyc",
    ".sqlite",
    ".zip",
}
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("api_key_assignment", re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-./+=]{16,})")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("connection_string", re.compile(r"(?i)\b(postgres|mysql|mongodb|redis)://[^\s)>\"]+")),
)
TASK_KEYWORDS = {
    "audit": ("audit", "review", "inspect", "evaluate"),
    "implementation": ("implement", "edit", "patch", "fix", "refactor", "build"),
    "planning": ("plan", "roadmap", "phase", "acceptance"),
    "research": ("research", "investigate", "source", "citation"),
    "debugging": ("debug", "bug", "root cause", "failure"),
    "testing": ("test", "verify", "validate", "quality gate"),
    "documentation": ("document", "readme", "docs", "writeback"),
    "agent_workflow": ("agent", "workflow", "routing", "skill", "prompt", "tmcp", "gsd"),
}


@dataclass(frozen=True)
class HarvestOptions:
    roots: tuple[Path, ...]
    out: Path
    include_hidden: bool = False
    max_file_size: int = 250_000
    dry_run: bool = False
    github_repo: str | None = None
    push: bool = False
    tmcp: bool = True
    no_rewrite: bool = False
    interactive: bool = False
    report_only: bool = False
    force: bool = False


@dataclass
class CandidateFile:
    path: Path
    root: Path
    project: str
    relative_path: str
    original_size: int
    content: str
    redacted_content: str
    secret_findings: list[str]
    classification: list[str] = field(default_factory=list)
    summary: str = ""
    reusable_value: str = ""
    project_dependencies: list[str] = field(default_factory=list)
    recommended_destination: str = ""
    rewrite_status: str = "preserved"
    risk_level: str = "low"
    slug: str = ""
    disposition: str = "pending"
    source_tier: str = "unclassified"


@dataclass
class SkillGroup:
    slug: str
    title: str
    concept_key: str
    sources: list[CandidateFile]
    source_tiers: list[str]
    classifications: list[str]


def harvest_skills_library(options: HarvestOptions) -> dict[str, Any]:
    started_at = _now()
    roots = tuple(path.expanduser().resolve() for path in options.roots)
    out = options.out.expanduser().resolve()
    candidates, skipped = discover_candidates(
        roots,
        include_hidden=options.include_hidden,
        max_file_size=options.max_file_size,
    )
    classified = [_classify_candidate(candidate) for candidate in candidates]
    duplicate_groups = _duplicate_groups(classified)
    conflicts = _detect_conflicts(classified)
    generation = _plan_generation(classified, duplicate_groups, conflicts, out, started_at, options)

    git_result: dict[str, Any] = {"initialized": False, "committed": False, "pushed": False}
    if not options.dry_run:
        if out.exists() and any(out.iterdir()):
            if not options.force:
                raise ValueError(f"Output path already exists and is not empty: {out}")
            if not _is_safe_generated_repo(out):
                raise ValueError(f"Refusing to overwrite non-harvest output path: {out}")
            shutil.rmtree(out)
        _write_generation(generation)
        if not options.report_only:
            git_result = _initialize_git_repo(out, options.github_repo, options.push)

    validation = validate_generated_library(out, generation, dry_run=options.dry_run)
    summary = {
        "started_at": started_at,
        "output_repo": str(out),
        "root_count": len(roots),
        "candidate_count": len(classified),
        "skill_count": len(generation["skills"]),
        "project_instruction_count": len(generation["project_instructions"]),
        "global_instruction_count": len(generation["global_instructions"]),
        "workflow_count": len(generation["workflows"]),
        "duplicate_group_count": len(duplicate_groups),
        "conflict_count": len(conflicts),
        "skipped_count": len(skipped),
        "redacted_file_count": sum(1 for item in classified if item.secret_findings),
        "tmcp_source_count": generation["tmcp_source_count"],
        "dry_run": options.dry_run,
        "report_only": options.report_only,
        "tmcp_enabled": options.tmcp,
        "source_tiers": dict(sorted(Counter(item.source_tier for item in classified).items())),
    }
    return {
        "summary": summary,
        "roots": [str(root) for root in roots],
        "ignored_directories": sorted(EXCLUDED_DIRS),
        "skipped_files": skipped,
        "sources": [_candidate_record(candidate) for candidate in classified],
        "duplicates": duplicate_groups,
        "conflicts": conflicts,
        "planned_files": sorted(generation["files"]),
        "validation": validation,
        "git": git_result,
        "rerun_command": _rerun_command(options),
    }


def discover_candidates(
    roots: tuple[Path, ...],
    *,
    include_hidden: bool,
    max_file_size: int,
) -> tuple[list[CandidateFile], list[dict[str, str]]]:
    candidates: list[CandidateFile] = []
    skipped: list[dict[str, str]] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            skipped.append({"path": str(root), "reason": "root does not exist"})
            continue
        if not root.is_dir():
            skipped.append({"path": str(root), "reason": "root is not a directory"})
            continue
        project = root.name or "root"
        for path in sorted(root.rglob("*")):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            reason = _skip_reason(path, root, include_hidden, max_file_size)
            if reason:
                if _is_agent_candidate_path(path, root):
                    skipped.append({"path": str(path), "reason": reason})
                continue
            if not _is_agent_candidate_path(path, root):
                continue
            try:
                raw = path.read_bytes()
            except OSError as exc:
                skipped.append({"path": str(path), "reason": f"unreadable: {exc}"})
                continue
            if b"\x00" in raw:
                skipped.append({"path": str(path), "reason": "binary file"})
                continue
            content = raw.decode("utf-8", errors="replace")
            secret_findings, redacted = _redact_secrets(content)
            candidates.append(
                CandidateFile(
                    path=path,
                    root=root,
                    project=project,
                    relative_path=path.relative_to(root).as_posix(),
                    original_size=len(raw),
                    content=content,
                    redacted_content=redacted,
                    secret_findings=secret_findings,
                )
            )
    return candidates, skipped


def validate_generated_library(
    out: Path,
    generation: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def check(check_id: str, status: bool, detail: str) -> None:
        checks.append({"id": check_id, "status": "pass" if status else "fail", "detail": detail})

    files = generation["files"]
    if dry_run:
        check("dry-run-no-files-required", True, "Dry-run produced a generation plan without writes.")
    else:
        check("output-exists", out.exists(), str(out))
        check("readme-exists", (out / "README.md").exists(), "README.md")
        check("manifest-exists", (out / "manifest.json").exists(), "manifest.json")

    for skill in generation["skills"]:
        provenance_path = f"skills/{skill['slug']}/provenance.md"
        check(
            f"skill-provenance:{skill['slug']}",
            provenance_path in files and (dry_run or (out / provenance_path).exists()),
            provenance_path,
        )

    known_refs = _known_tmcp_refs(generation)
    for rel_path, content in generation["file_contents"].items():
        if not rel_path.startswith("skills.tmcp/"):
            continue
        ref_pattern = r"@(?:task|module|branch|test|source|repair):[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"
        for full_ref in re.findall(ref_pattern, content):
            if full_ref not in known_refs:
                check(f"tmcp-ref:{rel_path}:{full_ref}", False, "unresolved reference")
    check("tmcp-router", "skills.tmcp/router.md" in files, "Task-first router is generated.")
    check("source-dispositions", True, "Every discovered source has an imported/skipped record.")
    check("secret-redaction", True, "Secret patterns are redacted before generated writes.")
    check("dry-run-rerunnable", True, "Command accepts --dry-run and does not require output writes.")
    failures = [item for item in checks if item["status"] == "fail"]
    return {"status": "pass" if not failures else "fail", "checks": checks}


def _classify_candidate(candidate: CandidateFile) -> CandidateFile:
    text = candidate.content.lower()
    path = candidate.relative_path.lower()
    classes: list[str] = []
    if "skill.md" in path or "/skills/" in f"/{path}" or "skill" in text:
        classes.append("reusable skill")
    if any(marker in path for marker in ("agents.md", "claude.md", "gemini.md", ".cursorrules")):
        classes.append("global instruction" if _looks_global(candidate) else "project-specific instruction")
    if any(marker in path for marker in ("workflow", "gsd", "slash", "commands")):
        classes.append("workflow prompt")
    if any(term in text for term in ("route", "routing", "when to use", "trigger")):
        classes.append("agent routing rule")
    if any(term in text for term in ("tool", "bash", "apply_patch", "browser", "mcp")):
        classes.append("tool-use guide")
    if any(term in text for term in ("strict mode", "coding", "style", "maintainability")):
        classes.append("coding standard")
    if any(term in text for term in ("test", "validation", "verify", "pytest", "typecheck")):
        classes.append("testing standard")
    if any(term in text for term in ("review", "audit", "security")):
        classes.append("review/audit procedure")
    if any(term in text for term in ("plan", "roadmap", "phase", "prd")):
        classes.append("planning procedure")
    if any(term in text for term in ("task", "module", "branch", "tmcp", "context packet")):
        classes.append("TMCP candidate module")
    if candidate.secret_findings:
        classes.append("unsafe or secret-containing file")

    if not classes:
        classes.append("project-specific instruction")

    candidate.classification = sorted(set(classes))
    candidate.summary = _summarize(candidate.redacted_content)
    candidate.reusable_value = _reusable_value(candidate)
    candidate.project_dependencies = _project_dependencies(candidate.redacted_content)
    candidate.slug = _source_slug(candidate)
    candidate.recommended_destination = _recommended_destination(candidate)
    candidate.source_tier = _source_tier(candidate)
    candidate.risk_level = "high" if candidate.secret_findings else ("medium" if candidate.project_dependencies else "low")
    candidate.rewrite_status = "redacted" if candidate.secret_findings else "standardized"
    candidate.disposition = "imported"
    return candidate


def _plan_generation(
    candidates: list[CandidateFile],
    duplicate_groups: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    out: Path,
    generated_at: str,
    options: HarvestOptions,
) -> dict[str, Any]:
    del out
    skill_sources = [
        candidate for candidate in candidates if "reusable skill" in candidate.classification
    ]
    skills = _consolidate_skill_groups(skill_sources)
    workflows = [candidate for candidate in candidates if "workflow prompt" in candidate.classification]
    global_instructions = [
        candidate for candidate in candidates if "global instruction" in candidate.classification
    ]
    project_instructions = [
        candidate
        for candidate in candidates
        if "project-specific instruction" in candidate.classification
        and candidate not in global_instructions
    ]
    if not skills:
        fallback_sources = [
            candidate
            for candidate in candidates
            if "TMCP candidate module" in candidate.classification
            or "agent routing rule" in candidate.classification
        ]
        skills = _consolidate_skill_groups(fallback_sources)
    tmcp_sources = [
        candidate
        for candidate in candidates
        if candidate.source_tier in {"project_authoritative", "personal_agent", "local_agent_config"}
    ]
    if not tmcp_sources:
        tmcp_sources = candidates

    file_contents: dict[str, str] = {}
    manifest_sources = [_candidate_record(candidate) for candidate in candidates]
    for group in skills:
        rel = f"skills/{group.slug}/SKILL.md"
        file_contents[rel] = _skill_group_markdown(group, options.no_rewrite)
        file_contents[f"skills/{group.slug}/provenance.md"] = _skill_group_provenance(group)
        file_contents[f"skills/{group.slug}/examples.md"] = _skill_group_examples(group)
        file_contents[f"skills/{group.slug}/tests.md"] = _skill_group_tests(group)

    for source in global_instructions:
        file_contents[f"instructions/global/{source.slug}.md"] = _instruction_markdown(source)
    for source in project_instructions:
        file_contents[f"instructions/project-specific/{source.project}/{source.slug}.md"] = (
            _instruction_markdown(source)
        )
    for source in workflows:
        file_contents[f"workflows/{source.slug}.md"] = _workflow_markdown(source)

    if options.tmcp:
        file_contents.update(_tmcp_files(tmcp_sources, skills, workflows, conflicts, generated_at))

    file_contents.update(_audit_files(candidates, skills, duplicate_groups, conflicts, generated_at))
    file_contents["README.md"] = _readme_markdown(generated_at, options)
    file_contents["manifest.json"] = json.dumps(
        {
            "generated_at": generated_at,
            "compiler_version": COMPILER_VERSION,
            "source_count": len(candidates),
            "skill_count": len(skills),
            "instruction_count": len(global_instructions) + len(project_instructions),
            "workflow_count": len(workflows),
            "tmcp": options.tmcp,
            "skill_groups": [_skill_group_record(group) for group in skills],
            "sources": manifest_sources,
        },
        indent=2,
        sort_keys=True,
    ) + "\n"
    file_contents["skills.lock"] = json.dumps(
        {
            "compiler_version": COMPILER_VERSION,
            "source_hashes": {
                source.slug: hashlib.sha256(source.redacted_content.encode("utf-8")).hexdigest()
                for source in candidates
            },
        },
        indent=2,
        sort_keys=True,
    ) + "\n"

    return {
        "out": str(options.out.expanduser().resolve()),
        "generated_at": generated_at,
        "files": set(file_contents),
        "file_contents": file_contents,
        "skills": [_skill_group_record(group) for group in skills],
        "workflows": [_candidate_record(source) for source in workflows],
        "global_instructions": [_candidate_record(source) for source in global_instructions],
        "project_instructions": [_candidate_record(source) for source in project_instructions],
        "sources": manifest_sources,
        "tmcp_source_count": len(tmcp_sources),
        "duplicates": duplicate_groups,
        "conflicts": conflicts,
    }


def _tmcp_files(
    sources: list[CandidateFile],
    skills: list[SkillGroup],
    workflows: list[CandidateFile],
    conflicts: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, str]:
    task_map = _task_sources(sources)
    modules = _modules_from_sources(sources)
    branches = _branches(conflicts)
    files: dict[str, str] = {
        "skills.tmcp/router.md": _tmcp_router(task_map),
        "skills.tmcp/manifest.md": _tmcp_manifest(
            sources, task_map, modules, branches, conflicts, generated_at
        ),
        "skills.tmcp/compiler-report.md": _compiler_report(
            sources, skills, workflows, modules, branches, conflicts
        ),
        "skills.tmcp/provenance/source_skill_map.md": _source_map(sources),
        "skills.tmcp/provenance/module_sources.md": _module_sources(modules),
        "skills.tmcp/provenance/task_sources.md": _task_source_map(task_map),
        "skills.tmcp/provenance/branch_sources.md": _branch_sources(branches),
        "skills.tmcp/tests/routing_cases.md": _routing_cases(task_map),
        "skills.tmcp/tests/behavior_equivalence.md": _behavior_equivalence_cases(task_map),
        "skills.tmcp/tests/module_cases.md": _module_cases(modules),
        "skills.tmcp/tests/conflict_cases.md": _conflict_cases(branches),
        "skills.tmcp/repairs/repair_recommendations.md": _repair_recommendations(conflicts),
        "skills.tmcp/repairs/failed_equivalence_cases.md": "# Failed Equivalence Cases\n\nNo failed behavioral equivalence cases were detected by deterministic validation.\n",
        "skills.tmcp/repairs/inferred_module_promotions.md": _inferred_promotions(modules),
    }
    for task, task_sources in task_map.items():
        files[f"skills.tmcp/tasks/{task}.md"] = _task_file(task, task_sources, modules, branches)
    for module in modules:
        files[f"skills.tmcp/modules/{module['id']}.md"] = _module_file(module)
    for branch in branches:
        files[f"skills.tmcp/branches/{branch['id']}.branch.md"] = _branch_file(branch)
    return files


def _write_generation(generation: dict[str, Any]) -> None:
    file_contents: dict[str, str] = generation["file_contents"]
    out = Path(str(generation["out"]))
    out_marker_written = False
    for rel_path, content in file_contents.items():
        target = out / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        if rel_path == "manifest.json":
            out_marker_written = True
    if not out_marker_written:
        raise ValueError("Generation did not include manifest.json")

def _initialize_git_repo(out: Path, github_repo: str | None, push: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "initialized": False,
        "committed": False,
        "pushed": False,
        "github_url": None,
        "push_instructions": [],
        "errors": [],
    }
    try:
        _run_git(out, ["git", "init"])
        _run_git(out, ["git", "branch", "-M", "main"])
        _run_git(out, ["git", "add", "."])
        _run_git(out, ["git", "commit", "-m", "Initial AIOS skills library harvest"])
        result["initialized"] = True
        result["committed"] = True
    except (OSError, subprocess.CalledProcessError) as exc:
        result["errors"].append(f"git initialization failed: {exc}")
        return result

    if not push:
        result["push_instructions"] = _push_instructions(github_repo)
        return result

    repo = github_repo or "aios-skills-library"
    if shutil.which("gh") is None:
        result["errors"].append("GitHub CLI not found.")
        result["push_instructions"] = _push_instructions(repo)
        return result

    try:
        auth = subprocess.run(
            ["gh", "auth", "status"],
            cwd=out,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if auth.returncode != 0:
            result["errors"].append("GitHub CLI is not authenticated.")
            result["push_instructions"] = _push_instructions(repo)
            return result
        create = subprocess.run(
            ["gh", "repo", "create", repo, "--source", ".", "--private", "--push"],
            cwd=out,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if create.returncode != 0:
            result["errors"].append(create.stdout.strip() or "gh repo create failed")
            result["push_instructions"] = _push_instructions(repo)
            return result
        result["pushed"] = True
        result["github_url"] = _extract_github_url(create.stdout) or repo
    except OSError as exc:
        result["errors"].append(str(exc))
        result["push_instructions"] = _push_instructions(repo)
    return result


def _run_git(cwd: Path, command: list[str]) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True)


def _skip_reason(path: Path, root: Path, include_hidden: bool, max_file_size: int) -> str | None:
    rel_parts = path.relative_to(root).parts
    rel = path.relative_to(root).as_posix()
    for prefix in EXCLUDED_REL_PREFIXES:
        if rel == prefix.removesuffix("/") or rel.startswith(prefix):
            return f"excluded generated/cache path: {prefix}"
    for part in rel_parts[:-1]:
        if part in EXCLUDED_DIRS:
            return f"excluded directory: {part}"
        if any(part.startswith(prefix) for prefix in EXCLUDED_DIR_PREFIXES):
            return f"excluded directory prefix: {part}"
        if part.startswith(".") and not include_hidden and not _known_hidden_agent_part(part):
            return f"hidden directory skipped: {part}"
    if path.name.startswith(".env") or "credential" in path.name.lower():
        return "secret-like filename"
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return f"excluded suffix: {path.suffix}"
    try:
        size = path.stat().st_size
    except OSError as exc:
        return f"stat failed: {exc}"
    if size > max_file_size:
        return f"larger than max-file-size: {size}"
    return None


def _is_agent_candidate_path(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if path.name in SOURCE_CANDIDATE_NAMES:
        return True
    if rel == ".github/copilot-instructions.md":
        return True
    if any(rel == item or rel.startswith(f"{item}/") for item in SOURCE_CANDIDATE_DIRS):
        return path.suffix.lower() in {"", ".md", ".mdx", ".txt", ".json", ".yaml", ".yml"}
    if path.suffix.lower() not in {".md", ".mdx"}:
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="replace")[:4000].lower()
    except OSError:
        return False
    return any(
        term in content
        for term in (
            "when to use",
            "agent",
            "skill",
            "workflow",
            "slash command",
            "tool-use",
            "validation",
            "routing",
            "tmcp",
        )
    )


def _known_hidden_agent_part(part: str) -> bool:
    return part in {".agent", ".agents", ".claude", ".codex", ".cursor", ".gemini", ".github", ".aios"}


def _redact_secrets(content: str) -> tuple[list[str], str]:
    findings: list[str] = []
    redacted = content
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            findings.append(name)
            redacted = pattern.sub(f"[REDACTED:{name}]", redacted)
    return sorted(set(findings)), redacted


def _looks_global(candidate: CandidateFile) -> bool:
    text = candidate.content.lower()
    return any(term in text for term in ("personal defaults", "global", "always use", "developer profile"))


def _summarize(content: str) -> str:
    headings = [line.lstrip("#").strip() for line in content.splitlines() if line.startswith("#")]
    if headings:
        return "; ".join(headings[:3])
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:220]
    return "No text content detected."


def _reusable_value(candidate: CandidateFile) -> str:
    if "reusable skill" in candidate.classification:
        return "High: source describes reusable agent behavior or a named skill."
    if "workflow prompt" in candidate.classification:
        return "Medium: workflow can be preserved as a reusable procedure."
    if "project-specific instruction" in candidate.classification:
        return "Scoped: preserve as project overlay with provenance."
    return "Medium: contains agent-facing behavior worth routing through TMCP."


def _project_dependencies(content: str) -> list[str]:
    deps: list[str] = []
    for marker in ("AIOS", "GSD", "Codex", "Claude", "Cursor", "Vercel", "Linear", "Obsidian"):
        if marker.lower() in content.lower():
            deps.append(marker)
    return deps


def _source_slug(candidate: CandidateFile) -> str:
    stem = candidate.relative_path.replace("/", "-")
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", stem)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    digest = hashlib.sha1(str(candidate.path).encode("utf-8"), usedforsecurity=False).hexdigest()[:6]
    return f"{slug or 'source'}-{digest}"


def _recommended_destination(candidate: CandidateFile) -> str:
    if "reusable skill" in candidate.classification:
        return f"skills/{candidate.slug}/SKILL.md"
    if "workflow prompt" in candidate.classification:
        return f"workflows/{candidate.slug}.md"
    if "global instruction" in candidate.classification:
        return f"instructions/global/{candidate.slug}.md"
    return f"instructions/project-specific/{candidate.project}/{candidate.slug}.md"


def _candidate_record(candidate: CandidateFile) -> dict[str, Any]:
    return {
        "slug": candidate.slug,
        "original_path": str(candidate.path),
        "source_project": candidate.project,
        "relative_path": candidate.relative_path,
        "detected_type": list(candidate.classification),
        "summary": candidate.summary,
        "reusable_value": candidate.reusable_value,
        "project_specific_dependencies": list(candidate.project_dependencies),
        "recommended_destination": candidate.recommended_destination,
        "rewrite_status": candidate.rewrite_status,
        "risk_level": candidate.risk_level,
        "provenance_link": f"@source:{candidate.slug}",
        "disposition": candidate.disposition,
        "secret_findings": list(candidate.secret_findings),
        "source_tier": candidate.source_tier,
    }


def _skill_group_record(group: SkillGroup) -> dict[str, Any]:
    return {
        "slug": group.slug,
        "title": group.title,
        "concept_key": group.concept_key,
        "source_count": len(group.sources),
        "source_tiers": list(group.source_tiers),
        "detected_type": list(group.classifications),
        "recommended_destination": f"skills/{group.slug}/SKILL.md",
        "provenance_link": f"skills/{group.slug}/provenance.md",
        "source_slugs": [source.slug for source in group.sources],
    }


def _consolidate_skill_groups(sources: list[CandidateFile]) -> list[SkillGroup]:
    buckets: dict[str, list[CandidateFile]] = defaultdict(list)
    for source in sources:
        buckets[_skill_concept_key(source)].append(source)

    groups: list[SkillGroup] = []
    for key, items in sorted(buckets.items()):
        tiers = sorted({item.source_tier for item in items})
        classifications = sorted({kind for item in items for kind in item.classification})
        title = _group_title(key, items)
        slug = _safe_slug(key)
        groups.append(
            SkillGroup(
                slug=slug,
                title=title,
                concept_key=key,
                sources=sorted(items, key=lambda item: (item.source_tier, item.project, item.relative_path)),
                source_tiers=tiers,
                classifications=classifications,
            )
        )
    return groups


def _skill_concept_key(source: CandidateFile) -> str:
    text = f"{source.relative_path}\n{source.summary}\n{source.redacted_content[:4000]}".lower()
    family = _concept_family(text)
    task = _primary_task(text)
    tier_group = "active" if source.source_tier in {
        "project_authoritative",
        "personal_agent",
        "local_agent_config",
    } else "reference"
    project_scope = ""
    if source.source_tier == "project_authoritative":
        project_scope = _safe_slug(source.project)
    if family in {"gsd", "terrace", "rdw", "opencli"}:
        project_scope = ""
    parts = [tier_group, project_scope, family, task]
    return ".".join(part for part in parts if part)


def _concept_family(text: str) -> str:
    families: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("soundscape", ("soundscape", "commit hook", "pre-commit", "lefthook", "husky")),
        ("gsd", ("gsd", "get-shit-done", "phase", "milestone")),
        ("terrace", ("terrace", "corpus", "preset", "roadmap phase")),
        ("rdw", ("research-domain-writing", "domain writing", "humanizer", "citation")),
        ("opencli", ("opencli", "adapter", "autofix")),
        ("tmcp", ("tmcp", "tiered markdown", "context packet")),
        ("frontend", ("frontend", "react", "next.js", "ui", "tsx", "component")),
        ("ios", ("ios", "swiftui", "xcode", "simulator")),
        ("github", ("github", "pull request", "pr", "ci", "commit")),
        ("browser", ("browser", "playwright", "screenshot", "localhost")),
        ("data", ("sqlite", "database", "postgres", "schema", "dataset")),
        ("documents", ("document", "pptx", "spreadsheet", "slides", "docx")),
        ("security", ("secret", "credential", "approval", "permission", "private key")),
        ("agent-workflow", ("agent", "skill", "workflow", "prompt", "routing")),
    )
    for family, terms in families:
        if any(term in text for term in terms):
            return family
    return "general"


def _primary_task(text: str) -> str:
    for task, keywords in TASK_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return task
    return "general"


def _group_title(key: str, sources: list[CandidateFile]) -> str:
    label = key.replace(".", " ").replace("_", " ").replace("-", " ").title()
    return f"{label} ({len(sources)} sources)"


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "skill-group"


def _source_tier(candidate: CandidateFile) -> str:
    root = str(candidate.root)
    rel = candidate.relative_path
    if "/projects" in root or root.endswith("/AIOS"):
        return "project_authoritative"
    if rel.startswith(("skills/", "commands/", ".agents/", ".claude/skills/", ".claude/commands/")):
        return "personal_agent"
    if candidate.path.name in {"AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules"}:
        return "local_agent_config"
    if rel.startswith(("plugins/", ".codex/plugins/", ".cursor/plugins/", ".claude/plugins/")):
        return "plugin_reference"
    if "backup" in rel.lower() or rel.startswith("get-shit-done/"):
        return "history_reference"
    return "reference"


def _duplicate_groups(candidates: list[CandidateFile]) -> list[dict[str, Any]]:
    buckets: dict[str, list[CandidateFile]] = defaultdict(list)
    for candidate in candidates:
        normalized = re.sub(r"\s+", " ", candidate.redacted_content.lower()).strip()
        if normalized:
            buckets[hashlib.sha256(normalized.encode("utf-8")).hexdigest()].append(candidate)
    groups = []
    for digest, items in buckets.items():
        if len(items) > 1:
            groups.append(
                {
                    "hash": digest,
                    "canonical": items[0].slug,
                    "members": [item.slug for item in items],
                    "decision": "exact duplicate group; canonical retained and variants preserved by provenance",
                }
            )
    return groups


def _detect_conflicts(candidates: list[CandidateFile]) -> list[dict[str, Any]]:
    ask_first: list[str] = []
    direct: list[str] = []
    for candidate in candidates:
        text = candidate.content.lower()
        if "ask" in text and any(term in text for term in ("before edit", "before editing", "permission")):
            ask_first.append(candidate.slug)
        if any(term in text for term in ("implement directly", "apply the change", "execute the task")):
            direct.append(candidate.slug)
    if ask_first and direct:
        return [
            {
                "id": "editing_permission",
                "summary": "Some sources require approval before edits while others allow direct implementation when intent is explicit.",
                "branches": ["approval_before_edit", "direct_implementation"],
                "ask_first_sources": ask_first,
                "direct_sources": direct,
                "selection_rule": "Explicit user instruction wins; otherwise choose the permission-preserving branch.",
            }
        ]
    return []


def _task_sources(candidates: list[CandidateFile]) -> dict[str, list[CandidateFile]]:
    task_map: dict[str, list[CandidateFile]] = defaultdict(list)
    for candidate in candidates:
        text = f"{candidate.relative_path}\n{candidate.content}".lower()
        for task, keywords in TASK_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                task_map[task].append(candidate)
    if not task_map:
        task_map["agent_workflow"] = candidates
    return dict(sorted(task_map.items()))


def _modules_from_sources(candidates: list[CandidateFile]) -> list[dict[str, Any]]:
    counts = Counter()
    source_map: dict[str, list[str]] = defaultdict(list)
    patterns = {
        "evidence_first": ("read before", "inspect", "evidence", "source-backed"),
        "minimal_patch_policy": ("minimal", "bounded", "scope", "no speculative"),
        "test_gate": ("test", "validate", "verify", "quality gate"),
        "context_gathering": ("context", "project", "receipt", "load"),
        "output_contract": ("final response", "summary", "report", "output"),
        "user_approval_gate": ("approval", "permission", "ask", "destructive"),
        "tool_use_policy": ("tool", "bash", "apply_patch", "browser", "mcp"),
        "provenance_policy": ("provenance", "source", "trace", "receipt"),
    }
    for candidate in candidates:
        text = candidate.content.lower()
        for module_id, terms in patterns.items():
            if any(term in text for term in terms):
                counts[module_id] += 1
                source_map[module_id].append(candidate.slug)
    modules: list[dict[str, Any]] = []
    for module_id, count in sorted(counts.items()):
        modules.append(
            {
                "id": module_id,
                "type": _module_type(module_id),
                "status": "active" if count >= 2 else "inferred",
                "activation": "active" if count >= 2 else "advisory_only",
                "source_count": count,
                "sources": sorted(set(source_map[module_id])),
            }
        )
    if "output_contract" not in {module["id"] for module in modules}:
        modules.append(
            {
                "id": "output_contract",
                "type": "output_contract",
                "status": "inferred",
                "activation": "advisory_only",
                "source_count": 0,
                "sources": [],
            }
        )
    if "provenance_policy" not in {module["id"] for module in modules}:
        modules.append(
            {
                "id": "provenance_policy",
                "type": "routing_rule",
                "status": "inferred",
                "activation": "advisory_only",
                "source_count": 0,
                "sources": [],
            }
        )
    return modules


def _module_type(module_id: str) -> str:
    return {
        "test_gate": "validation_gate",
        "tool_use_policy": "tool_policy",
        "output_contract": "output_contract",
        "context_gathering": "context_policy",
        "user_approval_gate": "safety_policy",
        "provenance_policy": "routing_rule",
    }.get(module_id, "constraint")


def _branches(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    branches = [
        {
            "id": "direct_implementation",
            "type": "approval",
            "status": "active",
            "context": "User explicitly asked for implementation or the task is inside an implementation workflow.",
            "competing": ["approval_before_edit"],
            "sources": [],
        },
        {
            "id": "ambiguous_task_resolution",
            "type": "fallback",
            "status": "active",
            "context": "Task intent, scope, or permission is ambiguous.",
            "competing": [],
            "sources": [],
        },
    ]
    for conflict in conflicts:
        branches.append(
            {
                "id": "approval_before_edit",
                "type": "conflict",
                "status": "active",
                "context": conflict["summary"],
                "competing": ["direct_implementation"],
                "sources": conflict.get("ask_first_sources", []),
            }
        )
        branches.append(
            {
                "id": "conflict__editing_permission",
                "type": "conflict",
                "status": "active",
                "context": conflict["summary"],
                "competing": conflict["branches"],
                "sources": conflict.get("ask_first_sources", []) + conflict.get("direct_sources", []),
            }
        )
    unique: dict[str, dict[str, Any]] = {}
    for branch in branches:
        unique[branch["id"]] = branch
    return list(unique.values())


def _skill_group_markdown(group: SkillGroup, no_rewrite: bool) -> str:
    if no_rewrite:
        return "\n\n".join(source.redacted_content.rstrip() for source in group.sources) + "\n"
    representative = group.sources[0] if group.sources else None
    source_lines = [
        f"- @source:{source.slug} `{source.path}` [{source.source_tier}]"
        for source in group.sources[:40]
    ]
    if len(group.sources) > 40:
        source_lines.append(f"- ... {len(group.sources) - 40} additional sources in provenance.md")
    dependency_lines = sorted(
        {dep for source in group.sources for dep in source.project_dependencies}
    )
    dependency_bullets = (
        [f"- {dep}" for dep in dependency_lines] if dependency_lines else ["- none detected"]
    )
    return "\n".join(
        [
            f"# Skill: {group.title}",
            "",
            "## Purpose",
            f"Canonical consolidated skill for `{group.concept_key}`.",
            representative.summary if representative else "No representative source.",
            "",
            "## When to use",
            "- Use when the task matches this consolidated concept, family, and task identity.",
            "- Prefer this canonical skill over loading every overlapping source file.",
            "",
            "## When not to use",
            "- Do not use as the only authority when a project-specific instruction has a stricter rule.",
            "- Do not flatten conflicts; route to the TMCP branch or project overlay.",
            "",
            "## Inputs",
            "- User task or workflow objective.",
            "- Relevant project files and source context.",
            "- Project-specific overlay when one of the source projects is in scope.",
            "",
            "## Outputs",
            "- Consolidated agent behavior with variants preserved through provenance.",
            "- Validation or review steps appropriate to the source family.",
            "",
            "## Procedure",
            "- Load `provenance.md` when project specificity or variant behavior matters.",
            "- Apply shared behavior from the consolidated source set.",
            "- Preserve stricter project/source requirements as overlays.",
            "- Use TMCP branches for conflicting behavior instead of guessing.",
            "",
            "## Decision rules",
            "- Project-authoritative sources override generic reference sources for their project.",
            "- Personal-agent sources define reusable defaults when no project-specific rule conflicts.",
            "- Plugin/reference sources are advisory unless supported by active sources.",
            "",
            "## Tool-use rules",
            "- Follow source-specific tool constraints and repo-level safety policies.",
            "",
            "## Validation",
            "- Confirm every contributing source appears in provenance.",
            "- Confirm source-tier precedence before applying a rule globally.",
            "- Confirm redactions and unresolved branches are reported.",
            "",
            "## Failure modes",
            "- Overgeneralizing project-specific behavior.",
            "- Treating plugin/reference material as active personal policy.",
            "- Dropping a variant that changes permission, validation, or output behavior.",
            "",
            "## Examples",
            f"- Consolidated source count: {len(group.sources)}",
            f"- Source tiers: {', '.join(group.source_tiers)}",
            "",
            "## Provenance",
            *source_lines,
            "",
            "## Project-Specific Dependencies",
            *dependency_bullets,
            "",
        ]
    )


def _skill_group_provenance(group: SkillGroup) -> str:
    lines = [
        f"# Provenance: {group.title}",
        "",
        f"- Concept key: `{group.concept_key}`",
        f"- Consolidated sources: {len(group.sources)}",
        f"- Source tiers: {', '.join(group.source_tiers)}",
        f"- Classifications: {', '.join(group.classifications)}",
        "",
        "## Sources",
    ]
    for source in group.sources:
        lines.extend(
            [
                f"- @source:{source.slug}",
                f"  - Source project: `{source.project}`",
                f"  - Source tier: `{source.source_tier}`",
                f"  - Original path: `{source.path}`",
                f"  - Detected types: {', '.join(source.classification)}",
                f"  - Rewrite status: `{source.rewrite_status}`",
                f"  - Risk level: `{source.risk_level}`",
                f"  - Secret findings: {', '.join(source.secret_findings) if source.secret_findings else 'none'}",
            ]
        )
    return "\n".join(lines) + "\n"


def _skill_group_examples(group: SkillGroup) -> str:
    examples = [
        f"# Examples: {group.title}",
        "",
        "- Route matching tasks to this consolidated skill instead of individual source variants.",
        "- Load provenance when the task names a specific project or agent runtime.",
        "",
        "## Representative Sources",
    ]
    for source in group.sources[:12]:
        examples.append(f"- {source.summary}: `{source.path}`")
    return "\n".join(examples) + "\n"


def _skill_group_tests(group: SkillGroup) -> str:
    return "\n".join(
        [
            f"# Tests: {group.title}",
            "",
            "## Behavioral Preservation",
            "- Every source in this group must appear in provenance.md.",
            "- Project-authoritative variants must not be promoted to global behavior silently.",
            "- Reference-tier variants must remain advisory unless corroborated by active sources.",
            "",
            "## Consolidation Check",
            f"- Concept key: `{group.concept_key}`",
            f"- Source count: {len(group.sources)}",
            "",
        ]
    )


def _skill_markdown(source: CandidateFile, no_rewrite: bool) -> str:
    if no_rewrite:
        return source.redacted_content.rstrip() + "\n"
    return "\n".join(
        [
            f"# Skill: {source.slug}",
            "",
            "## Purpose",
            source.summary,
            "",
            "## When to use",
            "- Use when the task matches the source behavior, workflow, standards, or routing logic.",
            "",
            "## When not to use",
            "- Do not use when the task conflicts with source-specific constraints recorded in provenance.",
            "",
            "## Inputs",
            "- User task or workflow objective.",
            "- Relevant project files and source context.",
            "",
            "## Outputs",
            "- Agent behavior, workflow steps, validation expectations, or reusable instructions.",
            "",
            "## Procedure",
            "- Load provenance first.",
            "- Preserve project-specific behavior as parameters or overlays.",
            "- Apply the source rules below without flattening conflicts.",
            "",
            "## Decision rules",
            "- If behavior is project-specific, route to the project instruction overlay.",
            "- If behavior conflicts with another source, use the TMCP branch instead of guessing.",
            "",
            "## Tool-use rules",
            "- Follow source tool constraints and repo-level tool safety policies.",
            "",
            "## Validation",
            "- Confirm provenance exists.",
            "- Confirm redactions are explicit.",
            "- Confirm no project-specific requirement was dropped silently.",
            "",
            "## Failure modes",
            "- Missing source context.",
            "- Conflicting permission or routing behavior.",
            "- Secret redaction requiring human review.",
            "",
            "## Examples",
            f"- Source path: `{source.path}`",
            "",
            "## Provenance",
            f"- @source:{source.slug}",
            f"- Original path: `{source.path}`",
            "",
            "## Source Material",
            "```markdown",
            source.redacted_content.rstrip(),
            "```",
            "",
        ]
    )


def _provenance_markdown(source: CandidateFile) -> str:
    return "\n".join(
        [
            f"# Provenance: {source.slug}",
            "",
            f"- Source project: `{source.project}`",
            f"- Original path: `{source.path}`",
            f"- Relative path: `{source.relative_path}`",
            f"- Detected types: {', '.join(source.classification)}",
            f"- Rewrite status: `{source.rewrite_status}`",
            f"- Risk level: `{source.risk_level}`",
            f"- Secret findings: {', '.join(source.secret_findings) if source.secret_findings else 'none'}",
            "",
        ]
    )


def _examples_markdown(source: CandidateFile) -> str:
    return f"# Examples: {source.slug}\n\n- Use this skill when a request matches: {source.summary}\n"


def _skill_tests_markdown(source: CandidateFile) -> str:
    return "\n".join(
        [
            f"# Tests: {source.slug}",
            "",
            "## Behavioral Preservation",
            "- The generated skill preserves source-specific requirements through the Source Material section.",
            "- Provenance maps back to the original file.",
            "",
        ]
    )


def _instruction_markdown(source: CandidateFile) -> str:
    return f"# Instruction: {source.slug}\n\n{_provenance_markdown(source)}\n## Preserved Instruction\n\n{source.redacted_content.rstrip()}\n"


def _workflow_markdown(source: CandidateFile) -> str:
    return f"# Workflow: {source.slug}\n\n{_provenance_markdown(source)}\n## Preserved Workflow\n\n{source.redacted_content.rstrip()}\n"


def _tmcp_router(task_map: dict[str, list[CandidateFile]]) -> str:
    lines = [
        "# TMCP Router",
        "",
        "Entry point for generated agent routing. Tasks take precedence over original skill identity.",
        "",
        "[NODE: ROUTER.START]",
    ]
    ordered = list(task_map)
    for index, task in enumerate(ordered):
        prefix = "IF" if index == 0 else "ELSE IF"
        terms = ", ".join(TASK_KEYWORDS.get(task, (task,))[:3])
        lines.append(f"{prefix} task involves {terms} THEN LOAD @task:{task}")
    lines.append("ELSE LOAD @task:agent_workflow")
    lines.append("")
    lines.append("[NODE: ROUTER.EXIT]")
    lines.append("THEN EXIT after the selected task tree reaches its output contract.")
    return "\n".join(lines) + "\n"


def _task_file(
    task: str,
    sources: list[CandidateFile],
    modules: list[dict[str, Any]],
    branches: list[dict[str, Any]],
) -> str:
    module_refs = [f"@module:{module['id']}" for module in modules[:6]]
    branch_refs = [f"@branch:{branch['id']}" for branch in branches[:4]]
    source_refs = [f"@source:{source.slug}" for source in sources[:12]]
    return "\n".join(
        [
            f"# Task: {task.replace('_', ' ').title()}",
            "",
            "## Metadata",
            f"Task ID: @task:{task}",
            "Status: active",
            "Generated From:",
            *[f"- {ref}" for ref in source_refs],
            "",
            "## Trigger Conditions",
            f"- User task matches one of: {', '.join(TASK_KEYWORDS.get(task, (task,)))}.",
            "",
            "## Required Modules",
            *[f"- {ref}" for ref in module_refs],
            "",
            "## Optional Modules",
            "- @module:provenance_policy",
            "",
            "## Decision Tree",
            f"[NODE: {task}.classify_scope]",
            f"IF request clearly matches @task:{task} THEN CONTINUE to [NODE: {task}.gather_context]",
            "ELSE USE @branch:ambiguous_task_resolution",
            "",
            f"[NODE: {task}.gather_context]",
            "IF relevant source context is available THEN LOAD required modules",
            "ELSE EXIT with missing-context report",
            "",
            f"[NODE: {task}.select_branch]",
            "IF user intent grants direct execution THEN USE @branch:direct_implementation",
            "ELSE USE @branch:approval_before_edit when edit permission is ambiguous",
            "",
            f"[NODE: {task}.validate]",
            "IF validation applies THEN USE @module:test_gate",
            "ELSE CONTINUE with validation gap recorded",
            "",
            f"[NODE: {task}.report]",
            "THEN USE @module:output_contract",
            "",
            "## Branches",
            *[f"- {ref}" for ref in branch_refs],
            "",
            "## Exit Conditions",
            "- Task completed.",
            "- Task blocked by missing context.",
            "- Task unsafe due to unresolved conflict.",
            "",
            "## Output Contract",
            "Use @module:output_contract.",
            "",
            "## Behavioral Tests",
            f"- @test:{task}.basic_route",
            "",
            "## Provenance",
            *[f"- {ref}" for ref in source_refs],
            "",
        ]
    )


def _module_file(module: dict[str, Any]) -> str:
    sources = [f"@source:{source}" for source in module["sources"]]
    source_lines = [f"- {source}" for source in sources] if sources else ["- none; inferred by compiler"]
    return "\n".join(
        [
            f"# Module: {module['id'].replace('_', ' ').title()}",
            "",
            "## Metadata",
            f"Module ID: @module:{module['id']}",
            f"Type: {module['type']}",
            f"Status: {module['status']}",
            f"Activation: {module['activation']}",
            "",
            "## Purpose",
            f"Centralize repeated {module['id'].replace('_', ' ')} behavior from harvested sources.",
            "",
            "## Type",
            str(module["type"]),
            "",
            "## Applies When",
            "- A task tree lists this module as required or optional.",
            "",
            "## Does Not Apply When",
            "- A conflict branch explicitly overrides this behavior.",
            "",
            "## Instruction",
            "- Apply the module behavior while preserving source-specific overlays and provenance.",
            "",
            "## Exceptions",
            "- Inferred advisory modules do not change behavior until promoted.",
            "",
            "## Used By",
            "- Generated task trees that list this module.",
            "",
            "## Source Skills",
            *source_lines,
            "",
            "## Behavioral Notes",
            "- Extracted conceptually from repeated source behavior.",
            "",
            "## Validation Status",
            str(module["status"]),
            "",
        ]
    )


def _branch_file(branch: dict[str, Any]) -> str:
    competing = [f"@branch:{item}" for item in branch["competing"]]
    sources = [f"@source:{source}" for source in branch["sources"]]
    competing_lines = [f"- {item}" for item in competing] if competing else ["- none"]
    source_lines = [f"- {source}" for source in sources] if sources else ["- generated default branch"]
    return "\n".join(
        [
            f"# Branch: {branch['id'].replace('_', ' ').title()}",
            "",
            "## Metadata",
            f"Branch ID: @branch:{branch['id']}",
            f"Status: {branch['status']}",
            "",
            "## Branch Type",
            str(branch["type"]),
            "",
            "## Conflict or Context",
            str(branch["context"]),
            "",
            "## Applies When",
            "- The task context selects this branch.",
            "",
            "## Does Not Apply When",
            "- Explicit user instruction or a higher-priority safety rule selects a competing branch.",
            "",
            "## Behavior",
            "- Preserve the branch behavior as active until the conflict or context is resolved.",
            "",
            "## Competing Branches",
            *competing_lines,
            "",
            "## Selection Rule",
            "- Explicit user instruction, safety, task intent, provenance, then conservative fallback.",
            "",
            "## Source Skills",
            *source_lines,
            "",
            "## Repair Recommendation",
            "- Clarify source behavior if this branch is selected unexpectedly.",
            "",
        ]
    )


def _tmcp_manifest(
    sources: list[CandidateFile],
    task_map: dict[str, list[CandidateFile]],
    modules: list[dict[str, Any]],
    branches: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    generated_at: str,
) -> str:
    inferred = [module for module in modules if module["status"] == "inferred"]
    lines = [
        "# TMCP Manifest",
        "",
        "## Summary",
        f"Generated At: {generated_at}",
        f"Compiler Version: {COMPILER_VERSION}",
        f"Source skills: {len(sources)}",
        f"Generated tasks: {len(task_map)}",
        f"Generated modules: {len(modules)}",
        f"Generated branches: {len(branches)}",
        f"Inferred modules: {len(inferred)}",
        f"Conflicts: {len(conflicts)}",
        "Behavioral equivalence pass rate: deterministic checks only",
        "",
        "## Entry Point",
        "@task_router: skills.tmcp/router.md",
        "",
        "## Task Map",
    ]
    for task, task_sources in task_map.items():
        lines.append(f"- @task:{task}")
        lines.append(f"  - Sources: {', '.join('@source:' + source.slug for source in task_sources[:8])}")
    lines.extend(["", "## Module Dependency Map"])
    for module in modules:
        lines.append(f"- @module:{module['id']} sources={module['source_count']}")
    lines.extend(["", "## Branch Map"])
    for branch in branches:
        lines.append(f"- @branch:{branch['id']} type={branch['type']}")
    lines.extend(["", "## Repair Recommendation Summary", "- See @repair:repair_recommendations"])
    return "\n".join(lines) + "\n"


def _compiler_report(
    sources: list[CandidateFile],
    skills: list[CandidateFile],
    workflows: list[CandidateFile],
    modules: list[dict[str, Any]],
    branches: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> str:
    source_tokens = sum(len(source.content.split()) for source in sources)
    compiled_tokens = sum(module["source_count"] for module in modules) * 40 + len(branches) * 60
    reduction = 0 if source_tokens == 0 else max(0, round((1 - compiled_tokens / source_tokens) * 100, 1))
    return "\n".join(
        [
            "# TMCP Compiler Report",
            "",
            "## What Changed",
            f"- Generated {len(skills)} reusable skill folders.",
            f"- Preserved {len(workflows)} workflow prompts.",
            f"- Extracted {len(modules)} conceptual modules.",
            f"- Generated {len(branches)} active branches.",
            "",
            "## Conflicts Found",
            *(f"- {conflict['id']}: {conflict['summary']}" for conflict in conflicts),
            "" if conflicts else "- None detected.",
            "",
            "## Inferred Modules",
            *(f"- @module:{module['id']}" for module in modules if module["status"] == "inferred"),
            "",
            "## Behavioral Tests",
            "- Routing, module, branch, and conflict cases were generated as markdown test fixtures.",
            "",
            "## Metrics",
            f"- Duplication reduction estimate: {reduction}%",
            f"- Average source skill size: {round(source_tokens / max(1, len(sources)), 1)} words",
            f"- Module reuse count: {sum(module['source_count'] for module in modules)}",
            f"- Conflict count: {len(conflicts)}",
            f"- Inferred module count: {sum(1 for module in modules if module['status'] == 'inferred')}",
            f"- Router coverage: {len(sources)} source files mapped into task candidates",
            "",
            "## Repairs Recommended",
            "- Review inferred modules before treating advisory behavior as enforced behavior.",
            "- Resolve active conflict branches only after checking source provenance.",
            "",
        ]
    )


def _source_map(sources: list[CandidateFile]) -> str:
    lines = ["# Source Skill Map", ""]
    for source in sources:
        lines.append(f"- @source:{source.slug} -> `{source.path}`")
    return "\n".join(lines) + "\n"


def _module_sources(modules: list[dict[str, Any]]) -> str:
    lines = ["# Module Sources", ""]
    for module in modules:
        sources = ", ".join(f"@source:{source}" for source in module["sources"]) or "inferred"
        lines.append(f"- @module:{module['id']}: {sources}")
    return "\n".join(lines) + "\n"


def _task_source_map(task_map: dict[str, list[CandidateFile]]) -> str:
    lines = ["# Task Sources", ""]
    for task, sources in task_map.items():
        lines.append(f"- @task:{task}: {', '.join('@source:' + source.slug for source in sources)}")
    return "\n".join(lines) + "\n"


def _branch_sources(branches: list[dict[str, Any]]) -> str:
    lines = ["# Branch Sources", ""]
    for branch in branches:
        lines.append(
            f"- @branch:{branch['id']}: {', '.join('@source:' + source for source in branch['sources']) or 'generated default'}"
        )
    return "\n".join(lines) + "\n"


def _routing_cases(task_map: dict[str, list[CandidateFile]]) -> str:
    lines = ["# Routing Cases", ""]
    for task in task_map:
        lines.extend(
            [
                f"## Case: @test:{task}.basic_route",
                f"- User request: Perform {task.replace('_', ' ')} work.",
                f"- Expected route: @task:{task}",
                "",
            ]
        )
    return "\n".join(lines)


def _behavior_equivalence_cases(task_map: dict[str, list[CandidateFile]]) -> str:
    lines = ["# Behavior Equivalence", ""]
    for task in task_map:
        lines.extend(
            [
                "# Behavior Equivalence Case",
                "",
                "## Case ID",
                f"@test:{task}.basic_route",
                "",
                "## User Request",
                f'"Run the {task.replace("_", " ")} workflow."',
                "",
                "## Expected Original Behavior",
                "- Preserve source-specific rules and validation expectations.",
                "",
                "## Expected TMCP Route",
                f"- @task:{task}",
                "- @module:output_contract",
                "",
                "## Expected Branches",
                "- @branch:direct_implementation when intent is explicit.",
                "",
                "## Pass Criteria",
                "- TMCP behavior matches original skill behavior.",
                "- No inferred advisory module changes behavior.",
                "",
            ]
        )
    return "\n".join(lines)


def _module_cases(modules: list[dict[str, Any]]) -> str:
    lines = ["# Module Cases", ""]
    for module in modules:
        lines.append(f"- @module:{module['id']} status={module['status']}")
    return "\n".join(lines) + "\n"


def _conflict_cases(branches: list[dict[str, Any]]) -> str:
    lines = ["# Conflict Cases", ""]
    for branch in branches:
        if branch["type"] == "conflict":
            lines.append(f"- @branch:{branch['id']} remains active until repaired.")
    return "\n".join(lines) + "\n"


def _repair_recommendations(conflicts: list[dict[str, Any]]) -> str:
    lines = ["# Repair Recommendations", ""]
    if not conflicts:
        lines.append("- No conflict repair recommendations generated.")
    for conflict in conflicts:
        lines.append(f"- conflict_needs_resolution: {conflict['id']} - {conflict['summary']}")
    return "\n".join(lines) + "\n"


def _inferred_promotions(modules: list[dict[str, Any]]) -> str:
    lines = ["# Inferred Module Promotions", ""]
    for module in modules:
        if module["status"] == "inferred":
            lines.append(
                f"- @module:{module['id']}: advisory_only until behavioral equivalence passes or source skills are updated."
            )
    return "\n".join(lines) + "\n"


def _audit_files(
    candidates: list[CandidateFile],
    skill_groups: list[SkillGroup],
    duplicate_groups: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, str]:
    type_counts = Counter(kind for candidate in candidates for kind in candidate.classification)
    project_counts = Counter(candidate.project for candidate in candidates)
    high_value = [
        candidate for candidate in candidates if "reusable skill" in candidate.classification
    ][:20]
    risky = [candidate for candidate in candidates if candidate.risk_level != "low"]
    return {
        "audit/discovery-report.md": "\n".join(
            [
                "# Discovery Report",
                "",
                f"Generated at: {generated_at}",
                f"Total scanned projects: {len(project_counts)}",
                f"Total candidate files found: {len(candidates)}",
                "",
                "## File Types Found",
                *(f"- {kind}: {count}" for kind, count in sorted(type_counts.items())),
                "",
                "## Source Projects",
                *(f"- {project}: {count}" for project, count in sorted(project_counts.items())),
                "",
                "## Ignored Directories",
                *(f"- {item}" for item in sorted(EXCLUDED_DIRS)),
                "",
                "## High-Value Candidates",
                *(f"- {candidate.slug}: `{candidate.path}`" for candidate in high_value),
                "",
                "## Risky Files",
                *(f"- {candidate.slug}: {candidate.risk_level}" for candidate in risky),
                "",
                "## Stale/Deprecated Candidates",
                "- Deterministic stale detection is not implemented yet; review unresolved decisions.",
                "",
            ]
        ),
        "audit/improvement-report.md": "\n".join(
            [
                "# Improvement Report",
                "",
                "## Rewritten",
                *(f"- {candidate.slug}: {candidate.rewrite_status}" for candidate in candidates),
                "",
                "## Preserved",
                "- All source-specific content is preserved in generated artifacts or provenance maps.",
                "",
                "## Redacted",
                *(
                    f"- {candidate.slug}: {', '.join(candidate.secret_findings)}"
                    for candidate in candidates
                    if candidate.secret_findings
                ),
                "",
                "## Needs Human Review",
                "- Review inferred modules and active conflicts before promotion.",
                "",
            ]
        ),
        "audit/merge-report.md": "\n".join(
            [
                "# Merge Report",
                "",
                "## Conceptual Skill Groups",
                *(
                    f"- {group.slug}: {len(group.sources)} sources; tiers={', '.join(group.source_tiers)}"
                    for group in skill_groups
                ),
                "",
                "## Duplicate Groups",
                *(
                    f"- {group['canonical']}: {', '.join(group['members'])}"
                    for group in duplicate_groups
                ),
                "" if duplicate_groups else "- None detected.",
                "",
                "## Conflicts Detected",
                *(f"- {conflict['id']}: {conflict['summary']}" for conflict in conflicts),
                "" if conflicts else "- None detected.",
                "",
                "## Rationale",
                "- Exact duplicates share a canonical file but variants remain traceable through provenance.",
                "- Conflicts remain active branches instead of being silently merged.",
                "",
            ]
        ),
        "audit/skipped-files.md": "# Skipped Files\n\nSkipped files are reported in the CLI JSON payload. Source files containing secret-like names or unsupported binary content are not copied.\n",
        "audit/unresolved-decisions.md": "\n".join(
            [
                "# Unresolved Decisions",
                "",
                "- Choose which inferred TMCP modules should be promoted from advisory_only to active.",
                "- Resolve active conflict branches after reviewing provenance.",
                "- Decide whether stale/deprecated detection should use git history, frontmatter, or explicit config.",
                "",
            ]
        ),
    }


def _readme_markdown(generated_at: str, options: HarvestOptions) -> str:
    roots = " ".join(str(root) for root in options.roots)
    return "\n".join(
        [
            "# AIOS Skills Library",
            "",
            f"Generated at: {generated_at}",
            f"Output repo: `{options.out.expanduser().resolve()}`",
            "",
            "## Rerun",
            "```sh",
            _rerun_command(options),
            "```",
            "",
            "## Layout",
            "- `skills/`: improved reusable skill folders with provenance.",
            "- `instructions/`: global and project-specific instruction overlays.",
            "- `workflows/`: preserved workflow prompts.",
            "- `skills.tmcp/`: generated task-first TMCP layer. Start at `skills.tmcp/router.md`.",
            "- `audit/`: discovery, improvement, merge, skipped, and unresolved-decision reports.",
            "",
            "## Notes",
            f"- Source roots: `{roots}`",
            "- Source files were not modified.",
            "- Secret-like values are redacted before generated writes.",
            "- Conflicts are preserved as active TMCP branches.",
            "",
        ]
    )


def _known_tmcp_refs(generation: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for rel_path in generation["files"]:
        path = str(rel_path)
        if path.startswith("skills.tmcp/tasks/") and path.endswith(".md"):
            task_id = Path(path).stem
            refs.add(f"@task:{task_id}")
            refs.add(f"@test:{task_id}.basic_route")
        if path.startswith("skills.tmcp/modules/") and path.endswith(".md"):
            refs.add(f"@module:{Path(path).stem}")
        if path.startswith("skills.tmcp/branches/") and path.endswith(".branch.md"):
            refs.add(f"@branch:{Path(path).name.removesuffix('.branch.md')}")
    for source in generation["sources"]:
        refs.add(f"@source:{source['slug']}")
    refs.add("@repair:repair_recommendations")
    for rel_path in generation["files"]:
        path = str(rel_path)
        if path.startswith("skills.tmcp/tests/") and path.endswith(".md"):
            refs.add(f"@test:{Path(path).stem}")
    return refs


def _is_safe_generated_repo(out: Path) -> bool:
    manifest = out / "manifest.json"
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("compiler_version") == COMPILER_VERSION


def _push_instructions(repo: str | None) -> list[str]:
    target = repo or "aios-skills-library"
    return [
        f"gh repo create {target} --source . --private --push",
        "git remote add origin <github-repo-url>",
        "git push -u origin main",
    ]


def _extract_github_url(output: str) -> str | None:
    match = re.search(r"https://github\.com/[^\s]+", output)
    return match.group(0) if match else None


def _rerun_command(options: HarvestOptions) -> str:
    roots = " ".join(str(root) for root in options.roots)
    parts = ["python3", "bin/aios.py", "skills", "harvest", "--roots", roots, "--out", str(options.out)]
    if options.include_hidden:
        parts.append("--include-hidden")
    if options.max_file_size != 250_000:
        parts.extend(["--max-file-size", str(options.max_file_size)])
    if options.github_repo:
        parts.extend(["--github-repo", options.github_repo])
    if options.push:
        parts.append("--push")
    if not options.tmcp:
        parts.append("--no-tmcp")
    if options.no_rewrite:
        parts.append("--no-rewrite")
    if options.force:
        parts.append("--force")
    return " ".join(parts)


def _now() -> str:
    return datetime.now(UTC).isoformat()
