from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceAnalysis:
    source_id: str
    summary: str
    key_quote: str
    business_relevance: str
    concepts: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    excitement_signals: list[str] = field(default_factory=list)
    sentiment: str | None = None
    confidence: float = 0.7
    provider: str = "skipped"

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "summary": self.summary,
            "key_quote": self.key_quote,
            "business_relevance": self.business_relevance,
            "concepts": self.concepts,
            "objections": self.objections,
            "excitement_signals": self.excitement_signals,
            "sentiment": self.sentiment,
            "confidence": self.confidence,
            "provider": self.provider,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SourceAnalysis:
        return cls(
            source_id=str(data["source_id"]),
            summary=str(data.get("summary") or ""),
            key_quote=str(data.get("key_quote") or ""),
            business_relevance=str(data.get("business_relevance") or ""),
            concepts=[str(item) for item in data.get("concepts") or []],
            objections=[str(item) for item in data.get("objections") or []],
            excitement_signals=[str(item) for item in data.get("excitement_signals") or []],
            sentiment=data.get("sentiment"),
            confidence=float(data.get("confidence") or 0.7),
            provider=str(data.get("provider") or "unknown"),
        )
