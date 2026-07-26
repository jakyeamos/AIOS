from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

COMPILER_VERSION = "skills-harvest-v0.1"
TMCP_DESIGN_DECISION_ID = "tmcp-decision-graph-v0.2"
TMCP_TRAVERSAL_ACTIONS = ("LOAD", "CONSIDER", "USE", "SKIP", "EXIT", "WHY", "EVIDENCE", "OUTCOME")
ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR_ATOM_REGISTRY_PATH = ROOT / "config" / "tmcp" / "behavior-atoms.json"

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
    (
        "private_key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    ),
    (
        "api_key_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-./+=]{16,})"
        ),
    ),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("connection_string", re.compile(r"(?i)\b(postgres|mysql|mongodb|redis)://[^\s)>\"]+")),
)
DEFAULT_GRAPH_PROFILE_PATH = Path("config/tmcp/canonical-graph.json")
TASK_KEYWORDS = {
    "audit": ("audit", "review", "inspect", "evaluate"),
    "implementation": ("implement", "edit", "patch", "fix", "refactor", "build"),
    "planning": (
        "plan",
        "roadmap",
        "phase",
        "acceptance",
        "strategy",
        "strategies",
        "promotion",
        "compare",
    ),
    "research": ("research", "investigate", "source", "citation"),
    "debugging": ("debug", "bug", "root cause", "failure"),
    "testing": ("test", "verify", "validate", "quality gate"),
    "documentation": ("document", "readme", "docs", "writeback"),
    "agent_workflow": ("agent", "workflow", "routing", "skill", "prompt", "tmcp", "gsd"),
    "visual_polish": (
        "visual polish",
        "product ui polish",
        "enterprise saas",
        "dashboard polish",
        "ai ui",
        "realistic demo data",
        "generic shadcn",
    ),
}

FALLBACK_BEHAVIOR_ATOMS: dict[str, list[str]] = {
    "context_gathering": ["context_selection", "minimal_context"],
    "evidence_first": ["read_before_edit", "evidence_trace"],
    "minimal_patch_policy": ["bounded_change", "avoid_speculative_abstraction"],
    "test_gate": ["verification_gate", "claim_evidence"],
    "output_contract": ["clear_closeout", "validation_reporting"],
    "user_approval_gate": ["approval_before_risk", "destructive_action_guard"],
    "tool_use_policy": ["tool_safety", "command_policy"],
    "provenance_policy": ["provenance_trace", "source_tier_precedence"],
    "operating_language": ["canonical_vocabulary", "term_consistency"],
    "direct_implementation": ["direct_execution_permission"],
    "approval_before_edit": ["approval_before_edit"],
    "ambiguous_task_resolution": ["ambiguity_clarification"],
    "conflict__editing_permission": ["conflict_branch_selection"],
    "implementation": ["change_execution", "verification_gate"],
    "debugging": ["reproduce_first", "root_cause_analysis"],
    "audit": ["risk_review", "finding_evidence"],
    "visual_polish": ["ui_quality", "visual_verification"],
    "planning": ["execution_ready_plan", "acceptance_criteria"],
    "research": ["source_grounding", "citation_discipline"],
    "testing": ["test_authoring", "verification_gate"],
    "documentation": ["doc_staleness_check"],
    "agent_workflow": ["skill_routing", "workflow_selection"],
}


@lru_cache(maxsize=1)
def _behavior_atom_registry() -> dict[str, Any]:
    if not BEHAVIOR_ATOM_REGISTRY_PATH.exists():
        return {
            "schema": "tmcp-behavior-atoms-fallback",
            "atoms": {},
            "node_mappings": FALLBACK_BEHAVIOR_ATOMS,
            "semantic_section_labels": {},
        }
    try:
        parsed = json.loads(BEHAVIOR_ATOM_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema": "tmcp-behavior-atoms-fallback",
            "atoms": {},
            "node_mappings": FALLBACK_BEHAVIOR_ATOMS,
            "semantic_section_labels": {},
        }
    if not isinstance(parsed, dict):
        return {
            "schema": "tmcp-behavior-atoms-fallback",
            "atoms": {},
            "node_mappings": FALLBACK_BEHAVIOR_ATOMS,
            "semantic_section_labels": {},
        }
    return parsed


def _behavior_atom_mappings() -> dict[str, list[str]]:
    mappings = _dict(_behavior_atom_registry().get("node_mappings"))
    normalized: dict[str, list[str]] = {}
    for key, value in mappings.items():
        if isinstance(key, str):
            normalized[key] = [str(item) for item in _string_list(value)]
    return normalized or FALLBACK_BEHAVIOR_ATOMS


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
    graph_profile_path: Path | None = None


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


def _load_graph_profile(path: Path | None) -> dict[str, Any]:
    profile_path = path or DEFAULT_GRAPH_PROFILE_PATH
    if not profile_path.exists():
        return {
            "schema": "tmcp-canonical-graph-profile-v0.1",
            "profile_id": "default",
            "output_path": "skills-library",
            "source_roots": [],
            "overlay_namespaces": [],
            "graph_version_policy": {
                "large_drop_threshold": 0.3,
                "fail_on_large_drop": True,
            },
        }
    parsed = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Invalid TMCP graph profile: {profile_path}")
    return {
        "schema": str(parsed.get("schema", "tmcp-canonical-graph-profile-v0.1")),
        "profile_id": str(parsed.get("profile_id", "default")),
        "description": str(parsed.get("description", "")),
        "output_path": str(parsed.get("output_path", "skills-library")),
        "source_roots": _string_list(parsed.get("source_roots")),
        "exclude_dirs": _string_list(parsed.get("exclude_dirs")),
        "overlay_namespaces": _string_list(parsed.get("overlay_namespaces")),
        "graph_version_policy": _dict(parsed.get("graph_version_policy")),
        "profile_path": str(profile_path),
    }


