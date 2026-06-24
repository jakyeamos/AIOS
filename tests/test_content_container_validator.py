from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "content-container-validator.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("content_container_validator", VALIDATOR_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bbdse_counts_lis_as_child_repo(tmp_path: Path, capsys) -> None:
    validator = _load_validator()
    root = tmp_path / "BBDSE"
    root.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "project-truth.md").write_text("# Truth\n", encoding="utf-8")
    (root / "docs" / "child-project-ownership.md").write_text("# Children\n", encoding="utf-8")
    for child in validator.BBDSE_CHILDREN:
        (root / child).mkdir()

    result = validator.validate_bbdse(root, run_delegated=False)

    output = capsys.readouterr().out
    assert result == 1
    assert "missing_child_pre_cr:LIS" in output
