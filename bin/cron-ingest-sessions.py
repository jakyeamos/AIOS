#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = Path.home() / "AIOS" / "logs" / "cron.log"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{now_iso()} [sessions-ingest] {message}\n"
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line)
    print(line, end="")


def main() -> int:
    script = ROOT / "bin" / "sessions.py"
    command = [sys.executable, str(script), "sync", "--all"]
    log("starting all-provider session sync")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.stdout:
        log(result.stdout.strip())
    if result.stderr:
        log(result.stderr.strip())
    if result.returncode == 0:
        log("all-provider session sync complete")
        return 0
    log(f"all-provider session sync failed with exit code {result.returncode}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
