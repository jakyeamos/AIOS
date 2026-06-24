from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = ROOT / "scripts" / "codex-aios-shadow.py"
    spec = importlib.util.spec_from_file_location("codex_aios_shadow", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_make_task_id_is_bounded_and_stable_shape() -> None:
    module = _load_module()

    task_id = module.make_task_id("Fix the route selector and verify the operator UI")

    assert task_id.startswith("codex-shadow-")
    assert "fix-the-route-selector" in task_id
    assert len(task_id) < 90


def test_shadow_prompt_points_to_separate_codex_thread() -> None:
    module = _load_module()

    prompt = module.shadow_prompt(
        "Fix login",
        {"worktree_path": "/tmp/repo/.aios/shadow-worktrees/aios-eval-fix-login-full-aios"},
    )

    assert prompt is not None
    assert "separate Codex thread" in prompt
    assert "/aios-shadow-implementation Fix login" in prompt


def test_make_branch_name_uses_codex_namespace() -> None:
    module = _load_module()

    branch = module.make_branch_name("codex-shadow-260624-fix-login")

    assert branch == "codex/aios-shadow-codex-shadow-260624-fix-login"
    assert branch.count("/") == 1


def test_baseline_instruction_separates_shadow_from_governed_route() -> None:
    module = _load_module()

    automatic = module.baseline_instruction(False)
    governed = module.baseline_instruction(True)

    assert "normally" in automatic
    assert "evidence only" in automatic
    assert "governing context" in governed


def test_route_rule_separates_shadow_from_governed_route() -> None:
    module = _load_module()

    automatic = module.route_rule(False)
    governed = module.route_rule(True)

    assert "do not govern" in automatic
    assert "govern" in governed
