#!/usr/bin/env python3
"""Script-facing wrapper for shared AIOS local path resolution."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.path_resolution import (  # noqa: E402
    get_vault_root,
    get_vault_subpath,
    rewrite_legacy_vault_path,
)

__all__ = ["get_vault_root", "get_vault_subpath", "rewrite_legacy_vault_path"]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "vault-root"
    if command == "vault-root":
        print(get_vault_root())
        return 0
    if command == "vault-subpath":
        print(get_vault_subpath(*args[1:]))
        return 0
    print("Usage: aios_paths.py [vault-root|vault-subpath <parts...>]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
