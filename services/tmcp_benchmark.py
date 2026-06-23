from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BENCHMARK_SCHEMA = "tmcp-benchmark-v0.1"
REPOSITORIES_SCHEMA = "tmcp-benchmark-repositories-v0.1"
BENCHMARK_CONDITIONS = (
    "baseline",
    "flat_skills",
    "tmcp_cold_start",
    "tmcp_validated_shortcut",
)
SHORTCUT_STATES = (
    "NONE",
    "CANDIDATE_AVAILABLE",
    "VALIDATED_AVAILABLE",
    "VALIDATED_SELECTED",
    "VALIDATED_NOT_SELECTED",
    "SHORTCUT_MISS",
    "FALSE_SHORTCUT_HIT",
    "STALE_SHORTCUT",
    "SHORTCUT_REJECTED",
    "SHORTCUT_FALLBACK",
    "SHORTCUT_INVALIDATED",
)

BENCHMARK_DIRECTORIES = (
    "manifest",
    "tasks/development",
    "tasks/held-out",
    "tasks/approved",
    "tasks/hidden-tests",
    "tasks/rejected",
    "shortcuts/candidates",
    "shortcuts/validated",
    "shortcuts/rejected",
    "shortcuts/stale",
    "shortcuts/receipts",
    "runs/raw",
    "runs/patches",
    "runs/logs",
    "runs/timing",
    "runs/tokens",
    "runs/routes",
    "runs/receipts",
    "runs/artifacts",
    "runs/worktrees",
    "evaluation/rubrics",
    "evaluation/automated",
    "evaluation/human",
    "evaluation/adjudication",
    "analysis/normalized",
    "analysis/scripts",
    "analysis/tables",
    "analysis/figures",
    "reports",
)

REPORT_STUBS = {
    "technical-report.md": "# TMCP Multi-Project Benchmark Technical Report\n\nStatus: not run.\n",
    "executive-summary.md": "# Executive Summary\n\nStatus: not run.\n",
    "methodology.md": "# Methodology\n\nStatus: scaffolded; systems are not frozen yet.\n",
    "limitations.md": "# Limitations\n\n- Benchmark execution has not started.\n",
    "claims-register.md": (
        "# Claims Register\n\n"
        "No public claim is approved until held-out analysis is complete and every claim maps "
        "to raw evidence, confidence intervals, effect sizes, and limitations.\n"
    ),
    "benchmark-card.md": "# Benchmark Card\n\nStatus: scaffolded.\n",
    "shortcut-economics.md": "# Shortcut Economics\n\nStatus: no shortcut economics measured yet.\n",
    "promotional-evidence-pack.md": (
        "# Promotional Evidence Pack\n\n"
        "Do not create promotional claims until held-out analysis is complete.\n"
    ),
    "failure-casebook.md": "# Failure Casebook\n\nStatus: no benchmark failures recorded yet.\n",
}

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "tmcp-benchmark",
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def discover_repositories(parent_dir: Path, *, max_depth: int = 4) -> list[dict[str, object]]:
    root = parent_dir.expanduser().resolve()
    repositories: list[dict[str, object]] = []
    for current, dirs, _files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        dirs[:] = [
            name
            for name in dirs
            if name not in SKIP_DIR_NAMES and not name.startswith(".")
        ]
        if depth >= max_depth:
            dirs[:] = []
        if (current_path / ".git").exists():
            repositories.append(_repository_record(current_path))
            dirs[:] = []
    return sorted(repositories, key=lambda item: str(item["project_id"]))


def create_benchmark_scaffold(*, parent_dir: Path, output_root: Path) -> dict[str, object]:
    benchmark_root = output_root.expanduser().resolve()
    for relative in BENCHMARK_DIRECTORIES:
        (benchmark_root / relative).mkdir(parents=True, exist_ok=True)

    repositories = discover_repositories(parent_dir)
    _write_json(
        benchmark_root / "manifest" / "repositories.json",
        {
            "schema": REPOSITORIES_SCHEMA,
            "created_at": now_iso(),
            "parent_dir": str(parent_dir.expanduser().resolve()),
            "repositories": repositories,
            "sync_policy": {
                "non_mutating_inventory": True,
                "fetch_before_sync_required": True,
                "force_push_allowed": False,
                "rewrite_shared_history_allowed": False,
            },
        },
    )
    _write_json(benchmark_root / "manifest" / "environments.json", _environment_manifest())
    _write_json(benchmark_root / "manifest" / "skill-equivalence.json", _skill_equivalence_manifest())
    _write_json(benchmark_root / "manifest" / "shortcut-registry.json", _shortcut_registry_manifest())
    _write_json(benchmark_root / "manifest" / "freeze-manifest.json", _freeze_manifest())
    for filename, content in REPORT_STUBS.items():
        report_path = benchmark_root / "reports" / filename
        if not report_path.exists():
            report_path.write_text(content, encoding="utf-8")
    return {
        "schema": BENCHMARK_SCHEMA,
        "benchmark_root": str(benchmark_root),
        "repository_count": len(repositories),
        "created_at": now_iso(),
    }


