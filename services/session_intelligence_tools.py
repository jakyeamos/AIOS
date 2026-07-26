from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

JSONDict = dict[str, object]

ROOT_MARKERS = (
    "AGENTS.md",
    "README.md",
    "pyproject.toml",
    "package.json",
    "pnpm-lock.yaml",
    "uv.lock",
    ".planning/STATE.md",
)


def _run(args: list[str], *, cwd: Path, timeout: float = 5.0) -> JSONDict:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stdout": "", "stderr": f"missing: {args[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": 124, "stdout": "", "stderr": "timed out"}
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _stdout(result: JSONDict) -> str:
    value = result.get("stdout")
    return value if isinstance(value, str) else ""


def _git(repo: Path, *args: str) -> JSONDict:
    return _run(["git", *args], cwd=repo)


def _git_root(repo: Path) -> Path:
    result = _git(repo, "rev-parse", "--show-toplevel")
    stdout = _stdout(result)
    if result.get("ok") and stdout:
        return Path(stdout).resolve()
    return repo.resolve()


def _load_package(repo: Path) -> JSONDict:
    package_path = repo / "package.json"
    if not package_path.exists():
        return {}
    try:
        loaded = json.loads(package_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"invalid": True}
    return loaded if isinstance(loaded, dict) else {"invalid": True}


def _package_manager(repo: Path, package: JSONDict) -> str | None:
    package_manager = package.get("packageManager")
    if isinstance(package_manager, str) and package_manager:
        return package_manager.split("@", 1)[0]
    if (repo / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo / "yarn.lock").exists():
        return "yarn"
    if (repo / "package-lock.json").exists():
        return "npm"
    return "pnpm" if package else None


def _root_markers(repo: Path) -> list[str]:
    return [marker for marker in ROOT_MARKERS if (repo / marker).exists()]


def _status_lines(repo: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line]


def _recent_commits(repo: Path, *, limit: int = 5) -> list[JSONDict]:
    result = _git(repo, "log", "--oneline", f"-{limit}")
    commits: list[JSONDict] = []
    for line in _stdout(result).splitlines():
        if not line.strip():
            continue
        sha, _, title = line.partition(" ")
        commits.append({"sha": sha, "title": title})
    return commits


def _current_branch(repo: Path) -> str | None:
    result = _git(repo, "branch", "--show-current")
    branch = _stdout(result)
    return branch or None


def _head_sha(repo: Path) -> str | None:
    result = _git(repo, "rev-parse", "HEAD")
    head = _stdout(result)
    return head or None


def _diff_stat_lines(repo: Path) -> list[str]:
    result = _git(repo, "diff", "--stat")
    return [line.strip() for line in _stdout(result).splitlines() if line.strip()]


def _remote_names(repo: Path) -> list[str]:
    result = _git(repo, "remote")
    return [line for line in _stdout(result).splitlines() if line]


def repo_inspect_payload(repo_path: str | Path, *, include_processes: bool = False) -> JSONDict:
    repo = _git_root(Path(repo_path).expanduser().resolve())
    git_probe = _git(repo, "rev-parse", "--is-inside-work-tree")
    is_repo = bool(git_probe.get("ok"))
    status = _status_lines(repo) if is_repo else []
    package = _load_package(repo)
    raw_scripts = package.get("scripts")
    scripts: dict[str, object] = raw_scripts if isinstance(raw_scripts, dict) else {}
    root_markers = _root_markers(repo)
    payload: JSONDict = {
        "schema": "aios-repo-inspect-v0.1",
        "repo": {"root": str(repo), "exists": repo.exists()},
        "git": {
            "is_repo": is_repo,
            "branch": _current_branch(repo) if is_repo else None,
            "dirty": bool(status),
            "status_short": status[:50],
            "recent_commits": _recent_commits(repo) if is_repo else [],
            "remotes": _remote_names(repo) if is_repo else [],
        },
        "package": {
            "has_package_json": bool(package),
            "manager": _package_manager(repo, package),
            "scripts": sorted(str(key) for key in scripts),
        },
        "files": {
            "root_markers": root_markers,
            "has_python": (repo / "pyproject.toml").exists(),
            "has_javascript": bool(package),
        },
        "recommendations": [
            {
                "tool": "aios quality ladder",
                "reason": "Plan project-aware verification commands before edits or closeout.",
            },
            {
                "tool": "aios ship guard",
                "reason": "Check branch, cleanliness, and review-gated publish readiness.",
            },
        ],
    }
    if include_processes:
        payload["local_services"] = service_probe_payload()
    return payload


def repo_closeout_payload(repo_path: str | Path, *, commit_limit: int = 5) -> JSONDict:
    repo = _git_root(Path(repo_path).expanduser().resolve())
    git_probe = _git(repo, "rev-parse", "--is-inside-work-tree")
    is_repo = bool(git_probe.get("ok"))
    status = _status_lines(repo) if is_repo else []
    bounded_limit = max(1, min(commit_limit, 20))
    return {
        "schema": "aios-repo-closeout-v0.1",
        "repo": str(repo),
        "git": {
            "is_repo": is_repo,
            "branch": _current_branch(repo) if is_repo else None,
            "head": _head_sha(repo) if is_repo else None,
            "dirty": bool(status),
            "dirty_files": status,
            "recent_commits": _recent_commits(repo, limit=bounded_limit) if is_repo else [],
        },
        "diff_stat": {
            "lines": _diff_stat_lines(repo) if is_repo else [],
        },
    }


def quality_ladder_payload(repo_path: str | Path, *, profile: str = "auto") -> JSONDict:
    repo = Path(repo_path).expanduser().resolve()
    package = _load_package(repo)
    raw_scripts = package.get("scripts")
    scripts: dict[str, object] = raw_scripts if isinstance(raw_scripts, dict) else {}
    has_python = (repo / "pyproject.toml").exists() or (repo / "tests").exists()
    has_js = bool(package)
    effective_profile = profile
    if profile == "auto":
        if has_python and has_js:
            effective_profile = "mixed"
        elif has_python:
            effective_profile = "python"
        elif has_js:
            effective_profile = "javascript"
        else:
            effective_profile = "generic"

    steps: list[JSONDict] = []
    if effective_profile in {"python", "mixed"}:
        steps.extend(
            [
                {"id": "python-lint", "command": "uv run ruff check .", "required": True},
                {
                    "id": "python-format",
                    "command": "uv run ruff format --check .",
                    "required": True,
                },
                {"id": "python-types", "command": "uv run basedpyright", "required": True},
                {
                    "id": "python-dead-code",
                    "command": "uv run vulture . --min-confidence 70",
                    "required": False,
                },
                {"id": "python-tests", "command": "uv run pytest -q", "required": True},
            ]
        )
    if effective_profile in {"javascript", "mixed"}:
        for script_name in ("lint", "typecheck", "test", "audit:dead-code", "build"):
            if script_name in scripts:
                steps.append(
                    {
                        "id": f"js-{script_name}",
                        "command": f"pnpm {script_name}",
                        "required": script_name in {"lint", "typecheck", "test"},
                    }
                )
    if not steps:
        steps.append(
            {
                "id": "manual-quality",
                "command": "inspect project docs for canonical quality commands",
                "required": True,
            }
        )
    return {
        "schema": "aios-quality-ladder-plan-v0.1",
        "repo": str(repo),
        "profile": effective_profile,
        "execution": {
            "mode": "plan_only",
            "review_gated": True,
            "runs_commands": False,
        },
        "steps": steps,
    }


def ship_guard_payload(repo_path: str | Path) -> JSONDict:
    repo = _git_root(Path(repo_path).expanduser().resolve())
    inspect_payload = repo_inspect_payload(repo)
    git_info = inspect_payload["git"]
    git_dict = git_info if isinstance(git_info, dict) else {}
    branch = git_dict.get("branch")
    status = git_dict.get("status_short")
    status_lines = status if isinstance(status, list) else []
    blockers: list[str] = []
    warnings: list[str] = []
    if not git_dict.get("is_repo"):
        blockers.append("target is not a git repository")
    if status_lines:
        blockers.append("working tree has uncommitted changes")
    if branch in {"main", "master"}:
        blockers.append("current branch is protected release branch")
    if not git_dict.get("remotes"):
        warnings.append("no git remotes configured")
    return {
        "schema": "aios-ship-guard-v0.1",
        "repo": str(repo),
        "review_gate": {
            "requires_explicit_action": True,
            "does_not_commit": True,
            "does_not_push": True,
        },
        "decision": {
            "ready": not blockers,
            "blockers": blockers,
            "warnings": warnings,
        },
        "proposed_actions": [
            "review repo inspect output",
            "run planned quality ladder",
            "stage only intended files",
            "commit a coherent change set",
            "push after explicit approval",
        ],
    }


def _port_listening(port: int, *, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        return probe.connect_ex((host, port)) == 0


def _process_matches(name: str) -> list[str]:
    result = _run(["pgrep", "-fl", name], cwd=Path.cwd())
    if not result.get("ok"):
        return []
    return [line for line in _stdout(result).splitlines() if line]


def service_probe_payload(
    *,
    ports: list[int] | None = None,
    names: list[str] | None = None,
) -> JSONDict:
    selected_ports = ports if ports is not None else [3000, 5173, 8000, 8080]
    selected_names = names if names is not None else []
    probes: list[JSONDict] = []
    for port in selected_ports:
        probes.append(
            {
                "kind": "tcp_port",
                "port": port,
                "host": "127.0.0.1",
                "listening": _port_listening(port),
            }
        )
    for name in selected_names:
        matches = _process_matches(name)
        probes.append(
            {
                "kind": "process_name",
                "name": name,
                "running": bool(matches),
                "matches": matches[:20],
            }
        )
    return {
        "schema": "aios-service-probe-v0.1",
        "review_gate": {"read_only": True},
        "probes": probes,
    }


def codex_workflow_skill_payload() -> JSONDict:
    return {
        "schema": "aios-codex-workflow-skill-v0.1",
        "promotion": {
            "review_gated": True,
            "writes_skill_file": False,
            "approved_candidate_lane": "workflow_skill",
        },
        "skill": {
            "name": "codex-tier-one-delivery",
            "summary": "Repeatable Codex delivery loop promoted from successful session patterns.",
            "steps": [
                {
                    "name": "orient",
                    "actions": [
                        "read user request and newest thread context",
                        "run repo inspection before editing",
                        "identify dirty worktree boundaries",
                    ],
                },
                {
                    "name": "implement",
                    "actions": [
                        "make scoped edits",
                        "preserve review gates",
                        "avoid unrelated cleanup",
                    ],
                },
                {
                    "name": "verify",
                    "actions": [
                        "run targeted checks while iterating",
                        "run the quality ladder before closeout",
                        "surface baseline failures explicitly",
                    ],
                },
                {
                    "name": "closeout",
                    "actions": [
                        "commit coherent work after explicit review gate",
                    ],
                },
            ],
        },
    }


def _frontmatter_value(text: str, key: str) -> str | None:
    prefix = f"{key}:"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.split(":", 1)[1].strip().strip("\"'")
    return None


def planning_state_payload(repo_path: str | Path) -> JSONDict:
    repo = Path(repo_path).expanduser().resolve()
    planning_path = repo / ".planning"
    state_path = planning_path / "STATE.md"
    markers = [
        str(path.relative_to(repo))
        for path in (state_path, repo / ".planning" / "ROADMAP.md")
        if path.exists()
    ]
    blockers: list[str] = []
    return {
        "schema": "aios-planning-state-v0.1",
        "repo": str(repo),
        "state": {
            "exists": state_path.exists(),
            "path": str(state_path),
            "summary": _frontmatter_value(
                state_path.read_text(encoding="utf-8") if state_path.exists() else "", "summary"
            ),
            "next_step": _frontmatter_value(
                state_path.read_text(encoding="utf-8") if state_path.exists() else "", "nextStep"
            ),
            "last_updated": _frontmatter_value(
                state_path.read_text(encoding="utf-8") if state_path.exists() else "", "lastUpdated"
            ),
        },
        "planning": {
            "exists": planning_path.exists(),
            "markers": markers,
        },
        "decision": {
            "ready_for_agent_work": not blockers,
            "blockers": blockers,
        },
    }
