from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "prompts"


def _load_validate_module():
    module_path = ROOT / "bin" / "validate-prompts.py"
    spec = importlib.util.spec_from_file_location("validate_prompts", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_fixture(name: str, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    source = FIXTURES / name
    destination = destination_dir / name
    shutil.copy2(source, destination)
    return destination


def _valid_prompt_text(
    *,
    prompt_id: str = "synthetic",
    lifecycle_state: str | None = "active",
    applicability: bool = True,
    last_evaluated_at: str | None = "2026-05-21T00:00:00Z",
    route_status: str | None = None,
) -> str:
    lines = [
        "---",
        f"id: {prompt_id}",
        "name: Synthetic Template",
        'version: "1.0"',
        "classification: debug",
        "tags:",
        "  - debug",
        "purpose: Synthetic prompt for validator tests.",
        "when_to_use: Use in validator tests.",
        "when_not_to_use: Do not use in production.",
        "required_inputs:",
        "  - symptom: Observed failure.",
        "output_contract: Root cause and minimal fix.",
        "eval_criteria:",
        "  - Root cause is explicit.",
        "owner: test-suite",
        'last_updated: "2026-04-23"',
    ]
    if lifecycle_state is not None:
        lines.append(f"lifecycle_state: {lifecycle_state}")
    if route_status is not None:
        lines.append(f"route_status: {route_status}")
    if applicability:
        lines.extend(["applicability:", "  - failure_recovery"])
    if last_evaluated_at is not None:
        lines.append(f'last_evaluated_at: "{last_evaluated_at}"')
    lines.extend(
        [
            "changelog:",
            '  - version: "1.0"',
            '    date: "2026-04-23"',
            "    note: Synthetic fixture.",
            "---",
            "",
            "## Instructions",
            "",
            "Debug.",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_synthetic_prompt(prompts_root: Path, text: str, name: str = "synthetic.md") -> None:
    prompts_root.mkdir(parents=True, exist_ok=True)
    (prompts_root / name).write_text(text, encoding="utf-8")


def test_validate_prompts_success_writes_registry(tmp_path: Path) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _copy_fixture("valid_template.md", prompts_root)
    (prompts_root / "evals" / "valid_template").mkdir(parents=True)
    (prompts_root / "evals" / "valid_template" / "cases.md").write_text(
        "## Case 1\n",
        encoding="utf-8",
    )

    exit_code = module.main(["--prompts-root", str(prompts_root)])
    assert exit_code == 0

    registry = json.loads((prompts_root / "registry.json").read_text(encoding="utf-8"))
    assert len(registry["templates"]) == 1
    assert registry["templates"][0]["id"] == "valid_template"
    assert registry["templates"][0]["classification"] == "debug"


def test_validate_prompts_flags_missing_required_fields(tmp_path: Path) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _copy_fixture("missing_fields.md", prompts_root)

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert rows == []
    assert any("missing required field 'purpose'" in error for error in errors)
    assert any("missing required field 'when_to_use'" in error for error in errors)


def test_validate_prompts_flags_duplicate_ids(tmp_path: Path) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _copy_fixture("valid_template.md", prompts_root)
    _copy_fixture("duplicate_id.md", prompts_root)

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert rows == []
    assert any("duplicate id 'valid_template'" in error for error in errors)


def test_validate_prompts_requires_lifecycle_state(tmp_path: Path) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _write_synthetic_prompt(
        prompts_root,
        _valid_prompt_text(lifecycle_state=None),
    )

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert rows == []
    assert any("lifecycle_state" in error and "required" in error for error in errors)


def test_validate_prompts_rejects_invalid_lifecycle_state_value(tmp_path: Path) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _write_synthetic_prompt(
        prompts_root,
        _valid_prompt_text(lifecycle_state="promoted"),
    )

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert rows == []
    assert any(
        "promoted" in error and "draft|candidate|approved|active|deprecated" in error
        for error in errors
    )


def test_validate_prompts_accepts_canonical_prompts_post_plan_01() -> None:
    module = _load_validate_module()

    rows, errors, _warnings = module.validate_templates(ROOT / "prompts")
    assert errors == []
    assert len(rows) == 6


def test_validate_prompts_requires_applicability(tmp_path: Path) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _write_synthetic_prompt(
        prompts_root,
        _valid_prompt_text(applicability=False),
    )

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert rows == []
    assert any("applicability" in error and "required" in error for error in errors)


def test_validate_prompts_requires_last_evaluated_at(tmp_path: Path) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _write_synthetic_prompt(
        prompts_root,
        _valid_prompt_text(last_evaluated_at=None),
    )

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert rows == []
    assert any("last_evaluated_at" in error and "required" in error for error in errors)


def test_validate_prompts_accepts_route_status_alias_during_transition(
    tmp_path: Path,
) -> None:
    module = _load_validate_module()
    prompts_root = tmp_path / "prompts"
    _write_synthetic_prompt(
        prompts_root,
        _valid_prompt_text(lifecycle_state="active", route_status="approved"),
    )

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert errors == []
    assert rows[0]["lifecycle_state"] == "active"

    prompts_root = tmp_path / "prompts-route-only"
    _write_synthetic_prompt(
        prompts_root,
        _valid_prompt_text(lifecycle_state=None, route_status="approved"),
    )

    rows, errors, _warnings = module.validate_templates(prompts_root)
    assert rows == []
    assert any("lifecycle_state" in error and "required" in error for error in errors)
