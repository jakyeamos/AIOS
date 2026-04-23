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