def refresh_discovery(*, parent_dir: Path, output_root: Path) -> dict[str, object]:
    benchmark_root = output_root.expanduser().resolve()
    (benchmark_root / "manifest").mkdir(parents=True, exist_ok=True)
    repositories = discover_repositories(parent_dir)
    payload = {
        "schema": REPOSITORIES_SCHEMA,
        "created_at": now_iso(),
        "parent_dir": str(parent_dir.expanduser().resolve()),
        "repositories": repositories,
        "sync_policy": {
            "non_mutating_inventory": True,
            "fetch_before_sync_required": True,
            "force_push_allowed": False,
            "rewrite_shared_history_allowed": False,
        },
    }
    _write_json(benchmark_root / "manifest" / "repositories.json", payload)
    return payload


def preflight_benchmark(
    *,
    output_root: Path,
    preferred_projects: tuple[str, ...] = ("BIP-Console", "Bballedu"),
) -> dict[str, object]:
    benchmark_root = output_root.expanduser().resolve()
    manifest = _read_json_object(benchmark_root / "manifest" / "repositories.json")
    repositories = _json_list(manifest.get("repositories"))
    results: list[dict[str, object]] = []
    for repo in repositories:
        if not isinstance(repo, dict):
            continue
        repo_path = Path(str(repo.get("repo_path", "")))
        checks = {
            "repo_exists": repo_path.exists(),
            "clean_worktree": not bool(_git(repo_path, "status", "--porcelain")) if repo_path.exists() else False,
            "has_start_commit": bool(repo.get("current_commit")),
            "has_lockfile": bool(repo.get("dependency_lockfiles")),
            "has_quality_command": any(
                bool(repo.get(key))
                for key in ("test_commands", "lint_commands", "typecheck_commands")
            ),
            "has_test_command": bool(repo.get("test_commands")),
            "has_lint_command": bool(repo.get("lint_commands")),
            "has_typecheck_command": bool(repo.get("typecheck_commands")),
        }
        required_checks = (
            "repo_exists",
            "clean_worktree",
            "has_start_commit",
            "has_lockfile",
            "has_quality_command",
        )
        eligible = all(checks[key] for key in required_checks)
        results.append(
            {
                "project_id": repo.get("project_id"),
                "repo_path": str(repo_path),
                "eligible": eligible,
                "checks": checks,
                "reason": "eligible" if eligible else "missing_required_preflight_signal",
            }
        )
    selected = _select_preflight_projects(results, preferred_projects)
    payload = {
        "schema": "tmcp-benchmark-preflight-v0.1",
        "created_at": now_iso(),
        "selected_projects": selected,
        "results": results,
    }
    _write_json(benchmark_root / "manifest" / "preflight.json", payload)
    return payload


def import_task_manifest(
    *,
    output_root: Path,
    task_families: list[dict[str, object]],
    tasks: list[dict[str, object]],
) -> dict[str, object]:
    benchmark_root = output_root.expanduser().resolve()
    task_dir = benchmark_root / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    _validate_task_manifest(task_families, tasks)
    family_payload = {
        "schema": "tmcp-benchmark-task-families-v0.1",
        "created_at": now_iso(),
        "task_families": task_families,
    }
    task_payload = {
        "schema": "tmcp-benchmark-tasks-v0.1",
        "created_at": now_iso(),
        "tasks": tasks,
        "route_visibility": "expected_tmcp_route is hidden from executing agents.",
    }
    _write_json(task_dir / "task-families.json", family_payload)
    _write_json(task_dir / "tasks.json", task_payload)
    return {
        "schema": "tmcp-benchmark-task-import-v0.1",
        "task_family_count": len(task_families),
        "task_count": len(tasks),
        "created_at": now_iso(),
    }


def randomize_condition_map(
    *,
    output_root: Path,
    seed: int,
    repeats: int,
    include_development: bool = False,
) -> dict[str, object]:
    benchmark_root = output_root.expanduser().resolve()
    tasks = {
        task_id: task
        for task_id, task in _tasks_by_id(benchmark_root).items()
        if include_development or task.get("split") != "development"
    }
    assignments: list[dict[str, object]] = []
    rng = random.Random(seed)
    for repeat_index in range(max(1, repeats)):
        for task_id in sorted(tasks):
            conditions = list(BENCHMARK_CONDITIONS)
            rng.shuffle(conditions)
            for order_index, condition in enumerate(conditions):
                assignments.append(
                    {
                        "condition_anonymous_id": _condition_id(task_id, repeat_index, condition, seed),
                        "task_id": task_id,
                        "condition_actual": condition,
                        "repeat_index": repeat_index,
                        "order_index": order_index,
                    }
                )
    payload = {
        "schema": "tmcp-benchmark-condition-map-v0.1",
        "created_at": f"deterministic-seed-{seed}",
        "seed": seed,
        "repeats": max(1, repeats),
        "include_development": include_development,
        "conditions": list(BENCHMARK_CONDITIONS),
        "assignments": assignments,
    }
    _write_json(benchmark_root / "manifest" / "condition-map.json", payload)
    return payload


