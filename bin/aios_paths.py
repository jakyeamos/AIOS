#!/usr/bin/env python3
"""
Shared path resolution for AIOS local stores.

`AIOS_VAULT_ROOT` overrides auto-detection. Without it, prefer the newer
project-scoped vault and fall back to the legacy root only if needed.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_vault_root() -> Path:
    env_root = os.environ.get("AIOS_VAULT_ROOT")
    candidates = [
        Path(env_root).expanduser() if env_root else None,
        Path.home() / "projects" / "Vaults" / "Command-Center",
        Path.home() / "Vaults" / "Command-Center",
    ]
    for candidate in candidates:
        if candidate and candidate.is_dir():
            return candidate.resolve()
    return (Path.home() / "projects" / "Vaults" / "Command-Center").resolve()


def get_vault_subpath(*parts: str) -> Path:
    return get_vault_root().joinpath(*parts)


def rewrite_legacy_vault_path(path: str | None) -> str | None:
    if not path:
        return path
    legacy_root = str((Path.home() / "Vaults" / "Command-Center").resolve())
    current_root = str(get_vault_root())
    if path.startswith(legacy_root):
        return current_root + path[len(legacy_root):]
    return path
