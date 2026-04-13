from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LSPClient:
    repo_root: Path
    command: list[str] | None = None

    def is_available(self) -> bool:
        return bool(self.command)

    def resolve_symbol_calls(self, _file_path: str, _line: int, _character: int) -> list[str]:
        if not self.command:
            raise RuntimeError("LSP command not configured.")
        # Placeholder API contract for Phase 6 wiring.
        return []

