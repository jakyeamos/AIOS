from __future__ import annotations

from .base import BackendResult


class LSPBackend:
    name = "lsp"
    confidence_floor = 0.90

    def __init__(self, client) -> None:
        self.client = client

    def is_available(self, repo_id: str) -> bool:
        _ = repo_id
        return self.client.is_available()

    def resolve_calls(self, file_path: str, line: int, character: int = 0) -> BackendResult:
        if not self.client.is_available():
            return BackendResult(
                backend=self.name,
                confidence_floor=self.confidence_floor,
                items=[],
                warnings=["LSP backend unavailable."],
            )
        symbols = self.client.resolve_symbol_calls(file_path, line, character)
        return BackendResult(
            backend=self.name,
            confidence_floor=self.confidence_floor,
            items=[{"resolved_symbols": symbols}],
        )