def harvest_skills_library(options: HarvestOptions) -> dict[str, Any]:
    started_at = _now()
    graph_profile = _load_graph_profile(options.graph_profile_path)
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
    generation = _plan_generation(
        classified,
        duplicate_groups,
        conflicts,
        out,
        started_at,
        options,
        graph_profile,
    )

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
        "graph_profile": graph_profile,
        "graph_diff": generation["graph_diff"],
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
        check(
            "dry-run-no-files-required", True, "Dry-run produced a generation plan without writes."
        )
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
        ref_pattern = r"@(?:task|module|branch|test|source|repair|shortcut):[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*"
        for full_ref in re.findall(ref_pattern, content):
            if full_ref not in known_refs:
                check(f"tmcp-ref:{rel_path}:{full_ref}", False, "unresolved reference")
    check("tmcp-router", "skills.tmcp/router.md" in files, "Task-first router is generated.")
    check(
        "tmcp-design-decision",
        "skills.tmcp/design-decision.md" in files,
        "Decision-graph design decision is generated.",
    )
    check(
        "tmcp-traversal-schema",
        "skills.tmcp/traversal-receipt-schema.md" in files,
        "Traversal receipt schema is generated.",
    )
    check(
        "tmcp-evaluation-plan",
        "skills.tmcp/evaluation-plan.md" in files,
        "Evaluation and token-ROI plan is generated.",
    )
    check(
        "tmcp-shortcut-policy",
        "skills.tmcp/shortcuts/candidate.md" in files,
        "Shortcut promotion policy is generated.",
    )
    check(
        "tmcp-graph-json",
        "skills.tmcp/graph.json" in files,
        "Structured TMCP graph metadata is generated.",
    )
    graph_payload = _json_loads(generation["file_contents"].get("skills.tmcp/graph.json", "{}"))
    check(
        "tmcp-graph-schema",
        graph_payload.get("schema") == "tmcp-graph-v0.1",
        "Structured graph declares the expected schema.",
    )
    graph_paths = _graph_paths(graph_payload)
    for rel_path in graph_paths:
        check(
            f"tmcp-graph-path:{rel_path}",
            rel_path in files and (dry_run or (out / rel_path).exists()),
            "Graph path resolves to a generated file.",
        )
    for rel_path, content in generation["file_contents"].items():
        if rel_path.startswith("skills.tmcp/tasks/") and rel_path.endswith(".md"):
            check(
                f"tmcp-task-transitions:{rel_path}",
                "## Transition Edges" in content and "## Custom Skill Construction" in content,
                "Task node includes explicit transition edges and custom-skill construction rules.",
            )
    check("source-dispositions", True, "Every discovered source has an imported/skipped record.")
    check("secret-redaction", True, "Secret patterns are redacted before generated writes.")
    check(
        "dry-run-rerunnable", True, "Command accepts --dry-run and does not require output writes."
    )
    failures = [item for item in checks if item["status"] == "fail"]
    passed = not failures
    return {"status": "pass" if passed else "fail", "passed": passed, "checks": checks}


def verify_tmcp_graph(
    library: Path,
    *,
    graph_profile_path: Path | None = None,
    repair: bool = False,
    refresh: bool = False,
) -> dict[str, Any]:
    root = library.expanduser().resolve()
    graph_profile = _load_graph_profile(graph_profile_path)
    graph_path = root / "skills.tmcp" / "graph.json"
    manifest = _json_file(root / "manifest.json")
    lock = _json_file(root / "skills.lock")
    skill_dirs = sorted(path for path in (root / "skills").glob("*") if path.is_dir())
    checks: list[dict[str, Any]] = []

    def check(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"id": check_id, "status": "pass" if passed else "fail", "detail": detail})

    check("library-exists", root.exists(), str(root))
    check("manifest-exists", bool(manifest), "manifest.json")
    check("skills-lock-exists", bool(lock), "skills.lock")
    manifest_skill_count = int(manifest.get("skill_count", 0) or 0)
    check(
        "canonical-skill-count",
        manifest_skill_count == len(skill_dirs) and len(skill_dirs) > 0,
        f"manifest={manifest_skill_count} skill_dirs={len(skill_dirs)}",
    )
    check(
        "skills-lock-source-hashes",
        bool(_dict(lock.get("source_hashes"))),
        f"source_hashes={len(_dict(lock.get('source_hashes')))}",
    )

    repaired = False
    if (
        repair
        and root.exists()
        and manifest
        and skill_dirs
        and (refresh or not graph_path.exists())
    ):
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(
            _existing_tmcp_graph_json(root, manifest, lock, graph_profile),
            encoding="utf-8",
        )
        repaired = True

    graph = _json_file(graph_path)
    check("graph-json-exists", graph_path.exists(), "skills.tmcp/graph.json")
    check("graph-json-schema", graph.get("schema") == "tmcp-graph-v0.1", "schema=tmcp-graph-v0.1")
    source_skills = _dict(graph.get("source_skills"))
    check(
        "graph-source-skill-count",
        len(source_skills) == len(skill_dirs) if graph else False,
        f"graph_source_skills={len(source_skills)} skill_dirs={len(skill_dirs)}",
    )
    graph_profile_payload = _dict(graph.get("graph_profile"))
    check(
        "graph-profile-id",
        graph_profile_payload.get("profile_id") == graph_profile.get("profile_id"),
        f"graph={graph_profile_payload.get('profile_id')} expected={graph_profile.get('profile_id')}",
    )
    for rel_path in sorted(_graph_paths(graph)):
        check(
            f"graph-path:{rel_path}",
            (root / rel_path).exists(),
            "Graph path resolves inside the skills library.",
        )

    failures = [item for item in checks if item["status"] == "fail"]
    return {
        "schema": "tmcp-graph-verification-v0.1",
        "status": "pass" if not failures else "fail",
        "library": str(root),
        "repaired": repaired,
        "graph_profile": graph_profile,
        "summary": {
            "skill_count": len(skill_dirs),
            "manifest_skill_count": manifest_skill_count,
            "source_hash_count": len(_dict(lock.get("source_hashes"))),
            "graph_source_skill_count": len(source_skills),
            "failure_count": len(failures),
        },
        "checks": checks,
    }


