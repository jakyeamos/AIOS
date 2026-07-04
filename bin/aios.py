#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
UV_BOOTSTRAP_ENV = "AIOS_UV_BOOTSTRAPPED"


def _restart_in_project_venv() -> None:
    if not VENV_PYTHON.exists():
        return
    if Path(sys.executable).resolve() == VENV_PYTHON.resolve():
        return
    import os

    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])


def _restart_with_uv() -> None:
    import os
    import shutil

    if os.environ.get(UV_BOOTSTRAP_ENV) == "1":
        return
    uv_path = shutil.which("uv")
    if uv_path is None:
        return
    env = os.environ.copy()
    env[UV_BOOTSTRAP_ENV] = "1"
    os.execve(
        uv_path, [uv_path, "run", "python", str(Path(__file__).resolve()), *sys.argv[1:]], env
    )


def _load_main():
    _restart_in_project_venv()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from services.aios_cli import main
    except ModuleNotFoundError:
        _restart_with_uv()
        raise

    return main


if __name__ == "__main__":
    _load_main()()
