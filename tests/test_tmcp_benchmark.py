from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.tmcp_benchmark import (  # noqa: E402
    BENCHMARK_CONDITIONS,
    SHORTCUT_STATES,
    aggregate_results,
    create_benchmark_scaffold,
    discover_repositories,
    freeze_benchmark,
    import_task_manifest,
    preflight_benchmark,
    randomize_condition_map,
    run_task_condition,
    tmcp_claim_gate,
    validate_shortcut_for_task,
)


def _init_repo(path: Path) -> str:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    (path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    (path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (path / "skills.tmcp").mkdir()
    (path / "skills.tmcp" / "router.md").write_text("# Router\n", encoding="utf-8")
    (path / ".github" / "workflows").mkdir(parents=True)
    (path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test User",
            "commit",
            "-m",
            "init",
        ],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "branch", "aios/main"], cwd=path, check=True, capture_output=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def test_discover_repositories_records_shadow_branch_and_tooling(tmp_path: Path) -> None:
    parent = tmp_path / "portfolio"
    expected_commit = _init_repo(parent / "project-a")
    _init_repo(parent / ".tool-cache")

    repositories = discover_repositories(parent)

    assert len(repositories) == 1
    repo = repositories[0]
    assert repo["project_id"] == "project-a"
    assert repo["default_branch"] == "main"
    assert repo["current_commit"] == expected_commit
    assert repo["aios_shadow_branch"] == "aios/main"
    assert repo["has_tmcp_graph"] is True
    assert repo["dependency_lockfiles"] == ["pnpm-lock.yaml"]
    assert repo["test_commands"] == ["pnpm test"]
    assert repo["package_manager"] == "pnpm"
    assert repo["ci_configuration"] == [".github/workflows/ci.yml"]


def test_discover_repositories_uses_lockfile_package_manager_for_scripts(tmp_path: Path) -> None:
    parent = tmp_path / "portfolio"
    repo = parent / "npm-project"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "package-lock.json").write_text('{"lockfileVersion": 3}\n', encoding="utf-8")
    (repo / "package.json").write_text('{"scripts":{"lint":"eslint"}}\n', encoding="utf-8")

    repositories = discover_repositories(parent)

    assert repositories[0]["package_manager"] == "npm"
    assert repositories[0]["lint_commands"] == ["npm run lint"]
    assert repositories[0]["dependency_lockfiles"] == ["package-lock.json"]


def test_create_benchmark_scaffold_writes_required_manifests_and_reports(tmp_path: Path) -> None:
    parent = tmp_path / "portfolio"
    _init_repo(parent / "project-a")
    output_root = tmp_path / "tmcp-benchmark"

    result = create_benchmark_scaffold(parent_dir=parent, output_root=output_root)

    assert result["benchmark_root"] == str(output_root)
    for relative in (
        "manifest/repositories.json",
        "manifest/environments.json",
        "manifest/skill-equivalence.json",
        "manifest/shortcut-registry.json",
        "manifest/freeze-manifest.json",
        "runs/raw",
        "analysis/scripts",
        "reports/technical-report.md",
        "reports/claims-register.md",
        "reports/promotional-evidence-pack.md",
    ):
        assert (output_root / relative).exists()

    repositories = json.loads((output_root / "manifest" / "repositories.json").read_text())
    assert repositories["schema"] == "tmcp-benchmark-repositories-v0.1"
    assert repositories["repositories"][0]["project_id"] == "project-a"

    shortcut_registry = json.loads(
        (output_root / "manifest" / "shortcut-registry.json").read_text()
    )
    assert shortcut_registry["shortcut_states"] == list(SHORTCUT_STATES)
    assert shortcut_registry["shortcuts"] == []

    freeze = json.loads((output_root / "manifest" / "freeze-manifest.json").read_text())
    assert freeze["conditions"] == list(BENCHMARK_CONDITIONS)
    assert freeze["run_record_template"]["shortcut_state"] == "NONE"
    assert freeze["run_record_template"]["uncached_input_tokens"] is None

    claims_register = (output_root / "reports" / "claims-register.md").read_text()
    assert "No public claim is approved until held-out analysis is complete" in claims_register


