#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_main():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from services.aios_cli import main

    return main


if __name__ == "__main__":
    _load_main()()
