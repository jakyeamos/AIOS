from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class BackendResult:
    backend: str
    confidence_floor: float
    items: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class CTSBackend(Protocol):
    name: str
    confidence_floor: float

    def is_available(self, repo_id: str) -> bool: ...
