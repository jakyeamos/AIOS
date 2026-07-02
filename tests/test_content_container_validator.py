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


def _vault_root(tmp_path: Path) -> Path:
    root = tmp_path / "Vaults"
    (root / ".tracker").mkdir(parents=True)
    (root / ".obsidian").mkdir()
    (root / "Command-Center").mkdir()
    (root / "README.md").write_text("# Vaults\n", encoding="utf-8")
    (root / ".tracker" / "PROJECT_TRUTH.md").write_text("# Truth\n", encoding="utf-8")
    return root


def _trusted_frontmatter() -> str:
    return """---
type: wiki
status: active
quality: human-curated
trust: trusted
sensitivity: safe
area: knowledge
created: "2026-07-02"
updated: "2026-07-02"
last_reviewed: "2026-07-02"
source: human
related: []
tags:
  - wiki
---
"""


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


def test_vault_reports_missing_metadata_for_trusted_surface(tmp_path: Path, capsys) -> None:
    validator = _load_validator()
    root = _vault_root(tmp_path)
    dashboard = root / "Command-Center" / "01 Dashboard"
    dashboard.mkdir(parents=True)
    (dashboard / "Open Actions.md").write_text(
        "---\ntype: dashboard\n---\n# Open Actions\n",
        encoding="utf-8",
    )

    result = validator.validate_vault(root)

    output = capsys.readouterr().out
    assert result == 1
    assert "missing_metadata:Command-Center/01 Dashboard/Open Actions.md:trust" in output
    assert "missing_metadata:Command-Center/01 Dashboard/Open Actions.md:sensitivity" in output


def test_vault_checks_only_trusted_wikilinks(tmp_path: Path, capsys) -> None:
    validator = _load_validator()
    root = _vault_root(tmp_path)
    wiki = root / "Command-Center" / "06 Knowledge" / "Wiki"
    archive = root / "Command-Center" / "09 Archive"
    wiki.mkdir(parents=True)
    archive.mkdir(parents=True)
    (wiki / "Trusted.md").write_text(
        _trusted_frontmatter() + "# Trusted\n[[Missing Trusted Target]]\n",
        encoding="utf-8",
    )
    (archive / "Raw Import.md").write_text(
        "# Raw Import\n[[Archive Missing Target]]\n",
        encoding="utf-8",
    )

    result = validator.validate_vault(root)

    output = capsys.readouterr().out
    assert result == 1
    assert "broken_trusted_wikilink:Command-Center/06 Knowledge/Wiki/Trusted.md->Missing Trusted Target" in output
    assert "Archive Missing Target" not in output


def test_vault_redacts_secret_like_paths(tmp_path: Path, capsys) -> None:
    validator = _load_validator()
    root = _vault_root(tmp_path)
    notes = root / "Command-Center" / "Personal-Corpus" / "Notes"
    notes.mkdir(parents=True)
    secret = "sk-abcdefghijklmnopqrstuvwxyz"
    (notes / f"{secret}.md").write_text(f"token: {secret}\n", encoding="utf-8")

    result = validator.validate_vault(root)

    output = capsys.readouterr().out
    assert result == 1
    assert secret not in output
    assert "<redacted-secret>" in output
    assert "quarantine_candidate:Command-Center/Personal-Corpus/Notes/<redacted-secret>.md:secret_like" in output