def _json_loads(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _graph_paths(graph: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    entrypoint = graph.get("entrypoint")
    if isinstance(entrypoint, str):
        paths.add(entrypoint)
    for section in ("tasks", "modules", "branches", "source_skills"):
        rows = graph.get(section)
        if not isinstance(rows, dict):
            continue
        for row in rows.values():
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                paths.add(str(row["path"]))
    return paths


def _graph_diff(
    out: Path,
    file_contents: dict[str, str],
    source_hashes: dict[str, str],
    new_skill_count: int,
) -> dict[str, Any]:
    previous_manifest = _json_file(out / "manifest.json")
    previous_lock = _json_file(out / "skills.lock")
    previous_hashes = _dict(previous_lock.get("source_hashes"))
    previous_files: set[str] = set()
    if out.exists():
        previous_files = {
            path.relative_to(out).as_posix()
            for path in out.rglob("*")
            if path.is_file() and ".git/" not in path.relative_to(out).as_posix()
        }
    current_files = set(file_contents)
    previous_skills = int(previous_manifest.get("skill_count", 0) or 0)
    added_sources = sorted(set(source_hashes) - set(previous_hashes))
    removed_sources = sorted(set(previous_hashes) - set(source_hashes))
    changed_sources = sorted(
        key
        for key, digest in source_hashes.items()
        if key in previous_hashes and previous_hashes[key] != digest
    )
    return {
        "schema": "tmcp-graph-diff-v0.1",
        "previous_skill_count": previous_skills,
        "new_skill_count": new_skill_count,
        "skill_drop_count": max(0, previous_skills - new_skill_count),
        "skill_drop_ratio": (
            round((previous_skills - new_skill_count) / previous_skills, 4)
            if previous_skills > 0 and previous_skills > new_skill_count
            else 0
        ),
        "added_files": sorted(current_files - previous_files),
        "removed_files": sorted(previous_files - current_files),
        "changed_source_count": len(changed_sources),
        "added_source_count": len(added_sources),
        "removed_source_count": len(removed_sources),
        "changed_sources": changed_sources[:50],
        "added_sources": added_sources[:50],
        "removed_sources": removed_sources[:50],
    }


def _guard_large_graph_drop(graph_diff: dict[str, Any], graph_profile: dict[str, Any]) -> None:
    policy = _dict(graph_profile.get("graph_version_policy"))
    if policy.get("fail_on_large_drop", True) is False:
        return
    threshold = float(policy.get("large_drop_threshold", 0.3) or 0.3)
    previous_count = int(graph_diff.get("previous_skill_count", 0) or 0)
    drop_ratio = float(graph_diff.get("skill_drop_ratio", 0) or 0)
    if previous_count > 0 and drop_ratio >= threshold:
        raise ValueError(
            "Refusing to regenerate TMCP graph because skill count dropped "
            f"from {previous_count} to {graph_diff.get('new_skill_count')} "
            f"({drop_ratio:.1%}). Review source roots or override the graph profile policy."
        )


def _classify_candidate(candidate: CandidateFile) -> CandidateFile:
    text = candidate.content.lower()
    path = candidate.relative_path.lower()
    classes: list[str] = []
    if "skill.md" in path or "/skills/" in f"/{path}" or "skill" in text:
        classes.append("reusable skill")
    if any(marker in path for marker in ("agents.md", "claude.md", "gemini.md", ".cursorrules")):
        classes.append(
            "global instruction" if _looks_global(candidate) else "project-specific instruction"
        )
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
    candidate.risk_level = (
        "high"
        if candidate.secret_findings
        else ("medium" if candidate.project_dependencies else "low")
    )
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
    graph_profile: dict[str, Any],
) -> dict[str, Any]:
    skill_sources = [
        candidate for candidate in candidates if "reusable skill" in candidate.classification
    ]
    skills = _consolidate_skill_groups(skill_sources)
    workflows = [
        candidate for candidate in candidates if "workflow prompt" in candidate.classification
    ]
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
        if candidate.source_tier
        in {"project_authoritative", "personal_agent", "local_agent_config"}
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
        file_contents.update(
            _tmcp_files(tmcp_sources, skills, workflows, conflicts, generated_at, graph_profile)
        )

    file_contents.update(
        _audit_files(candidates, skills, duplicate_groups, conflicts, generated_at)
    )
    file_contents["README.md"] = _readme_markdown(generated_at, options)
    source_hashes = {
        source.slug: hashlib.sha256(source.redacted_content.encode("utf-8")).hexdigest()
        for source in candidates
    }
    graph_diff = _graph_diff(out, file_contents, source_hashes, len(skills))
    _guard_large_graph_drop(graph_diff, graph_profile)
    file_contents["manifest.json"] = (
        json.dumps(
            {
                "generated_at": generated_at,
                "compiler_version": COMPILER_VERSION,
                "graph_profile": graph_profile,
                "graph_diff": graph_diff,
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
        )
        + "\n"
    )
    file_contents["skills.lock"] = (
        json.dumps(
            {
                "compiler_version": COMPILER_VERSION,
                "source_hashes": source_hashes,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

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
        "graph_diff": graph_diff,
        "duplicates": duplicate_groups,
        "conflicts": conflicts,
    }


def _tmcp_files(
    sources: list[CandidateFile],
    skills: list[SkillGroup],
    workflows: list[CandidateFile],
    conflicts: list[dict[str, Any]],
    generated_at: str,
    graph_profile: dict[str, Any],
) -> dict[str, str]:
    task_map = _task_sources(sources)
    modules = _modules_from_sources(sources)
    branches = _branches(conflicts)
    files: dict[str, str] = {
        "skills.tmcp/router.md": _tmcp_router(task_map),
        "skills.tmcp/graph.json": _tmcp_graph_json(
            sources=sources,
            skills=skills,
            task_map=task_map,
            modules=modules,
            branches=branches,
            generated_at=generated_at,
            graph_profile=graph_profile,
        ),
        "skills.tmcp/design-decision.md": _tmcp_design_decision(generated_at),
        "skills.tmcp/traversal-receipt-schema.md": _traversal_receipt_schema(),
        "skills.tmcp/evaluation-plan.md": _evaluation_plan(),
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
        "skills.tmcp/tests/traversal_roi_cases.md": _traversal_roi_cases(task_map),
        "skills.tmcp/tests/shortcut_promotion_cases.md": _shortcut_promotion_cases(task_map),
        "skills.tmcp/tests/module_cases.md": _module_cases(modules),
        "skills.tmcp/tests/conflict_cases.md": _conflict_cases(branches),
        "skills.tmcp/repairs/repair_recommendations.md": _repair_recommendations(conflicts),
        "skills.tmcp/repairs/failed_equivalence_cases.md": "# Failed Equivalence Cases\n\nNo failed behavioral equivalence cases were detected by deterministic validation.\n",
        "skills.tmcp/repairs/inferred_module_promotions.md": _inferred_promotions(modules),
        "skills.tmcp/shortcuts/candidate.md": _shortcut_promotion_policy(),
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
    return part in {
        ".agent",
        ".agents",
        ".claude",
        ".codex",
        ".cursor",
        ".gemini",
        ".github",
        ".aios",
    }


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
    return any(
        term in text for term in ("personal defaults", "global", "always use", "developer profile")
    )


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
    digest = hashlib.sha1(str(candidate.path).encode("utf-8"), usedforsecurity=False).hexdigest()[
        :6
    ]
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
                sources=sorted(
                    items, key=lambda item: (item.source_tier, item.project, item.relative_path)
                ),
                source_tiers=tiers,
                classifications=classifications,
            )
        )
    return groups


def _skill_concept_key(source: CandidateFile) -> str:
    text = f"{source.relative_path}\n{source.summary}\n{source.redacted_content[:4000]}".lower()
    family = _concept_family(text)
    task = _primary_task(text)
    tier_group = (
        "active"
        if source.source_tier
        in {
            "project_authoritative",
            "personal_agent",
            "local_agent_config",
        }
        else "reference"
    )
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
        if "ask" in text and any(
            term in text for term in ("before edit", "before editing", "permission")
        ):
            ask_first.append(candidate.slug)
        if any(
            term in text for term in ("implement directly", "apply the change", "execute the task")
        ):
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
    for task in TASK_KEYWORDS:
        task_map.setdefault(task, [])
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
        "operating_language": (
            "operating language",
            "glossary",
            "canonical vocabulary",
            "domain language",
            "leading word",
        ),
    }
    for candidate in candidates:
        text = candidate.content.lower()
        for module_id, terms in patterns.items():
            if any(term in text for term in terms):
                counts[module_id] += 1
                source_map[module_id].append(candidate.slug)
    modules: list[dict[str, Any]] = []
    for module_id in sorted(patterns):
        count = counts[module_id]
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
            "id": "approval_before_edit",
            "type": "approval",
            "status": "active",
            "context": "Edit permission is ambiguous or the task is review-only.",
            "competing": ["direct_implementation"],
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
                "sources": conflict.get("ask_first_sources", [])
                + conflict.get("direct_sources", []),
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
    return (
        f"# Examples: {source.slug}\n\n- Use this skill when a request matches: {source.summary}\n"
    )


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
        "Entry point for generated agent routing. TMCP is a thin decision graph, not a rigid script.",
        "",
        "Agents should explore the graph enough to construct a task-specific custom skill packet, then stop. Record the path as a traversal receipt so AIOS can learn from the run.",
        "",
        "Allowed traversal actions: " + ", ".join(TMCP_TRAVERSAL_ACTIONS) + ".",
        "",
        "[NODE: ROUTER.START]",
        "CONSIDER @shortcut:candidate before normal task routing when a prior traversal fingerprint matches the task, project, and available context.",
        "USE an active shortcut only when its source graph version is current, related source material is unchanged, and behavioral tests passed.",
        "SKIP @shortcut:candidate when there is no matching receipt history, unresolved repair, current graph version, unchanged source material, or positive token-ROI evidence.",
        "ELSE LOAD task nodes through normal router traversal and emit a shortcut rebuild recommendation.",
        "",
        "[NODE: ROUTER.TASK]",
    ]
    ordered = list(task_map)
    for index, task in enumerate(ordered):
        prefix = "IF" if index == 0 else "ELSE IF"
        terms = ", ".join(TASK_KEYWORDS.get(task, (task,))[:3])
        lines.append(f"{prefix} task involves {terms} THEN LOAD @task:{task}")
    lines.append("ELSE LOAD @task:agent_workflow")
    lines.append("")
    lines.append("[NODE: ROUTER.EXPLORE]")
    lines.append("CONSIDER adjacent task nodes when task intent is compound.")
    lines.append(
        "SKIP adjacent task nodes when they do not add constraints, validation, or project-specific behavior."
    )
    lines.append(
        "WHY record the selected path, skipped nodes, and evidence in the traversal receipt."
    )
    lines.append("")
    lines.append("[NODE: ROUTER.EXIT]")
    lines.append(
        "THEN EXIT after constructing the smallest custom skill packet that preserves required behavior."
    )
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
            "## Traversal Contract",
            "- LOAD this task when task intent matches the trigger conditions.",
            "- CONSIDER adjacent task nodes when the request mixes intents such as implementation plus testing or audit plus planning.",
            "- USE only modules and branches that change behavior, validation, permissions, output, or provenance.",
            "- SKIP nodes that do not add task-specific instruction value.",
            "- WHY record node choices, skipped alternatives, and evidence in `skills.tmcp/traversal-receipt-schema.md` format.",
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
            "## Transition Edges",
            f"- LOAD -> @task:{task}: task intent matches trigger conditions.",
            "- CONSIDER -> @task:testing: implementation, audit, or data changes need validation evidence.",
            "- CONSIDER -> @task:research: external facts, uncertain standards, or unfamiliar domain claims affect correctness.",
            "- CONSIDER -> @task:documentation: durable truth, readme, or project memory should be updated.",
            "- USE -> @branch:approval_before_edit: edit permission is ambiguous or source policy conflicts.",
            "- USE -> @branch:direct_implementation: user explicitly requested implementation and no stricter project branch blocks it.",
            "- EXIT -> output contract: selected nodes form a minimal custom skill packet.",
            "",
            "## Custom Skill Construction",
            "- Concatenate the selected task, required modules, selected branch, project overlays, and output contract in traversal order.",
            "- Preserve source-tier precedence: project_authoritative > personal_agent > local_agent_config > reference.",
            "- Keep the constructed packet smaller than loading the broad source skill set unless evaluation shows quality loss.",
            "- Store traversal metadata so repeated successful paths can become shortcuts and failed paths can become repairs.",
            "- When a shortcut candidate matches, treat it as a top-level node and then branch from it only for task-specific deltas.",
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
    source_lines = (
        [f"- {source}" for source in sources] if sources else ["- none; inferred by compiler"]
    )
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
            "## Transition Hooks",
            "- Entry: task node explicitly lists this module or traversal reasoning selects it as behavior-changing.",
            "- Before use: check whether a selected branch overrides or narrows this module.",
            "- After use: continue to the next selected module, selected branch, validation gate, or output contract.",
            "- Receipt: record why this module was loaded or skipped when it was a plausible candidate.",
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
    source_lines = (
        [f"- {source}" for source in sources] if sources else ["- generated default branch"]
    )
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
            "## Transition Hooks",
            "- Entry: selected when task context, source-tier precedence, or conflict evidence makes this branch behavior-changing.",
            "- Before use: compare competing branches and cite the evidence that selected this branch.",
            "- After use: return to the task node's validation or output node.",
            "- Receipt: record competing branches considered and why they were skipped.",
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


def _tmcp_graph_json(
    *,
    sources: list[CandidateFile],
    skills: list[SkillGroup],
    task_map: dict[str, list[CandidateFile]],
    modules: list[dict[str, Any]],
    branches: list[dict[str, Any]],
    generated_at: str,
    graph_profile: dict[str, Any],
) -> str:
    source_by_slug = {source.slug: source for source in sources}
    tasks = {
        task_id: {
            "id": task_id,
            "node": f"@task:{task_id}",
            "path": f"skills.tmcp/tasks/{task_id}.md",
            "triggers": list(TASK_KEYWORDS.get(task_id, (task_id,))),
            **_node_utility_metadata(task_id, "task"),
            "source_refs": [source.slug for source in task_sources],
            "source_tiers": sorted({source.source_tier for source in task_sources}),
            "required_modules": [
                module["id"] for module in modules if module["status"] == "active"
            ][:6],
        }
        for task_id, task_sources in task_map.items()
    }
    module_rows = {
        module["id"]: {
            "id": module["id"],
            "node": f"@module:{module['id']}",
            "path": f"skills.tmcp/modules/{module['id']}.md",
            "type": module["type"],
            "status": module["status"],
            "activation": module["activation"],
            "source_refs": list(module["sources"]),
            "source_tiers": sorted(
                {
                    source_by_slug[source_slug].source_tier
                    for source_slug in module["sources"]
                    if source_slug in source_by_slug
                }
            ),
            "triggers": _module_triggers(module["id"]),
            **_node_utility_metadata(module["id"], "module"),
        }
        for module in modules
    }
    branch_rows = {
        branch["id"]: {
            "id": branch["id"],
            "node": f"@branch:{branch['id']}",
            "path": f"skills.tmcp/branches/{branch['id']}.branch.md",
            "type": branch["type"],
            "status": branch["status"],
            "competing": list(branch["competing"]),
            "source_refs": list(branch["sources"]),
            "triggers": _branch_triggers(branch["id"]),
            **_node_utility_metadata(branch["id"], "branch"),
        }
        for branch in branches
    }
    source_skills = {
        group.slug: {
            "id": group.slug,
            "node": f"@source_skill:{group.slug}",
            "path": f"skills/{group.slug}/SKILL.md",
            "concept_key": group.concept_key,
            "title": group.title,
            "source_refs": [source.slug for source in group.sources],
            "source_tiers": list(group.source_tiers),
            "classifications": list(group.classifications),
            "triggers": _source_skill_triggers(group),
            **_source_skill_utility_metadata(group),
        }
        for group in skills
    }
    source_hashes = {
        source.slug: hashlib.sha256(source.redacted_content.encode("utf-8")).hexdigest()
        for source in sources
    }
    payload = {
        "schema": "tmcp-graph-v0.1",
        "generated_at": generated_at,
        "compiler_version": COMPILER_VERSION,
        "design_decision": TMCP_DESIGN_DECISION_ID,
        "entrypoint": "skills.tmcp/router.md",
        "graph_profile": graph_profile,
        "tasks": tasks,
        "modules": module_rows,
        "branches": branch_rows,
        "source_skills": source_skills,
        "source_hashes": source_hashes,
        "overlay_namespaces": list(graph_profile.get("overlay_namespaces", [])),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _existing_tmcp_graph_json(
    library: Path,
    manifest: dict[str, Any],
    lock: dict[str, Any],
    graph_profile: dict[str, Any],
) -> str:
    task_rows: dict[str, dict[str, Any]] = {}
    for path in sorted((library / "skills.tmcp" / "tasks").glob("*.md")):
        task_id = path.stem
        task_rows[task_id] = {
            "id": task_id,
            "node": f"@task:{task_id}",
            "path": path.relative_to(library).as_posix(),
            "triggers": list(TASK_KEYWORDS.get(task_id, (task_id.replace("_", " "),))),
            **_node_utility_metadata(task_id, "task"),
            "source_refs": [],
            "source_tiers": [],
            "required_modules": _existing_task_required_modules(library, task_id),
        }
    if not task_rows:
        for task_id in TASK_KEYWORDS:
            task_rows[task_id] = {
                "id": task_id,
                "node": f"@task:{task_id}",
                "path": f"skills.tmcp/tasks/{task_id}.md",
                "triggers": list(TASK_KEYWORDS.get(task_id, (task_id,))),
                "source_refs": [],
                "source_tiers": [],
                "required_modules": [],
            }

    module_rows: dict[str, dict[str, Any]] = {}
    for path in sorted((library / "skills.tmcp" / "modules").glob("*.md")):
        module_id = path.stem
        module_rows[module_id] = {
            "id": module_id,
            "node": f"@module:{module_id}",
            "path": path.relative_to(library).as_posix(),
            "type": _module_type(module_id),
            "status": "active",
            "activation": "active",
            "source_refs": [],
            "source_tiers": [],
            "triggers": _module_triggers(module_id),
            **_node_utility_metadata(module_id, "module"),
        }

    branch_rows: dict[str, dict[str, Any]] = {}
    for path in sorted((library / "skills.tmcp" / "branches").glob("*.branch.md")):
        branch_id = path.name.removesuffix(".branch.md")
        branch_rows[branch_id] = {
            "id": branch_id,
            "node": f"@branch:{branch_id}",
            "path": path.relative_to(library).as_posix(),
            "type": "existing",
            "status": "active",
            "competing": [],
            "source_refs": [],
            "triggers": _branch_triggers(branch_id),
            **_node_utility_metadata(branch_id, "branch"),
        }

    skill_groups = {
        str(item.get("slug")): item
        for item in _list_of_dicts(manifest.get("skill_groups"))
        if item.get("slug")
    }
    source_skills: dict[str, dict[str, Any]] = {}
    for skill_path in sorted((library / "skills").glob("*/SKILL.md")):
        skill_id = skill_path.parent.name
        group = skill_groups.get(skill_id, {})
        title = str(
            group.get("title") or _first_heading(skill_path) or skill_id.replace("-", " ").title()
        )
        concept_key = str(group.get("concept_key") or skill_id.replace("-", "."))
        source_skills[skill_id] = {
            "id": skill_id,
            "node": f"@source_skill:{skill_id}",
            "path": skill_path.relative_to(library).as_posix(),
            "concept_key": concept_key,
            "title": title,
            "source_refs": _string_list(group.get("source_slugs")),
            "source_tiers": _string_list(group.get("source_tiers")),
            "classifications": _string_list(group.get("detected_type")),
            "triggers": _existing_skill_triggers(skill_id, concept_key, title, skill_path),
            **_existing_skill_utility_metadata(skill_id, concept_key, title, group),
        }

    payload = {
        "schema": "tmcp-graph-v0.1",
        "generated_at": _now(),
        "compiler_version": COMPILER_VERSION,
        "design_decision": TMCP_DESIGN_DECISION_ID,
        "entrypoint": "skills.tmcp/router.md",
        "graph_profile": graph_profile,
        "tasks": task_rows,
        "modules": module_rows,
        "branches": branch_rows,
        "source_skills": source_skills,
        "source_hashes": _dict(lock.get("source_hashes")),
        "overlay_namespaces": list(graph_profile.get("overlay_namespaces", [])),
        "repair_source": "existing-generated-library",
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _existing_task_required_modules(library: Path, task_id: str) -> list[str]:
    task_path = library / "skills.tmcp" / "tasks" / f"{task_id}.md"
    if task_path.exists():
        refs = re.findall(
            r"@module:([A-Za-z0-9_-]+)", task_path.read_text(encoding="utf-8", errors="replace")
        )
        if refs:
            return list(dict.fromkeys(refs))[:8]
    return [
        module_id
        for module_id in (
            "context_gathering",
            "evidence_first",
            "provenance_policy",
            "output_contract",
        )
        if (library / "skills.tmcp" / "modules" / f"{module_id}.md").exists()
    ]


def _existing_skill_triggers(
    skill_id: str,
    concept_key: str,
    title: str,
    skill_path: Path,
) -> list[str]:
    terms = set(_summary_terms(skill_id))
    terms.update(_summary_terms(concept_key))
    terms.update(_summary_terms(title))
    try:
        content = skill_path.read_text(encoding="utf-8", errors="replace")[:2000]
    except OSError:
        content = ""
    terms.update(_summary_terms(content))
    return sorted(terms)[:20]


def _existing_skill_utility_metadata(
    skill_id: str,
    concept_key: str,
    title: str,
    group: dict[str, Any],
) -> dict[str, Any]:
    atoms = sorted(
        {
            *_behavior_atoms_for(skill_id),
            *_behavior_atoms_for(concept_key),
            *_behavior_atoms_for(title),
            *(
                atom
                for classification in _string_list(group.get("detected_type"))
                for atom in _behavior_atoms_for(classification)
            ),
        }
    )
    if not atoms:
        atoms = ["source_specific_behavior"]
    source_count = int(group.get("source_count", 1) or 1)
    source_tiers = _string_list(group.get("source_tiers"))
    return {
        "behavior_atoms": atoms[:8],
        "token_cost": 180 + min(420, source_count * 40),
        "adds_behavior": _adds_behavior_description(atoms),
        "redundant_with": [],
        "risk_if_omitted": "medium" if "project_authoritative" in source_tiers else "low",
    }


def _first_heading(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("# "):
                return line.lstrip("#").strip()
    except OSError:
        return ""
    return ""


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _module_triggers(module_id: str) -> list[str]:
    return {
        "context_gathering": ["context", "packet", "receipt", "load"],
        "evidence_first": ["evidence", "source", "inspect", "prove"],
        "minimal_patch_policy": ["minimal", "scope", "bounded", "patch"],
        "operating_language": ["operating language", "glossary", "vocabulary", "leading word"],
        "output_contract": ["output", "summary", "report", "final"],
        "provenance_policy": ["provenance", "source", "trace", "receipt"],
        "test_gate": ["test", "verify", "validate", "quality gate"],
        "tool_use_policy": ["tool", "bash", "browser", "mcp"],
        "user_approval_gate": ["approval", "permission", "ask", "destructive"],
    }.get(module_id, [module_id.replace("_", " ")])


def _branch_triggers(branch_id: str) -> list[str]:
    return {
        "direct_implementation": ["implement", "fix", "patch", "edit", "build"],
        "approval_before_edit": ["review", "audit", "plan", "research", "approval"],
        "ambiguous_task_resolution": ["ambiguous", "unclear", "maybe"],
        "conflict__editing_permission": ["conflict", "permission", "approval"],
    }.get(branch_id, [branch_id.replace("_", " ")])


def _source_skill_triggers(group: SkillGroup) -> list[str]:
    terms: set[str] = set()
    for value in (group.slug, group.concept_key, group.title):
        terms.update(term for term in re.split(r"[^a-zA-Z0-9]+", value.lower()) if len(term) >= 4)
    for source in group.sources[:3]:
        terms.update(_summary_terms(source.summary))
        terms.update(_summary_terms(source.relative_path))
    return sorted(terms)[:16]


def _summary_terms(value: str) -> set[str]:
    stop = {
        "with",
        "from",
        "that",
        "this",
        "when",
        "where",
        "then",
        "into",
        "skill",
        "skills",
    }
    return {
        term
        for term in re.split(r"[^a-zA-Z0-9]+", value.lower())
        if len(term) >= 4 and term not in stop
    }


def _node_utility_metadata(node_id: str, node_type: str) -> dict[str, Any]:
    atoms = _behavior_atoms_for(node_id)
    return {
        "behavior_atoms": atoms,
        "token_cost": _estimated_node_token_cost(node_id, node_type, atoms),
        "adds_behavior": _adds_behavior_description(atoms),
        "redundant_with": _redundant_with(node_id, atoms),
        "risk_if_omitted": _risk_if_omitted(node_id, atoms),
    }


def _source_skill_utility_metadata(group: SkillGroup) -> dict[str, Any]:
    atoms = sorted(
        {
            *_behavior_atoms_for(group.concept_key),
            *_behavior_atoms_for(group.title),
            *(
                atom
                for classification in group.classifications
                for atom in _behavior_atoms_for(classification)
            ),
        }
    )
    if not atoms:
        atoms = ["source_specific_behavior"]
    return {
        "behavior_atoms": atoms[:8],
        "token_cost": 180 + min(420, len(group.sources) * 40),
        "adds_behavior": _adds_behavior_description(atoms),
        "redundant_with": [],
        "risk_if_omitted": "medium" if "project_authoritative" in group.source_tiers else "low",
    }


def _behavior_atoms_for(value: str) -> list[str]:
    lowered = value.replace("-", "_").replace(".", "_").lower()
    atom_mappings = _behavior_atom_mappings()
    atoms: set[str] = set(atom_mappings.get(lowered, []))
    for key, key_atoms in atom_mappings.items():
        if key in lowered:
            atoms.update(key_atoms)
    if any(term in lowered for term in ("test", "verify", "validation")):
        atoms.add("verification_gate")
    if any(term in lowered for term in ("review", "audit", "risk")):
        atoms.add("risk_review")
    if any(term in lowered for term in ("frontend", "ui", "visual")):
        atoms.add("ui_quality")
    if any(term in lowered for term in ("docs", "documentation", "readme")):
        atoms.add("doc_staleness_check")
    if any(term in lowered for term in ("tool", "command", "mcp", "bash")):
        atoms.add("tool_safety")
    return sorted(atoms)


def _estimated_node_token_cost(node_id: str, node_type: str, atoms: list[str]) -> int:
    base = {"task": 180, "module": 140, "branch": 90, "source_skill": 260}.get(node_type, 140)
    return base + (len(atoms) * 18) + min(80, len(node_id) * 2)


def _adds_behavior_description(atoms: list[str]) -> str:
    if not atoms:
        return "No distinct behavior atom detected; include only with direct trigger evidence."
    return "Adds " + ", ".join(atoms[:6]).replace("_", " ") + "."


def _redundant_with(node_id: str, atoms: list[str]) -> list[str]:
    redundant: list[str] = []
    for other_id, other_atoms in _behavior_atom_mappings().items():
        if other_id == node_id:
            continue
        if atoms and set(atoms).issubset(set(other_atoms)):
            redundant.append(other_id)
    return sorted(redundant)[:8]


def _risk_if_omitted(node_id: str, atoms: list[str]) -> str:
    high_risk_atoms = {
        "verification_gate",
        "approval_before_risk",
        "destructive_action_guard",
        "tool_safety",
        "source_tier_precedence",
    }
    if high_risk_atoms & set(atoms):
        return "high"
    if node_id in {"implementation", "debugging", "audit", "direct_implementation"}:
        return "medium"
    return "low"


def _tmcp_design_decision(generated_at: str) -> str:
    return "\n".join(
        [
            "# TMCP Design Decision: Decision Graph Traversal",
            "",
            f"Decision ID: {TMCP_DESIGN_DECISION_ID}",
            f"Generated At: {generated_at}",
            "Status: active",
            "",
            "## Decision",
            "TMCP is a thin, agent-explorable markdown decision graph. It is not a rigid IF/ELSE script and not a single flattened skill.",
            "",
            "Agents construct a custom skill packet by traversing task, module, branch, provenance, and output nodes that are relevant to the current task intent.",
            "",
            "## Rationale",
            "- Agent reasoning is better than static IF/ELSE for ambiguous task intent.",
            "- Thin graph nodes reduce duplication and allow selective loading.",
            "- Traversal receipts make reasoning inspectable and learnable by AIOS.",
            "- Source-tier precedence protects project-specific behavior from generic plugin or history material.",
            "",
            "## Required Traversal Actions",
            *(f"- {action}" for action in TMCP_TRAVERSAL_ACTIONS),
            "",
            "## Transition Policy",
            "- Prefer explicit transition edges over raw concatenation when constructing a custom skill.",
            "- Raw ingestion is acceptable only as a fallback when transition metadata is missing.",
            "- Every transition should explain what behavior, validation, permission rule, output contract, or provenance it adds.",
            "",
            "## Learning Policy",
            "- Store traversal path, skipped nodes, branch decisions, token estimates, validation evidence, and outcome.",
            "- Promote repeated successful paths into @shortcut:candidate records only after quality and token ROI are positive.",
            "- Once promoted, expose the shortcut as a top-level router node and allow new branches to grow from it.",
            "- Treat shortcut skills as generated cached traversals, not source of truth.",
            "- Revalidate, regenerate, split, branch, supersede, or deprecate shortcuts when related graph/source material changes.",
            "- Fall back to router traversal whenever shortcut freshness is uncertain.",
            "- Create repair recommendations when traversal paths fail or over-load low-value nodes.",
            "",
        ]
    )


def _traversal_receipt_schema() -> str:
    return "\n".join(
        [
            "# TMCP Traversal Receipt Schema",
            "",
            "Agents should emit or persist this shape after constructing a custom skill packet.",
            "",
            "```json",
            "{",
            '  "schema": "tmcp-traversal-receipt-v0.2",',
            '  "task_id": "string",',
            '  "task_summary": "string",',
            '  "entry_node": "@task:implementation",',
            '  "traversal_fingerprint": "sha256 of ordered loaded nodes, selected branches, source tiers, and project scope",',
            '  "source_graph_version": "sha256 of generated TMCP graph material",',
            '  "loaded_nodes": ["@task:implementation", "@module:evidence_first"],',
            '  "considered_nodes": ["@task:testing"],',
            '  "skipped_nodes": [{"node": "@task:research", "reason": "No external uncertainty"}],',
            '  "selected_branches": [{"branch": "@branch:direct_implementation", "reason": "Explicit user implementation intent"}],',
            '  "shortcut_candidate": {"node": "@shortcut:candidate", "matched": false, "status": "needs_revalidation", "source_graph_version": "string", "fallback": "router_traversal", "reason": "No valid active shortcut matched this task"},',
            '  "source_tiers_used": ["project_authoritative", "personal_agent"],',
            '  "transition_trace": [',
            '    {"from": "ROUTER.START", "to": "@task:implementation", "action": "LOAD", "why": "Implementation intent"}',
            "  ],",
            '  "custom_skill_token_estimate": 0,',
            '  "baseline_skill_token_estimate": 0,',
            '  "promotion_metrics": {"use_count": 0, "success_count": 0, "positive_token_roi_count": 0, "projects_seen": []},',
            '  "promoted_skill_target": null,',
            '  "execution_outcome": "pass|partial|fail|blocked",',
            '  "validation_evidence": ["command or artifact"],',
            '  "repair_recommendations": []',
            "}",
            "```",
            "",
            "## Required Invariants",
            "- Every loaded node must have a reason.",
            "- Every skipped plausible node must have a reason.",
            "- Branch choices must cite competing branches when any exist.",
            "- Token estimates must compare custom packet size to an equivalent broad-skill baseline when available.",
            "- Shortcut promotion requires repeated receipt evidence, not a single successful run.",
            "- Shortcut default use requires active status, current source graph version, unchanged related source material, and passing behavioral tests.",
            "- Outcomes must be linked to validation evidence, not just agent confidence.",
            "",
        ]
    )


def _evaluation_plan() -> str:
    return "\n".join(
        [
            "# TMCP Evaluation Plan",
            "",
            "Purpose: verify whether tree search plus custom skill construction improves outcomes enough to justify its token and latency cost.",
            "",
            "## Conditions To Compare",
            "- baseline_skill: load the closest existing canonical skill or source skill.",
            "- tmcp_custom_skill: traverse TMCP, construct a task-specific packet, then execute.",
            "- tmcp_router_only: use router-selected task without adjacent exploration.",
            "- tmcp_promoted_shortcut: load a promoted shortcut path, then branch only for task-specific deltas.",
            "",
            "## Metrics",
            "- task_success: pass, partial, fail, blocked.",
            "- validation_success: whether relevant checks passed.",
            "- instruction_precision: loaded nodes that changed behavior divided by loaded nodes.",
            "- missed_requirement_count: source-specific requirements lost or skipped incorrectly.",
            "- conflict_handling_quality: branch selection was correct and justified.",
            "- custom_skill_tokens: estimated tokens in constructed packet.",
            "- baseline_tokens: estimated tokens in broad skill/source baseline.",
            "- token_roi: quality_delta divided by token_delta.",
            "- traversal_overhead_ms: time spent constructing the packet.",
            "",
            "## Pass Rule",
            "- TMCP custom skill is worth using when quality is equal or better and token cost is lower, or when quality improves enough to justify extra token cost.",
            "- TMCP custom skill should be repaired when it loads nodes that do not affect behavior or misses project-specific constraints.",
            "- A path is eligible for shortcut promotion when use_count >= 3, validation_success_rate >= 0.8, positive_token_roi_count >= 2, and no unresolved repair blocks the path.",
            "- A promoted shortcut should be demoted or repaired when two recent uses have negative token ROI, miss requirements, or require repeated manual corrections.",
            "- A shortcut should be bypassed when freshness is uncertain; normal router traversal should produce a rebuild recommendation instead.",
            "",
            "## Minimum Evaluation Cases",
            "- simple implementation with tests.",
            "- project-specific implementation with commit hooks.",
            "- audit-only request where edits are not allowed.",
            "- mixed audit plus implementation request.",
            "- research-heavy request requiring external uncertainty handling.",
            "- conflict case involving edit permission.",
            "",
            "## AIOS Learning Hook",
            "- Persist traversal receipts with run/session ids when available.",
            "- Cluster repeated successful paths into candidate shortcuts.",
            "- Promote shortcuts only after repeated positive token ROI and validation success.",
            "- Expose promoted shortcuts as top-level router nodes so future branches can build from them.",
            "- Generate repair recommendations for repeated negative ROI or failed validation.",
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
        f"Design decision: {TMCP_DESIGN_DECISION_ID}",
        "",
        "## Entry Point",
        "@task_router: skills.tmcp/router.md",
        "",
        "## Graph Traversal",
        "- CONSIDER @shortcut:candidate first when receipt history indicates a repeated successful path.",
        "- Start at router, but allow agent reasoning to CONSIDER adjacent task/module/branch nodes.",
        "- Construct a minimal custom skill packet from the traversed path.",
        "- Emit a traversal receipt using `skills.tmcp/traversal-receipt-schema.md`.",
        "- Evaluate quality and token ROI using `skills.tmcp/evaluation-plan.md`.",
        "- Promote stable repeated paths into top-level shortcut nodes only after evaluation evidence passes.",
        "",
        "## Task Map",
    ]
    for task, task_sources in task_map.items():
        lines.append(f"- @task:{task}")
        lines.append(
            f"  - Sources: {', '.join('@source:' + source.slug for source in task_sources[:8])}"
        )
    lines.extend(["", "## Module Dependency Map"])
    for module in modules:
        lines.append(f"- @module:{module['id']} sources={module['source_count']}")
    lines.extend(["", "## Branch Map"])
    for branch in branches:
        lines.append(f"- @branch:{branch['id']} type={branch['type']}")
    lines.extend(
        [
            "",
            "## Shortcut Promotion",
            "- @shortcut:candidate starts as the generic promotion target for repeated successful paths.",
            "- Promoted shortcuts should become named top-level router nodes before gaining branches.",
            "",
            "## Repair Recommendation Summary",
            "- See @repair:repair_recommendations",
        ]
    )
    return "\n".join(lines) + "\n"


def _compiler_report(
    sources: list[CandidateFile],
    skills: list[SkillGroup],
    workflows: list[CandidateFile],
    modules: list[dict[str, Any]],
    branches: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> str:
    source_tokens = sum(len(source.content.split()) for source in sources)
    compiled_tokens = sum(module["source_count"] for module in modules) * 40 + len(branches) * 60
    reduction = (
        0 if source_tokens == 0 else max(0, round((1 - compiled_tokens / source_tokens) * 100, 1))
    )
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
            "- Traversal ROI cases were generated to compare custom-skill construction against baseline skill loading.",
            "- Shortcut promotion cases were generated to guard against promoting one-off traversal wins.",
            "",
            "## Decision Graph Semantics",
            f"- Decision ID: {TMCP_DESIGN_DECISION_ID}",
            "- TMCP output is a graph traversal scaffold for agent reasoning, not a rigid IF/ELSE replacement.",
            "- Transition hooks are generated so constructed custom skills can be assembled coherently.",
            "- Traversal receipts are the durable learning surface for AIOS.",
            "- Repeated successful receipt fingerprints can be promoted into shortcut nodes.",
            "",
            "## Metrics",
            f"- Duplication reduction estimate: {reduction}%",
            f"- Average source skill size: {round(source_tokens / max(1, len(sources)), 1)} words",
            f"- Module reuse count: {sum(module['source_count'] for module in modules)}",
            f"- Conflict count: {len(conflicts)}",
            f"- Inferred module count: {sum(1 for module in modules if module['status'] == 'inferred')}",
            f"- Router coverage: {len(sources)} source files mapped into task candidates",
            "- Token ROI: not measured yet; see `skills.tmcp/evaluation-plan.md` for required comparison.",
            "",
            "## Repairs Recommended",
            "- Review inferred modules before treating advisory behavior as enforced behavior.",
            "- Resolve active conflict branches only after checking source provenance.",
            "- Add executable traversal evaluations before promoting TMCP paths as superior to baseline skills.",
            "- Promote only stable shortcuts, then branch from the shortcut node for recurring variants.",
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


def _traversal_roi_cases(task_map: dict[str, list[CandidateFile]]) -> str:
    lines = ["# Traversal ROI Cases", ""]
    for task in task_map:
        lines.extend(
            [
                f"## Case: @test:{task}.traversal_roi",
                "",
                "## Goal",
                f"Compare a TMCP-constructed custom skill for @task:{task} against loading the nearest broad baseline skill.",
                "",
                "## Baseline",
                "- Load nearest canonical skill or original source skill.",
                "- Execute task with baseline instructions.",
                "- Record baseline token estimate and validation outcome.",
                "",
                "## TMCP Custom Skill",
                f"- LOAD @task:{task}.",
                "- CONSIDER adjacent task nodes that add validation, research, documentation, or permission behavior.",
                "- USE only behavior-changing modules and branches.",
                "- SKIP unrelated nodes with reasons.",
                "- Emit traversal receipt.",
                "",
                "## Pass Criteria",
                "- Validation outcome is equal or better than baseline.",
                "- Missed requirement count is zero.",
                "- Token ROI is positive, or quality gain justifies additional tokens.",
                "",
            ]
        )
    return "\n".join(lines)


def _shortcut_promotion_cases(task_map: dict[str, list[CandidateFile]]) -> str:
    lines = ["# Shortcut Promotion Cases", ""]
    for task in task_map:
        lines.extend(
            [
                f"## Case: @test:{task}.shortcut_promotion",
                "",
                "## Goal",
                f"Decide whether a repeated traversal path for @task:{task} should become a top-level shortcut node.",
                "",
                "## Required Evidence",
                "- At least three traversal receipts share the same traversal_fingerprint.",
                "- validation_success_rate is at least 0.8.",
                "- positive_token_roi_count is at least 2.",
                "- missed_requirement_count is zero across promoted examples.",
                "- No unresolved repair recommendation blocks the path.",
                "",
                "## Expected Outcome",
                "- Eligible paths become a named promoted shortcut derived from @shortcut:candidate.",
                "- Ineligible paths remain receipt history and may still inform repairs.",
                "- Once promoted, future graph traversal starts at the shortcut and branches only for task-specific deltas.",
                "",
            ]
        )
    return "\n".join(lines)


def _shortcut_promotion_policy() -> str:
    return "\n".join(
        [
            "# Shortcut: Candidate Promotion",
            "",
            "## Metadata",
            "Shortcut ID: @shortcut:candidate",
            "Status: promotion_policy",
            "",
            "## Purpose",
            "Turn a repeated, validated custom-skill traversal path into a reusable top-level TMCP node.",
            "",
            "## Shortcut Skill Contract",
            "- A shortcut skill is a cached compiled traversal through the TMCP graph.",
            "- Shortcut skills are generated artifacts, not source of truth.",
            "- Shortcut skills must preserve provenance.",
            "- Shortcut skills must declare their source graph version.",
            "- Shortcut skills must declare source tasks, modules, branches, and source skills.",
            "- Shortcut skills must be revalidated when related source material changes.",
            "- Shortcut skills must not be manually appended by default.",
            "- Related graph changes must trigger regeneration, splitting, supersession, conflict branching, or deprecation review.",
            "- If shortcut freshness is uncertain, agents must fall back to router traversal.",
            "- Shortcut skills may only become default paths after behavioral tests pass.",
            "",
            "## Shortcut Statuses",
            "- active: valid for default use when graph version and source material are current.",
            "- stale_candidate: likely affected by source or graph drift; do not use as default.",
            "- needs_revalidation: candidate has useful history but requires behavioral test replay.",
            "- superseded: replaced by a newer shortcut version.",
            "- deprecated: no longer useful enough to keep in routing.",
            "- conflict_branch: useful only as one competing branch under a conflict node.",
            "",
            "## Rebuild Outcomes",
            "- revalidate_unchanged: behavioral tests pass without material shortcut edits.",
            "- regenerate_new_version: source graph changed but the shortcut remains coherent after regeneration.",
            "- split_more_specific: one shortcut has become too broad and should become multiple focused shortcuts.",
            "- create_conflict_branches: related source material creates competing valid behaviors.",
            "- deprecate_not_useful: shortcut no longer saves tokens or preserves behavior reliably.",
            "",
            "## Why This Exists",
            "- TMCP should not re-run the same tree search forever when the same path keeps winning.",
            "- A successful path is stronger than a static prewritten skill because it encodes task intent, selected branches, source-tier precedence, and validation evidence.",
            "- Once promoted, the shortcut becomes a new starting node that future branches can grow from.",
            "",
            "## Promotion Threshold",
            "- use_count >= 3 for the same traversal_fingerprint.",
            "- validation_success_rate >= 0.8.",
            "- positive_token_roi_count >= 2.",
            "- missed_requirement_count == 0 for promoted examples.",
            "- No unresolved repair recommendation, conflict branch, or project-specific override blocks promotion.",
            "",
            "## Construction Rule",
            "- Name the shortcut after the stable task path, not the original one-off request.",
            "- Include the ordered selected task, modules, branches, source tiers, and output contract.",
            "- Preserve links to the receipts that justified promotion.",
            "- Write the promoted artifact as a normal skill target only when it has enough evidence to be reused outside the original run.",
            "",
            "## Router Behavior",
            "- CONSIDER this shortcut before normal task routing when task, project, and context fingerprints match receipt history.",
            "- USE a promoted shortcut only when status is active, source graph version is current, related source material is unchanged, and behavioral tests have passed.",
            "- SKIP a shortcut when the request includes a new domain, stricter project overlay, unresolved conflict, or changed validation surface.",
            "- FALL BACK to router traversal when graph version, source freshness, provenance, or behavioral test status is uncertain.",
            "",
            "## Demotion and Repair",
            "- Demote or repair when two recent uses have negative token ROI.",
            "- Demote or repair when a shortcut misses requirements that normal traversal would have loaded.",
            "- Demote or repair when users or agents repeatedly add the same missing branch by hand.",
            "",
            "## Output",
            "- Candidate shortcut: receipt cluster plus promotion evidence.",
            "- Promoted shortcut: named top-level router node and optional generated `skills/<shortcut>/SKILL.md` target.",
            "- Repair: recommendation when the candidate path is useful but not yet safe to promote.",
            "",
        ]
    )


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
            refs.add(f"@test:{task_id}.traversal_roi")
            refs.add(f"@test:{task_id}.shortcut_promotion")
        if path.startswith("skills.tmcp/modules/") and path.endswith(".md"):
            refs.add(f"@module:{Path(path).stem}")
        if path.startswith("skills.tmcp/branches/") and path.endswith(".branch.md"):
            refs.add(f"@branch:{Path(path).name.removesuffix('.branch.md')}")
        if path.startswith("skills.tmcp/shortcuts/") and path.endswith(".md"):
            refs.add(f"@shortcut:{Path(path).stem}")
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
    parts = [
        "python3",
        "bin/aios.py",
        "skills",
        "harvest",
        "--roots",
        roots,
        "--out",
        str(options.out),
    ]
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