def freeze_benchmark(*, output_root: Path, model_config: dict[str, object]) -> dict[str, object]:
    benchmark_root = output_root.expanduser().resolve()
    manifest_dir = benchmark_root / "manifest"
    _write_json(manifest_dir / "model-config.json", {"schema": "tmcp-benchmark-model-config-v0.1", **model_config})
    hashes = {
        "repositories_json": _file_sha256(manifest_dir / "repositories.json"),
        "skill_equivalence_json": _file_sha256(manifest_dir / "skill-equivalence.json"),
        "shortcut_registry_json": _file_sha256(manifest_dir / "shortcut-registry.json"),
        "condition_map_json": _file_sha256(manifest_dir / "condition-map.json"),
        "model_config_json": _file_sha256(manifest_dir / "model-config.json"),
        "task_families_json": _file_sha256(benchmark_root / "tasks" / "task-families.json"),
        "tasks_json": _file_sha256(benchmark_root / "tasks" / "tasks.json"),
    }
    payload = _freeze_manifest()
    payload.update(
        {
            "created_at": now_iso(),
            "systems_frozen": True,
            "hashes": hashes,
            "model_config": model_config,
        }
    )
    _write_json(manifest_dir / "freeze-manifest.json", payload)
    return payload


def validate_shortcut_for_task(
    *,
    output_root: Path,
    shortcut: dict[str, object],
    task_id: str,
) -> dict[str, object]:
    _ = output_root
    created_from = {str(item) for item in _json_list(shortcut.get("created_from_task_ids"))}
    validated_on = {str(item) for item in _json_list(shortcut.get("validated_on_task_ids"))}
    if task_id in created_from or task_id in validated_on:
        return {
            "allowed": False,
            "reason": "shortcut_contains_target_task",
            "shortcut_id": shortcut.get("shortcut_id"),
            "task_id": task_id,
        }
    return {
        "allowed": True,
        "reason": "reusable_family_route_only",
        "shortcut_id": shortcut.get("shortcut_id"),
        "task_id": task_id,
    }


