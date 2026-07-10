from __future__ import annotations

from abc import ABC, abstractmethod

from services.business.llm.models import SourceAnalysis
from services.business.sources_db import DbSource


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def analyze_source(self, source: DbSource) -> SourceAnalysis | None: ...

    def analyze_batch(self, sources: list[DbSource]) -> dict[str, SourceAnalysis]:
        results: dict[str, SourceAnalysis] = {}
        for source in sources:
            analysis = self.analyze_source(source)
            if analysis:
                results[source.source_id] = analysis
        return results
