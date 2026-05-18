from __future__ import annotations

import os
from pathlib import Path

CANONICAL_VAULT_ROOT = Path.home() / "projects" / "Vaults" / "Command-Center"
LEGACY_VAULT_ROOT = Path.home() / "Vaults" / "Command-Center"


def get_vault_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env_root = os.environ.get("AIOS_VAULT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    candidates = [
        CANONICAL_VAULT_ROOT,
        LEGACY_VAULT_ROOT,
    ]
    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate.resolve()
    return CANONICAL_VAULT_ROOT.resolve()


def get_vault_subpath(*parts: str, explicit: str | None = None) -> Path:
    return get_vault_root(explicit).joinpath(*parts)


def rewrite_legacy_vault_path(path: str | None, *, explicit: str | None = None) -> str | None:
    if not path:
        return path
    legacy_root = str(LEGACY_VAULT_ROOT.resolve())
    current_root = str(get_vault_root(explicit))
    if path.startswith(legacy_root):
        return current_root + path[len(legacy_root):]
    return path
