from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import path_resolution  # noqa: E402


def test_vault_root_prefers_env_override(tmp_path: Path, monkeypatch) -> None:
    override = tmp_path / "custom-vault"
    monkeypatch.setenv("AIOS_VAULT_ROOT", str(override))

    assert path_resolution.get_vault_root() == override.resolve()


def test_vault_root_uses_canonical_before_legacy(tmp_path: Path, monkeypatch) -> None:
    canonical = tmp_path / "projects" / "Vaults" / "Command-Center"
    legacy = tmp_path / "Vaults" / "Command-Center"
    canonical.mkdir(parents=True)
    legacy.mkdir(parents=True)
    monkeypatch.delenv("AIOS_VAULT_ROOT", raising=False)
    monkeypatch.setattr(path_resolution, "CANONICAL_VAULT_ROOT", canonical)
    monkeypatch.setattr(path_resolution, "LEGACY_VAULT_ROOT", legacy)

    assert path_resolution.get_vault_root() == canonical.resolve()


def test_vault_root_falls_back_to_existing_legacy(tmp_path: Path, monkeypatch) -> None:
    canonical = tmp_path / "projects" / "Vaults" / "Command-Center"
    legacy = tmp_path / "Vaults" / "Command-Center"
    legacy.mkdir(parents=True)
    monkeypatch.delenv("AIOS_VAULT_ROOT", raising=False)
    monkeypatch.setattr(path_resolution, "CANONICAL_VAULT_ROOT", canonical)
    monkeypatch.setattr(path_resolution, "LEGACY_VAULT_ROOT", legacy)

    assert path_resolution.get_vault_root() == legacy.resolve()


def test_rewrite_legacy_vault_path_uses_resolved_root(tmp_path: Path, monkeypatch) -> None:
    canonical = tmp_path / "projects" / "Vaults" / "Command-Center"
    legacy = tmp_path / "Vaults" / "Command-Center"
    canonical.mkdir(parents=True)
    legacy.mkdir(parents=True)
    monkeypatch.delenv("AIOS_VAULT_ROOT", raising=False)
    monkeypatch.setattr(path_resolution, "CANONICAL_VAULT_ROOT", canonical)
    monkeypatch.setattr(path_resolution, "LEGACY_VAULT_ROOT", legacy)

    rewritten = path_resolution.rewrite_legacy_vault_path(str(legacy / "02 AI OS" / "note.md"))

    assert rewritten == str(canonical / "02 AI OS" / "note.md")


def test_aios_paths_cli_preserves_env_override(tmp_path: Path) -> None:
    override = tmp_path / "cli-vault"
    override.mkdir()
    env = {**os.environ, "AIOS_VAULT_ROOT": str(override)}

    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "aios_paths.py"), "vault-root"],
        check=True,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.stdout.strip() == str(override.resolve())