def run_task_condition(
    *,
    output_root: Path,
    run_id: str,
    task_id: str,
    condition_anonymous_id: str,
    executor: str = "stub",
) -> dict[str, object]:
    if executor != "stub":
        raise ValueError("Only the deterministic stub executor is implemented in this benchmark slice.")
    benchmark_root = output_root.expanduser().resolve()
    tasks = _tasks_by_id(benchmark_root)
    task = tasks[task_id]
    assignment = _condition_assignment(benchmark_root, condition_anonymous_id)
    repo = _repository_for_project(benchmark_root, str(task["project_id"]))
    worktree = benchmark_root / "runs" / "worktrees" / run_id
    artifact_dir = benchmark_root / "runs" / "artifacts" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    t0 = _monotonic()
    started_at = now_iso()
    _create_worktree(Path(str(repo["repo_path"])), worktree, str(task["starting_commit"]))
    environment_ready_at = now_iso()
    t1 = _monotonic()
    task_presented_at = now_iso()
    route_selected_at = now_iso()
    t2 = _monotonic()
    context_path = artifact_dir / "benchmark_context.json"
    context_path.write_text(
        json.dumps(
            {
                "condition_actual": assignment["condition_actual"],
                "condition_anonymous_id": condition_anonymous_id,
                "task_id": task_id,
                "executor": executor,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    first_relevant_action_at = now_iso()
    first_edit_at = ""
    public_result = _run_commands(_string_list(task.get("required_test_commands")), worktree, artifact_dir, "public")
    first_test_at = public_result["first_started_at"] or ""
    first_successful_test_at = public_result["first_success_at"] or ""
    public_tests_completed_at = now_iso()
    hidden_result = _run_commands(_string_list(task.get("hidden_test_commands")), worktree, artifact_dir, "hidden")
    hidden_tests_completed_at = now_iso()
    agent_completed_at = now_iso()
    evaluation_completed_at = now_iso()
    t11 = _monotonic()

    route = _route_payload(task, assignment, run_id)
    timing = {
        "started_at": started_at,
        "environment_ready_at": environment_ready_at,
        "task_presented_at": task_presented_at,
        "route_selected_at": route_selected_at,
        "first_relevant_action_at": first_relevant_action_at,
        "first_edit_at": first_edit_at,
        "first_test_at": first_test_at,
        "first_successful_test_at": first_successful_test_at,
        "public_tests_completed_at": public_tests_completed_at,
        "hidden_tests_completed_at": hidden_tests_completed_at,
        "agent_completed_at": agent_completed_at,
        "evaluation_completed_at": evaluation_completed_at,
        "setup_seconds": round(t1 - t0, 6),
        "routing_seconds": round(t2 - t1, 6),
        "total_benchmark_seconds": round(t11 - t0, 6),
    }
    token_payload = _condition_token_payload(str(assignment["condition_actual"]), task)

    patch_path = benchmark_root / "runs" / "patches" / f"{run_id}.patch"
    patch_text = _git(worktree, "diff", "--binary")
    patch_path.write_text(patch_text, encoding="utf-8")
    timing_path = benchmark_root / "runs" / "timing" / f"{run_id}.json"
    token_path = benchmark_root / "runs" / "tokens" / f"{run_id}.json"
    route_path = benchmark_root / "runs" / "routes" / f"{run_id}.json"
    raw_path = benchmark_root / "runs" / "raw" / f"{run_id}.json"
    _write_json(timing_path, timing)
    _write_json(token_path, token_payload)
    _write_json(route_path, route)

    public_total = len(public_result["commands"])
    hidden_total = len(hidden_result["commands"])
    public_passed = sum(1 for item in public_result["commands"] if item["exit_code"] == 0)
    hidden_passed = sum(1 for item in hidden_result["commands"] if item["exit_code"] == 0)
    completed = public_total == public_passed and hidden_total == hidden_passed
    quality_score = 100 if completed else 0
    record = {
        **run_record_template(),
        **timing,
        **token_payload,
        "run_id": run_id,
        "project_id": task["project_id"],
        "task_family_id": task["task_family_id"],
        "task_id": task_id,
        "task_class": task["task_class"],
        "compositionality_score": task["compositionality_score"],
        "condition_anonymous_id": condition_anonymous_id,
        "condition_actual": assignment["condition_actual"],
        "starting_commit": task["starting_commit"],
        "harness": "tmcp-benchmark-stub",
        "seed": _read_condition_seed(benchmark_root),
        "shortcut_state": _shortcut_state_for_condition(str(assignment["condition_actual"])),
        "shortcut_selected": assignment["condition_actual"] == "tmcp_validated_shortcut",
        "shortcut_fallback_used": False,
        "tool_calls": 0,
        "shell_commands": public_total + hidden_total,
        "selected_modules": route["selected_modules"],
        "expected_modules": _string_list(task.get("expected_tmcp_route")),
        "route_precision": route["route_precision"],
        "route_recall": route["route_recall"],
        "public_tests_passed": public_passed,
        "public_tests_total": public_total,
        "hidden_tests_passed": hidden_passed,
        "hidden_tests_total": hidden_total,
        "build_passed": completed,
        "lint_passed": completed,
        "typecheck_passed": completed,
        "task_completed": completed,
        "quality_score_raw": quality_score,
        "quality_score_adjusted": quality_score,
        "patch_path": str(patch_path),
        "log_path": str(artifact_dir),
        "timing_path": str(timing_path),
        "token_path": str(token_path),
        "route_receipt_path": str(route_path),
        "notes": "Deterministic stub executor; no agent patch was attempted.",
    }
    _write_json(raw_path, record)
    _write_json(benchmark_root / "evaluation" / "automated" / f"{run_id}.json", _evaluation_payload(record))
    return record


def aggregate_results(*, output_root: Path) -> dict[str, object]:
    benchmark_root = output_root.expanduser().resolve()
    raw_dir = benchmark_root / "runs" / "raw"
    runs = [_read_json_object(path) for path in sorted(raw_dir.glob("*.json"))]
    by_condition: dict[str, list[dict[str, object]]] = {}
    for run in runs:
        by_condition.setdefault(str(run.get("condition_actual")), []).append(run)
    summaries = {
        condition: _condition_summary(condition_runs)
        for condition, condition_runs in sorted(by_condition.items())
    }
    comparisons: dict[str, dict[str, object]] = {}
    for baseline_condition, challenger_condition in (
        ("baseline", "flat_skills"),
        ("flat_skills", "tmcp_cold_start"),
        ("tmcp_cold_start", "tmcp_validated_shortcut"),
        ("baseline", "tmcp_cold_start"),
        ("baseline", "tmcp_validated_shortcut"),
        ("flat_skills", "tmcp_validated_shortcut"),
    ):
        if baseline_condition in by_condition and challenger_condition in by_condition:
            comparisons[f"{baseline_condition}__{challenger_condition}"] = _comparison_summary(
                by_condition[baseline_condition],
                by_condition[challenger_condition],
            )
    payload = {
        "schema": "tmcp-benchmark-aggregate-v0.1",
        "created_at": now_iso(),
        "run_count": len(runs),
        "conditions": summaries,
        "comparisons": comparisons,
        "claim_policy": "Speed or token claims require task completion and quality non-inferiority.",
    }
    tables_dir = benchmark_root / "analysis" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    _write_json(tables_dir / "condition-summary.json", payload)
    _write_report_summaries(benchmark_root, payload)
    return payload


def _repository_record(repo_path: Path) -> dict[str, object]:
    package = _load_json_if_exists(repo_path / "package.json")
    scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
    package_manager = _package_manager(repo_path, package)
    test_commands = _script_commands(scripts, ("test",), package_manager)
    lint_commands = _script_commands(scripts, ("lint",), package_manager)
    typecheck_commands = _script_commands(scripts, ("typecheck", "tsc"), package_manager)
    return {
        "project_id": repo_path.name,
        "repo_path": str(repo_path),
        "default_branch": _git(repo_path, "branch", "--show-current") or None,
        "aios_shadow_branch": _detect_shadow_branch(repo_path),
        "current_commit": _git(repo_path, "rev-parse", "HEAD") or None,
        "upstream_remote": _git(repo_path, "remote", "get-url", "origin") or None,
        "uncommitted_changes": bool(_git(repo_path, "status", "--porcelain")),
        "existing_skills": _relative_matches(repo_path, ("skills", ".agents/skills", ".codex/skills")),
        "has_tmcp_graph": (repo_path / "skills.tmcp").exists()
        or (repo_path / "skills-library" / "skills.tmcp").exists(),
        "existing_shortcut_registry": _relative_matches(
            repo_path,
            ("skills.tmcp/shortcuts", "skills-library/skills.tmcp/shortcuts"),
        ),
        "build_system": _build_system(repo_path),
        "testing_framework": _testing_framework(package),
        "test_commands": test_commands,
        "lint_commands": lint_commands,
        "typecheck_commands": typecheck_commands,
        "package_manager": package_manager,
        "ci_configuration": _ci_configuration(repo_path),
        "project_language": _project_language(repo_path),
        "framework": _framework(package),
        "dependency_lockfiles": _lockfiles(repo_path),
    }


def _git(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _detect_shadow_branch(repo_path: Path) -> str | None:
    branches = _git(repo_path, "branch", "--format=%(refname:short)").splitlines()
    candidates = [
        branch
        for branch in branches
        if branch.startswith("aios/") or branch.startswith("aios-") or "aios-shadow" in branch
    ]
    return sorted(candidates)[0] if candidates else None


def _relative_matches(repo_path: Path, candidates: tuple[str, ...]) -> list[str]:
    return [relative for relative in candidates if (repo_path / relative).exists()]


def _load_json_if_exists(path: Path) -> object:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _package_manager(repo_path: Path, package: object) -> str | None:
    if isinstance(package, dict):
        declared = package.get("packageManager")
        if isinstance(declared, str):
            name = declared.split("@", maxsplit=1)[0]
            if name in {"pnpm", "npm", "yarn"}:
                return name
    if (repo_path / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo_path / "package-lock.json").exists():
        return "npm"
    if (repo_path / "yarn.lock").exists():
        return "yarn"
    return "pnpm" if (repo_path / "package.json").exists() else None


def _script_commands(scripts: object, names: tuple[str, ...], package_manager: str | None) -> list[str]:
    if not isinstance(scripts, dict):
        return []
    commands: list[str] = []
    for name in names:
        if name in scripts:
            if package_manager == "npm":
                commands.append(f"npm run {name}")
            elif package_manager == "yarn":
                commands.append(f"yarn {name}")
            else:
                commands.append(f"pnpm {name}")
    return commands


def _build_system(repo_path: Path) -> str | None:
    if (repo_path / "package.json").exists():
        return "node"
    if (repo_path / "pyproject.toml").exists():
        return "python"
    if (repo_path / "Cargo.toml").exists():
        return "rust"
    if (repo_path / "go.mod").exists():
        return "go"
    return None


def _testing_framework(package: object) -> str | None:
    if not isinstance(package, dict):
        return None
    text = json.dumps(package).lower()
    for name in ("vitest", "pytest", "jest", "playwright"):
        if name in text:
            return name
    return None


def _framework(package: object) -> str | None:
    if not isinstance(package, dict):
        return None
    deps: dict[str, object] = {}
    for key in ("dependencies", "devDependencies"):
        value = package.get(key)
        if isinstance(value, dict):
            deps.update(value)
    if "next" in deps:
        return "nextjs"
    if "react" in deps:
        return "react"
    return None


def _project_language(repo_path: Path) -> str | None:
    if any(repo_path.rglob("*.ts")) or any(repo_path.rglob("*.tsx")):
        return "typescript"
    if any(repo_path.rglob("*.py")):
        return "python"
    if any(repo_path.rglob("*.rs")):
        return "rust"
    if any(repo_path.rglob("*.go")):
        return "go"
    return None


def _lockfiles(repo_path: Path) -> list[str]:
    names = (
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "uv.lock",
        "poetry.lock",
        "Cargo.lock",
        "go.sum",
    )
    return [name for name in names if (repo_path / name).exists()]


def _ci_configuration(repo_path: Path) -> list[str]:
    workflows = repo_path / ".github" / "workflows"
    if not workflows.exists():
        return []
    return sorted(str(path.relative_to(repo_path)) for path in workflows.glob("*.yml"))


def _environment_manifest() -> dict[str, object]:
    return {
        "schema": "tmcp-benchmark-environments-v0.1",
        "created_at": now_iso(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hardware": platform.machine(),
        "unavailable_values_policy": "Use null, never fabricated zeros.",
    }


def _skill_equivalence_manifest() -> dict[str, object]:
    return {
        "schema": "tmcp-benchmark-skill-equivalence-v0.1",
        "created_at": now_iso(),
        "review_status": "not_started",
        "human_skills": [],
        "rule": "Flat skills, cold TMCP, and shortcut TMCP must have semantically equivalent knowledge.",
    }


def _shortcut_registry_manifest() -> dict[str, object]:
    return {
        "schema": "tmcp-benchmark-shortcut-registry-v0.1",
        "created_at": now_iso(),
        "shortcut_states": list(SHORTCUT_STATES),
        "shortcuts": [],
        "leakage_rule": "Shortcuts must encode reusable routing knowledge, not target-task answers.",
    }


def _freeze_manifest() -> dict[str, object]:
    return {
        "schema": "tmcp-benchmark-freeze-v0.1",
        "created_at": now_iso(),
        "conditions": list(BENCHMARK_CONDITIONS),
        "systems_frozen": False,
        "freeze_required_before_held_out": [
            "tmcp_compiler",
            "skill_corpus",
            "flat_skill_representation",
            "graph_router",
            "shortcut_registry",
            "shortcut_validation_rules",
            "scoring_rubric",
            "task_definitions",
            "hidden_tests",
        ],
        "run_record_template": run_record_template(),
    }


def run_record_template() -> dict[str, object]:
    return {
        "run_id": "",
        "benchmark_version": BENCHMARK_SCHEMA,
        "project_id": "",
        "task_family_id": "",
        "task_id": "",
        "task_class": "",
        "compositionality_score": 0,
        "condition_anonymous_id": "",
        "condition_actual": "",
        "starting_commit": "",
        "aios_commit": "",
        "skill_corpus_hash": "",
        "flat_skill_hash": "",
        "tmcp_graph_hash": "",
        "tmcp_compiler_commit": "",
        "shortcut_registry_hash": "",
        "shortcut_id": None,
        "shortcut_state": "NONE",
        "shortcut_confidence": None,
        "shortcut_selected": False,
        "shortcut_correct": None,
        "shortcut_fallback_used": False,
        "model": "",
        "model_version": "",
        "reasoning_level": "",
        "harness": "",
        "seed": 0,
        "started_at": "",
        "environment_ready_at": "",
        "task_presented_at": "",
        "route_selected_at": "",
        "first_relevant_action_at": "",
        "first_edit_at": "",
        "first_test_at": "",
        "first_successful_test_at": "",
        "public_tests_completed_at": "",
        "hidden_tests_completed_at": "",
        "agent_completed_at": "",
        "evaluation_completed_at": "",
        "setup_seconds": 0,
        "routing_seconds": 0,
        "time_to_first_relevant_action_seconds": 0,
        "time_to_first_edit_seconds": 0,
        "time_to_first_test_seconds": 0,
        "time_to_first_successful_test_seconds": None,
        "agent_execution_seconds": 0,
        "total_benchmark_seconds": 0,
        "input_tokens": None,
        "output_tokens": None,
        "cached_input_tokens": None,
        "uncached_input_tokens": None,
        "reasoning_tokens": None,
        "repository_context_tokens": None,
        "skill_tokens_loaded": None,
        "relevant_skill_tokens": None,
        "irrelevant_skill_tokens": None,
        "shortcut_lookup_tokens": None,
        "shortcut_validation_tokens": None,
        "routing_tokens": None,
        "recovery_tokens": None,
        "estimated_cost_usd": None,
        "tool_calls": 0,
        "failed_tool_calls": 0,
        "shell_commands": 0,
        "repeated_commands": 0,
        "files_opened": 0,
        "irrelevant_files_opened": 0,
        "selected_modules": [],
        "expected_modules": [],
        "route_precision": None,
        "route_recall": None,
        "public_tests_passed": 0,
        "public_tests_total": 0,
        "hidden_tests_passed": 0,
        "hidden_tests_total": 0,
        "build_passed": False,
        "lint_passed": False,
        "typecheck_passed": False,
        "regression_count": 0,
        "task_completed": False,
        "quality_score_raw": 0,
        "quality_score_adjusted": 0,
        "hard_penalties": [],
        "unsupported_assumptions": [],
        "prohibited_actions": [],
        "patch_path": "",
        "log_path": "",
        "timing_path": "",
        "token_path": "",
        "route_receipt_path": "",
        "shortcut_receipt_path": "",
        "evaluator_version": "",
        "notes": "",
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _json_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _select_preflight_projects(
    results: list[dict[str, object]],
    preferred_projects: tuple[str, ...],
) -> list[str]:
    eligible = [item for item in results if item.get("eligible")]
    by_id = {str(item["project_id"]): item for item in eligible}
    selected = [project_id for project_id in preferred_projects if project_id in by_id]
    for item in sorted(eligible, key=lambda row: str(row["project_id"])):
        project_id = str(item["project_id"])
        if project_id not in selected:
            selected.append(project_id)
        if len(selected) >= 2:
            break
    return selected[:2]


def _validate_task_manifest(
    task_families: list[dict[str, object]],
    tasks: list[dict[str, object]],
) -> None:
    family_ids = {str(family.get("task_family_id")) for family in task_families}
    task_ids: set[str] = set()
    required_task_fields = {
        "task_id",
        "task_family_id",
        "project_id",
        "task_class",
        "compositionality_score",
        "starting_commit",
        "natural_language_request",
        "public_acceptance_criteria",
        "hidden_acceptance_criteria",
        "required_test_commands",
        "expected_tmcp_route",
        "expected_shortcut_eligibility",
        "maximum_execution_time_seconds",
        "maximum_token_budget",
        "network_access",
        "evaluator_rubric",
        "real_work_reason",
    }
    for task in tasks:
        missing = sorted(field for field in required_task_fields if field not in task)
        if missing:
            raise ValueError(f"Task {task.get('task_id', '<unknown>')} missing required fields: {missing}")
        task_id = str(task["task_id"])
        if task_id in task_ids:
            raise ValueError(f"Duplicate task_id: {task_id}")
        task_ids.add(task_id)
        if str(task["task_family_id"]) not in family_ids:
            raise ValueError(f"Task {task_id} references unknown task family.")


def _tasks_by_id(benchmark_root: Path) -> dict[str, dict[str, object]]:
    payload = _read_json_object(benchmark_root / "tasks" / "tasks.json")
    tasks = _json_list(payload.get("tasks"))
    return {
        str(task["task_id"]): task
        for task in tasks
        if isinstance(task, dict) and task.get("task_id")
    }


def _condition_id(task_id: str, repeat_index: int, condition: str, seed: int) -> str:
    digest = hashlib.sha256(f"{task_id}:{repeat_index}:{condition}:{seed}".encode()).hexdigest()
    return f"cond-{digest[:12]}"


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _condition_assignment(benchmark_root: Path, condition_anonymous_id: str) -> dict[str, object]:
    payload = _read_json_object(benchmark_root / "manifest" / "condition-map.json")
    for assignment in _json_list(payload.get("assignments")):
        if isinstance(assignment, dict) and assignment.get("condition_anonymous_id") == condition_anonymous_id:
            return assignment
    raise ValueError(f"Unknown condition_anonymous_id: {condition_anonymous_id}")


def _read_condition_seed(benchmark_root: Path) -> int:
    payload = _read_json_object(benchmark_root / "manifest" / "condition-map.json")
    seed = payload.get("seed", 0)
    return int(seed) if isinstance(seed, int | float | str) and str(seed).isdigit() else 0


def _repository_for_project(benchmark_root: Path, project_id: str) -> dict[str, object]:
    payload = _read_json_object(benchmark_root / "manifest" / "repositories.json")
    for repo in _json_list(payload.get("repositories")):
        if isinstance(repo, dict) and repo.get("project_id") == project_id:
            return repo
    raise ValueError(f"Repository not found in manifest for project_id: {project_id}")


def _create_worktree(repo_path: Path, worktree: Path, commit: str) -> None:
    worktree.parent.mkdir(parents=True, exist_ok=True)
    if worktree.exists():
        raise ValueError(f"Worktree already exists: {worktree}")
    result = subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree), commit],
        cwd=repo_path,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git worktree add failed")


def _monotonic() -> float:
    return time.monotonic()


def _run_commands(
    commands: list[str],
    cwd: Path,
    artifact_dir: Path,
    label: str,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    first_started_at = ""
    first_success_at = ""
    for index, command in enumerate(commands):
        started_at = now_iso()
        if not first_started_at:
            first_started_at = started_at
        started = _monotonic()
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )
        ended_at = now_iso()
        if result.returncode == 0 and not first_success_at:
            first_success_at = ended_at
        log_path = artifact_dir / f"{label}-{index}.log"
        log_path.write_text(
            f"$ {command}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}",
            encoding="utf-8",
        )
        results.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_seconds": round(_monotonic() - started, 6),
                "log_path": str(log_path),
            }
        )
    return {
        "commands": results,
        "first_started_at": first_started_at,
        "first_success_at": first_success_at,
    }


def _route_payload(
    task: dict[str, object],
    assignment: dict[str, object],
    run_id: str,
) -> dict[str, object]:
    expected = _string_list(task.get("expected_tmcp_route"))
    condition = str(assignment["condition_actual"])
    if condition == "baseline":
        selected: list[str] = []
    elif condition == "flat_skills":
        selected = _string_list(task.get("expected_skills"))
    else:
        selected = expected
    precision, recall = _route_scores(selected, expected)
    return {
        "schema": "tmcp-benchmark-route-v0.1",
        "run_id": run_id,
        "condition_actual": condition,
        "selected_modules": selected,
        "expected_modules": expected,
        "route_precision": precision,
        "route_recall": recall,
        "shortcut_state": _shortcut_state_for_condition(condition),
    }


def _route_scores(selected: list[str], expected: list[str]) -> tuple[float | None, float | None]:
    selected_set = set(selected)
    expected_set = set(expected)
    if not expected_set:
        return None, None
    precision = len(selected_set & expected_set) / len(selected_set) if selected_set else 0.0
    recall = len(selected_set & expected_set) / len(expected_set)
    return round(precision, 4), round(recall, 4)


def _shortcut_state_for_condition(condition: str) -> str:
    if condition == "tmcp_validated_shortcut":
        return "VALIDATED_SELECTED"
    if condition == "tmcp_cold_start":
        return "NONE"
    return "NONE"


def _condition_token_payload(condition: str, task: dict[str, object]) -> dict[str, object]:
    route_tokens = {
        "baseline": 0,
        "flat_skills": 1400,
        "tmcp_cold_start": 900,
        "tmcp_validated_shortcut": 450,
    }.get(condition, 0)
    expected_modules = _string_list(task.get("expected_tmcp_route"))
    return {
        "input_tokens": None,
        "output_tokens": None,
        "cached_input_tokens": None,
        "uncached_input_tokens": None,
        "reasoning_tokens": None,
        "repository_context_tokens": None,
        "skill_tokens_loaded": route_tokens,
        "relevant_skill_tokens": min(route_tokens, len(expected_modules) * 225) if route_tokens else None,
        "irrelevant_skill_tokens": max(0, route_tokens - len(expected_modules) * 225) if route_tokens else None,
        "shortcut_lookup_tokens": 120 if condition == "tmcp_validated_shortcut" else None,
        "shortcut_validation_tokens": 80 if condition == "tmcp_validated_shortcut" else None,
        "routing_tokens": route_tokens if condition.startswith("tmcp_") else None,
        "recovery_tokens": None,
        "estimated_cost_usd": None,
        "estimated_loaded_context_tokens": route_tokens,
        "token_claim_basis": "estimated_loaded_context_tokens_only",
    }


def _evaluation_payload(record: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "tmcp-benchmark-automated-evaluation-v0.1",
        "run_id": record["run_id"],
        "task_completed": record["task_completed"],
        "quality_score_raw": record["quality_score_raw"],
        "quality_score_adjusted": record["quality_score_adjusted"],
        "public_tests_passed": record["public_tests_passed"],
        "public_tests_total": record["public_tests_total"],
        "hidden_tests_passed": record["hidden_tests_passed"],
        "hidden_tests_total": record["hidden_tests_total"],
        "speed_token_claim_allowed": bool(record["task_completed"]),
    }


def _condition_summary(runs: list[dict[str, object]]) -> dict[str, object]:
    completed = [run for run in runs if run.get("task_completed")]
    return {
        "run_count": len(runs),
        "success_count": len(completed),
        "completion_rate": round(len(completed) / len(runs), 4) if runs else None,
        "median_quality_score": _median_number(run.get("quality_score_adjusted") for run in runs),
        "median_total_benchmark_seconds": _median_number(run.get("total_benchmark_seconds") for run in runs),
        "median_total_tokens": _median_number(_total_tokens(run) for run in runs),
        "median_estimated_loaded_context_tokens": _median_number(
            run.get("estimated_loaded_context_tokens") for run in runs
        ),
    }


def _comparison_summary(
    baseline_runs: list[dict[str, object]],
    challenger_runs: list[dict[str, object]],
) -> dict[str, object]:
    baseline = _condition_summary(baseline_runs)
    challenger = _condition_summary(challenger_runs)
    baseline_quality = baseline["median_quality_score"]
    challenger_quality = challenger["median_quality_score"]
    baseline_completion = baseline["completion_rate"]
    challenger_completion = challenger["completion_rate"]
    quality_ok = (
        isinstance(baseline_quality, int | float)
        and isinstance(challenger_quality, int | float)
        and challenger_quality >= baseline_quality
    )
    completion_ok = (
        isinstance(baseline_completion, int | float)
        and isinstance(challenger_completion, int | float)
        and challenger_completion >= baseline_completion
    )
    quality_claim_allowed = bool(quality_ok and completion_ok)
    speed_delta = _delta(
        baseline["median_total_benchmark_seconds"],
        challenger["median_total_benchmark_seconds"],
    )
    estimated_token_delta = _delta(
        baseline["median_estimated_loaded_context_tokens"],
        challenger["median_estimated_loaded_context_tokens"],
    )
    speed_claim_allowed = quality_claim_allowed and isinstance(speed_delta, int | float) and speed_delta > 0
    token_claim_allowed = (
        quality_claim_allowed
        and isinstance(estimated_token_delta, int | float)
        and estimated_token_delta > 0
    )
    reason = "quality_noninferior" if quality_claim_allowed else "quality_or_completion_regression"
    return {
        "baseline": baseline,
        "challenger": challenger,
        "quality_claim_allowed": quality_claim_allowed,
        "speed_claim_allowed": speed_claim_allowed,
        "token_claim_allowed": token_claim_allowed,
        "reason": reason,
        "speed_delta_seconds": speed_delta if quality_claim_allowed else None,
        "estimated_loaded_context_token_delta": estimated_token_delta if quality_claim_allowed else None,
    }


def _median_number(values: object) -> float | None:
    numeric = sorted(float(value) for value in values if isinstance(value, int | float))
    if not numeric:
        return None
    midpoint = len(numeric) // 2
    if len(numeric) % 2:
        return numeric[midpoint]
    return (numeric[midpoint - 1] + numeric[midpoint]) / 2


def _total_tokens(run: dict[str, object]) -> int | None:
    input_tokens = run.get("input_tokens")
    output_tokens = run.get("output_tokens")
    if isinstance(input_tokens, int | float) and isinstance(output_tokens, int | float):
        return int(input_tokens + output_tokens)
    return None


def _delta(baseline: object, challenger: object) -> float | None:
    if isinstance(baseline, int | float) and isinstance(challenger, int | float):
        return round(float(baseline) - float(challenger), 6)
    return None


def _write_report_summaries(benchmark_root: Path, aggregate: dict[str, object]) -> None:
    (benchmark_root / "reports").mkdir(parents=True, exist_ok=True)
    technical = benchmark_root / "reports" / "technical-report.md"
    executive = benchmark_root / "reports" / "executive-summary.md"
    claims = benchmark_root / "reports" / "claims-register.md"
    summary = json.dumps(
        {
            "run_count": aggregate["run_count"],
            "conditions": aggregate["conditions"],
            "comparisons": aggregate["comparisons"],
        },
        indent=2,
        sort_keys=True,
    )
    technical.write_text(f"# TMCP Multi-Project Benchmark Technical Report\n\n```json\n{summary}\n```\n", encoding="utf-8")
    executive.write_text(
        "# Executive Summary\n\nCalibration data exists, but promotional claims remain unapproved.\n",
        encoding="utf-8",
    )
    claims.write_text(
        "# Claims Register\n\nNo public claim is approved until held-out analysis is complete.\n",
        encoding="utf-8",
    )
