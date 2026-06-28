#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"


def _restart_in_project_venv() -> None:
    if not VENV_PYTHON.exists():
        return
    if Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        return
    import os

    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])


def _load_main():
    _restart_in_project_venv()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from services.aios_cli import main

    return main


if __name__ == "__main__":
    _load_main()()
