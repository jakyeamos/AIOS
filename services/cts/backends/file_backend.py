from __future__ import annotations

import subprocess
from pathlib import Path

from .base import BackendResult


class FileBackend:
    name = "file"
    confidence_floor = 0.20

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def is_available(self, repo_id: str) -> bool:
        return self.repo_path.exists()

    def search(self, query: str, limit: int = 20) -> BackendResult:
        cmd = [
            "rg",
            "-n",
            "--no-heading",
            "--max-count",
            str(limit),
            query,
            str(self.repo_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        except FileNotFoundError:
            return BackendResult(
                backend=self.name,
                confidence_floor=self.confidence_floor,
                items=[],
                warnings=["ripgrep not available for file fallback search."],
            )
        lines = proc.stdout.strip().splitlines() if proc.returncode in (0, 1) else []
        items = []
        for line in lines[:limit]:
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue
            items.append(
                {
                    "file_path": parts[0],
                    "line": int(parts[1]) if parts[1].isdigit() else 0,
                    "preview": parts[2].strip(),
                    "score": 0.25,
                    "source": "file_exploration",
                }
            )
        return BackendResult(
            backend=self.name,
            confidence_floor=self.confidence_floor,
            items=items,
            warnings=[] if items else ["File fallback returned no results."],
        )
