from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EmbeddingAdapter:
    provider: str | None = None

    def is_available(self) -> bool:
        return self.provider is not None

    def embed(self, text: str) -> list[float]:
        if not self.provider:
            raise RuntimeError("No embeddings provider configured.")
        # Placeholder deterministic vector until provider wiring is configured.
        seed = sum(ord(ch) for ch in text)
        return [float((seed + i) % 101) / 100.0 for i in range(32)]

