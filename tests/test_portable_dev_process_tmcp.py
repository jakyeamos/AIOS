from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / "config" / "tmcp" / "portable-dev-process"


def _load_manifest() -> dict[str, Any]:
    return json.loads((PACK_ROOT / "manifest.json").read_text(encoding="utf-8"))


def test_portable_dev_process_manifest_references_existing_nodes() -> None:
    manifest = _load_manifest()
    nodes = manifest["nodes"]
    assert isinstance(nodes, dict)

    task_nodes = nodes["tasks"]
    assert isinstance(task_nodes, dict)
    assert len(task_nodes) >= 10

    for task_id, task in task_nodes.items():
        assert isinstance(task, dict), task_id
        task_path = PACK_ROOT / str(task["path"])
        assert task_path.exists(), task_path
        required_modules = task["requires"]
        assert isinstance(required_modules, list), task_id
        assert required_modules, task_id
        for module_ref in required_modules:
            module_path = PACK_ROOT / str(module_ref)
            assert module_path.exists(), module_path
        optional_nodes = task.get("optional", [])
        assert isinstance(optional_nodes, list), task_id
        for optional_ref in optional_nodes:
            optional_path = PACK_ROOT / str(optional_ref)
            assert optional_path.exists(), optional_path

    module_nodes = nodes["modules"]
    assert isinstance(module_nodes, dict)
    for module_id, module_path in module_nodes.items():
        assert (PACK_ROOT / str(module_path)).exists(), module_id

    branch_nodes = nodes["branches"]
    assert isinstance(branch_nodes, dict)
    for branch_id, branch_path in branch_nodes.items():
        assert (PACK_ROOT / str(branch_path)).exists(), branch_id


def test_portable_dev_process_excludes_aios_governance_requirements() -> None:
    manifest = _load_manifest()
    contract = manifest["portable_contract"]
    assert isinstance(contract, dict)

    assert contract["requires_aios_runtime"] is False
    assert contract["requires_sqlite"] is False
    assert "requires_truth_file_workflow" not in contract
    assert contract["requires_eval_archive"] is False

    readme = (PACK_ROOT / "README.md").read_text(encoding="utf-8")
    router = (PACK_ROOT / "router.md").read_text(encoding="utf-8")
    combined = f"{readme}\n{router}".lower()

    assert "eval archives" in combined
    assert "continuous-learning requirements" in combined
    assert "without explicitly asking" in combined


def test_portable_dev_process_has_core_dev_process_capabilities() -> None:
    manifest = _load_manifest()
    task_nodes = manifest["nodes"]["tasks"]
    assert isinstance(task_nodes, dict)

    expected_tasks = {
        "repo_detect",
        "quality_check",
        "debug_failure",
        "review_diff",
        "add_tests",
        "planning_review",
        "ci_triage",
        "frontend_verify",
        "visual_polish",
        "git_hygiene",
        "dependency_audit",
        "docs_update",
    }
    assert expected_tasks <= set(task_nodes)

    expected_modules = {
        "command_discovery",
        "quality_gate",
        "reproduce_first",
        "diff_review",
        "git_hygiene",
        "test_authoring",
        "ci_triage",
        "frontend_runtime",
        "saas_interaction_architecture",
        "visual_polish_system",
        "make_interfaces_feel_better",
        "enterprise_saas_visual_polish",
        "ai_surface_polish",
        "print_report_design",
        "data_realism_polish",
        "dependency_policy",
        "hook_guidance",
    }
    module_nodes = manifest["nodes"]["modules"]
    assert isinstance(module_nodes, dict)
    assert expected_modules <= set(module_nodes)


def test_portable_dev_process_routing_cases_are_satisfied_by_manifest() -> None:
    manifest = _load_manifest()
    task_nodes = manifest["nodes"]["tasks"]
    assert isinstance(task_nodes, dict)
    branch_nodes = manifest["nodes"]["branches"]
    assert isinstance(branch_nodes, dict)
    cases = json.loads((PACK_ROOT / "tests" / "routing-cases.json").read_text(encoding="utf-8"))[
        "cases"
    ]

    for case in cases:
        task_id = case["expected_task"]
        assert task_id in task_nodes
        task = task_nodes[task_id]
        assert isinstance(task, dict)
        required = {Path(module_ref).stem for module_ref in task["requires"]}
        assert set(case["expected_modules"]) <= required
        optional = {Path(module_ref).stem for module_ref in task.get("optional", [])}
        assert set(case.get("expected_optional_modules", [])) <= optional
        expected_branch = case.get("expected_branch")
        if expected_branch is not None:
            assert expected_branch in branch_nodes


def test_visual_polish_keeps_tenure_identity_as_optional_branch() -> None:
    manifest = _load_manifest()
    task_nodes = manifest["nodes"]["tasks"]
    assert isinstance(task_nodes, dict)
    visual_polish = task_nodes["visual_polish"]
    assert isinstance(visual_polish, dict)

    required = set(visual_polish["requires"])
    assert "branches/tenure_visual_identity.branch.md" not in required

    optional = set(visual_polish["optional"])
    assert "branches/tenure_visual_identity.branch.md" in optional


def test_visual_polish_keeps_detail_polish_skill_optional() -> None:
    manifest = _load_manifest()
    task_nodes = manifest["nodes"]["tasks"]
    assert isinstance(task_nodes, dict)
    visual_polish = task_nodes["visual_polish"]
    assert isinstance(visual_polish, dict)

    required = set(visual_polish["requires"])
    assert "modules/make_interfaces_feel_better.md" not in required

    optional = set(visual_polish["optional"])
    assert "modules/make_interfaces_feel_better.md" in optional


def test_visual_polish_keeps_product_identity_branches_optional() -> None:
    manifest = _load_manifest()
    task_nodes = manifest["nodes"]["tasks"]
    assert isinstance(task_nodes, dict)
    visual_polish = task_nodes["visual_polish"]
    assert isinstance(visual_polish, dict)

    required = set(visual_polish["requires"])
    assert "branches/bidcamp_visual_identity.branch.md" not in required
    assert "branches/framework_labs_editorial_identity.branch.md" not in required

    optional = set(visual_polish["optional"])
    assert "branches/bidcamp_visual_identity.branch.md" in optional
    assert "branches/framework_labs_editorial_identity.branch.md" in optional


def test_visual_polish_keeps_print_report_module_optional() -> None:
    manifest = _load_manifest()
    task_nodes = manifest["nodes"]["tasks"]
    assert isinstance(task_nodes, dict)
    visual_polish = task_nodes["visual_polish"]
    assert isinstance(visual_polish, dict)

    required = set(visual_polish["requires"])
    assert "modules/print_report_design.md" not in required

    optional = set(visual_polish["optional"])
    assert "modules/print_report_design.md" in optional