def _task_payload(
    repo_path: Path, start_sha: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    families = [
        {
            "task_family_id": "family-api",
            "description": "Add similar deterministic behavior.",
            "shared_process_structure": ["inspect", "edit", "test"],
            "expected_modules": ["context_gathering", "test_gate"],
            "expected_quality_gates": ["public_tests", "hidden_tests"],
            "development_tasks": ["task-dev"],
            "held_out_tasks": ["task-heldout"],
            "shortcut_eligible": True,
            "shortcut_transfer_scope": "same_repository",
            "known_invalidating_differences": [],
        }
    ]
    tasks = [
        {
            "task_id": "task-dev",
            "task_family_id": "family-api",
            "project_id": repo_path.name,
            "task_class": "repeated_task_family",
            "difficulty_estimate": "small",
            "compositionality_score": 4,
            "starting_commit": start_sha,
            "natural_language_request": "Development calibration task.",
            "public_acceptance_criteria": ["tests pass"],
            "hidden_acceptance_criteria": ["hidden tests pass"],
            "required_test_commands": ["python3 -c 'print(1)'"],
            "hidden_test_commands": ["python3 -c 'print(2)'"],
            "prohibited_shortcuts": [],
            "expected_skills": ["testing"],
            "expected_tmcp_route": ["@task:implementation", "@module:test_gate"],
            "expected_shortcut_eligibility": True,
            "maximum_execution_time_seconds": 60,
            "maximum_token_budget": 10000,
            "maximum_cost_budget_usd": None,
            "network_access": "disabled",
            "evaluator_rubric": "default-100",
            "known_risks": [],
            "real_work_reason": "Represents a deterministic local implementation loop.",
            "split": "development",
        },
        {
            "task_id": "task-heldout",
            "task_family_id": "family-api",
            "project_id": repo_path.name,
            "task_class": "repeated_task_family",
            "difficulty_estimate": "small",
            "compositionality_score": 4,
            "starting_commit": start_sha,
            "natural_language_request": "Held-out sibling task.",
            "public_acceptance_criteria": ["tests pass"],
            "hidden_acceptance_criteria": ["hidden tests pass"],
            "required_test_commands": ["python3 -c 'print(1)'"],
            "hidden_test_commands": ["python3 -c 'print(2)'"],
            "prohibited_shortcuts": ["task-heldout"],
            "expected_skills": ["testing"],
            "expected_tmcp_route": ["@task:implementation", "@module:test_gate"],
            "expected_shortcut_eligibility": True,
            "maximum_execution_time_seconds": 60,
            "maximum_token_budget": 10000,
            "maximum_cost_budget_usd": None,
            "network_access": "disabled",
            "evaluator_rubric": "default-100",
            "known_risks": [],
            "real_work_reason": "Held-out task shares process, not implementation answer.",
            "split": "held_out",
        },
    ]
    return families, tasks


def test_preflight_import_randomize_and_freeze_are_reproducible(tmp_path: Path) -> None:
    parent = tmp_path / "portfolio"
    start_sha = _init_repo(parent / "BIP-Console")
    output_root = tmp_path / "tmcp-benchmark"
    create_benchmark_scaffold(parent_dir=parent, output_root=output_root)

    preflight = preflight_benchmark(output_root=output_root, preferred_projects=("BIP-Console",))
    families, tasks = _task_payload(parent / "BIP-Console", start_sha)
    import_result = import_task_manifest(
        output_root=output_root, task_families=families, tasks=tasks
    )
    first_map = randomize_condition_map(output_root=output_root, seed=42, repeats=2)
    second_map = randomize_condition_map(output_root=output_root, seed=42, repeats=2)
    freeze = freeze_benchmark(
        output_root=output_root,
        model_config={
            "model": "stub-model",
            "model_version": "0",
            "reasoning_level": "none",
            "tool_permissions": "local",
            "network_access": "disabled",
        },
    )

    assert preflight["selected_projects"] == ["BIP-Console"]
    assert import_result["task_count"] == 2
    assert first_map == second_map
    assert len(first_map["assignments"]) == 10
    assert "tmcp_behavior_optimized" in first_map["conditions"]
    assert freeze["systems_frozen"] is True
    assert freeze["hashes"]["tasks_json"]
    assert (output_root / "manifest" / "model-config.json").exists()


def test_optimized_tmcp_condition_measures_against_flat_skills(tmp_path: Path) -> None:
    parent = tmp_path / "portfolio"
    start_sha = _init_repo(parent / "BIP-Console")
    output_root = tmp_path / "tmcp-benchmark"
    create_benchmark_scaffold(parent_dir=parent, output_root=output_root)
    families, tasks = _task_payload(parent / "BIP-Console", start_sha)
    import_task_manifest(output_root=output_root, task_families=families, tasks=tasks)
    condition_map = randomize_condition_map(output_root=output_root, seed=11, repeats=1)
    optimized_assignment = next(
        item
        for item in condition_map["assignments"]
        if item["condition_actual"] == "tmcp_behavior_optimized"
    )
    flat_assignment = next(
        item for item in condition_map["assignments"] if item["condition_actual"] == "flat_skills"
    )

    optimized = run_task_condition(
        output_root=output_root,
        run_id="run-optimized",
        task_id=str(optimized_assignment["task_id"]),
        condition_anonymous_id=str(optimized_assignment["condition_anonymous_id"]),
        executor="stub",
    )
    flat = run_task_condition(
        output_root=output_root,
        run_id="run-flat",
        task_id=str(flat_assignment["task_id"]),
        condition_anonymous_id=str(flat_assignment["condition_anonymous_id"]),
        executor="stub",
    )
    aggregate = aggregate_results(output_root=output_root)

    assert optimized["skill_tokens_loaded"] < flat["skill_tokens_loaded"]
    assert optimized["routing_tokens"] == optimized["skill_tokens_loaded"]
    assert "flat_skills__tmcp_behavior_optimized" in aggregate["comparisons"]


def test_preflight_accepts_clean_repo_with_lint_quality_command(tmp_path: Path) -> None:
    parent = tmp_path / "portfolio"
    repo = parent / "lint-only"
    _init_repo(repo)
    package_path = repo / "package.json"
    package_path.write_text('{"scripts":{"lint":"eslint"}}\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test User",
            "commit",
            "-m",
            "switch to lint quality command",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    output_root = tmp_path / "tmcp-benchmark"
    create_benchmark_scaffold(parent_dir=parent, output_root=output_root)

    preflight = preflight_benchmark(output_root=output_root, preferred_projects=("lint-only",))

    assert preflight["selected_projects"] == ["lint-only"]
    result = preflight["results"][0]
    assert result["eligible"] is True
    assert result["checks"]["has_quality_command"] is True
    assert result["checks"]["has_test_command"] is False
    assert result["checks"]["has_lint_command"] is True


def test_shortcut_leakage_guard_rejects_held_out_task_source(tmp_path: Path) -> None:
    parent = tmp_path / "portfolio"
    start_sha = _init_repo(parent / "BIP-Console")
    output_root = tmp_path / "tmcp-benchmark"
    create_benchmark_scaffold(parent_dir=parent, output_root=output_root)
    families, tasks = _task_payload(parent / "BIP-Console", start_sha)
    import_task_manifest(output_root=output_root, task_families=families, tasks=tasks)

    result = validate_shortcut_for_task(
        output_root=output_root,
        shortcut={
            "shortcut_id": "shortcut-leaky",
            "task_family_id": "family-api",
            "created_from_task_ids": ["task-heldout"],
            "validated_on_task_ids": [],
            "status": "validated",
        },
        task_id="task-heldout",
    )

    assert result["allowed"] is False
    assert result["reason"] == "shortcut_contains_target_task"


def test_run_task_condition_emits_isolated_records_and_hidden_tests_after_public(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "portfolio"
    start_sha = _init_repo(parent / "BIP-Console")
    output_root = tmp_path / "tmcp-benchmark"
    create_benchmark_scaffold(parent_dir=parent, output_root=output_root)
    families, tasks = _task_payload(parent / "BIP-Console", start_sha)
    import_task_manifest(output_root=output_root, task_families=families, tasks=tasks)
    condition_map = randomize_condition_map(output_root=output_root, seed=7, repeats=1)
    assignment = next(
        item for item in condition_map["assignments"] if item["task_id"] == "task-heldout"
    )

    run = run_task_condition(
        output_root=output_root,
        run_id="run-1",
        task_id="task-heldout",
        condition_anonymous_id=assignment["condition_anonymous_id"],
        executor="stub",
    )

    assert run["run_id"] == "run-1"
    assert run["task_completed"] is True
    assert run["input_tokens"] is None
    assert run["uncached_input_tokens"] is None
    assert run["public_tests_passed"] == 1
    assert run["hidden_tests_passed"] == 1
    assert run["public_tests_completed_at"] <= run["hidden_tests_completed_at"]
    assert Path(run["patch_path"]).exists()
    assert Path(run["route_receipt_path"]).exists()
    assert not (parent / "BIP-Console" / "benchmark_context.json").exists()


def test_aggregate_refuses_speed_or_token_win_when_quality_is_worse(tmp_path: Path) -> None:
    output_root = tmp_path / "tmcp-benchmark"
    (output_root / "runs" / "raw").mkdir(parents=True)
    better_quality = {
        "run_id": "baseline",
        "task_id": "task-1",
        "condition_actual": "baseline",
        "task_completed": True,
        "quality_score_adjusted": 90,
        "total_benchmark_seconds": 100,
        "input_tokens": 1000,
        "output_tokens": 100,
    }
    faster_failed = {
        "run_id": "tmcp",
        "task_id": "task-1",
        "condition_actual": "tmcp_validated_shortcut",
        "task_completed": False,
        "quality_score_adjusted": 20,
        "total_benchmark_seconds": 10,
        "input_tokens": 200,
        "output_tokens": 20,
    }
    (output_root / "runs" / "raw" / "baseline.json").write_text(json.dumps(better_quality))
    (output_root / "runs" / "raw" / "tmcp.json").write_text(json.dumps(faster_failed))

    aggregate = aggregate_results(output_root=output_root)

    comparison = aggregate["comparisons"]["baseline__tmcp_validated_shortcut"]
    assert comparison["speed_claim_allowed"] is False
    assert comparison["token_claim_allowed"] is False
    assert comparison["reason"] == "quality_or_completion_regression"
    assert (output_root / "analysis" / "tables" / "condition-summary.json").exists()


def test_tmcp_claim_gate_requires_quality_tokens_missed_requirements_and_separate_shortcut() -> (
    None
):
    runs = [
        {
            "condition_actual": "flat_skills",
            "task_completed": True,
            "quality_score_adjusted": 90,
            "estimated_loaded_context_tokens": 1400,
            "missed_requirement_count": 0,
        },
        {
            "condition_actual": "tmcp_behavior_optimized",
            "task_completed": True,
            "quality_score_adjusted": 90,
            "estimated_loaded_context_tokens": 650,
            "missed_requirement_count": 0,
        },
        {
            "condition_actual": "tmcp_validated_shortcut",
            "task_completed": True,
            "quality_score_adjusted": 90,
            "estimated_loaded_context_tokens": 450,
            "missed_requirement_count": 0,
        },
    ]

    gate = tmcp_claim_gate(runs)

    assert gate["claim_allowed"] is True
    assert gate["reason"] == "quality_noninferior_token_positive_missed_requirements_nonregressive"


def test_tmcp_claim_gate_blocks_when_missed_requirement_rate_regresses() -> None:
    runs = [
        {
            "condition_actual": "flat_skills",
            "task_completed": True,
            "quality_score_adjusted": 90,
            "estimated_loaded_context_tokens": 1400,
            "missed_requirement_count": 0,
        },
        {
            "condition_actual": "tmcp_behavior_optimized",
            "task_completed": True,
            "quality_score_adjusted": 90,
            "estimated_loaded_context_tokens": 650,
            "missed_requirement_count": 1,
        },
        {
            "condition_actual": "tmcp_validated_shortcut",
            "task_completed": True,
            "quality_score_adjusted": 90,
            "estimated_loaded_context_tokens": 450,
            "missed_requirement_count": 0,
        },
    ]

    gate = tmcp_claim_gate(runs)

    assert gate["claim_allowed"] is False
    assert gate["reason"] == "missed_requirement_rate_worse"
