from __future__ import annotations

from collections import Counter
from statistics import mean

from .models import (
    ConfidenceSummary,
    CTSNode,
    ExtractionMethod,
    ResolutionMethod,
    TrustLevel,
)

LOW_CONFIDENCE_THRESHOLD = 0.60
GRAPH_ONLY_THRESHOLD = 0.75

NODE_CONFIDENCE_DEFAULTS: dict[ExtractionMethod, float] = {
    ExtractionMethod.LSP: 0.95,
    ExtractionMethod.TREE_SITTER: 0.75,
    ExtractionMethod.INFERRED: 0.50,
    ExtractionMethod.MANUAL: 1.00,
}

EDGE_CONFIDENCE_DEFAULTS: dict[tuple[ExtractionMethod, ResolutionMethod], float] = {
    (ExtractionMethod.LSP, ResolutionMethod.LSP): 0.90,
    (ExtractionMethod.TREE_SITTER, ResolutionMethod.STATIC): 0.70,
    (ExtractionMethod.TREE_SITTER, ResolutionMethod.ALIAS_RESOLVED): 0.70,
    (ExtractionMethod.TREE_SITTER, ResolutionMethod.UNRESOLVED): 0.40,
    (ExtractionMethod.INFERRED, ResolutionMethod.INFERRED): 0.40,
    (ExtractionMethod.MANUAL, ResolutionMethod.STATIC): 1.00,
}


def default_node_confidence(extraction_method: ExtractionMethod) -> float:
    return NODE_CONFIDENCE_DEFAULTS.get(extraction_method, 0.50)


def default_edge_confidence(
    extraction_method: ExtractionMethod,
    resolution_method: ResolutionMethod,
) -> float:
    return EDGE_CONFIDENCE_DEFAULTS.get(
        (extraction_method, resolution_method),
        0.40,
    )


def classify_trust_level(node: CTSNode, unresolved_threshold: int = 5) -> TrustLevel:
    if node.is_stale:
        return TrustLevel.STALE
    if node.extraction_method == ExtractionMethod.LSP and node.confidence >= 0.85:
        return TrustLevel.STRUCTURAL_FACT
    if (
        node.extraction_method == ExtractionMethod.TREE_SITTER
        and node.confidence >= LOW_CONFIDENCE_THRESHOLD
        and node.unresolved_call_count <= unresolved_threshold
    ):
        return TrustLevel.INFERRED_RELATION
    return TrustLevel.SEMANTICALLY_DEGRADED


def summarize_nodes(nodes: list[CTSNode]) -> ConfidenceSummary:
    if not nodes:
        return ConfidenceSummary(
            mean=0.0,
            min=0.0,
            max=0.0,
            low_confidence_count=0,
            stale_count=0,
            total=0,
            trust_level_counts={},
        )
    confidences = [n.confidence for n in nodes]
    trust_counts = Counter(classify_trust_level(n).value for n in nodes)
    low_count = sum(1 for n in nodes if n.confidence < LOW_CONFIDENCE_THRESHOLD)
    stale_count = sum(1 for n in nodes if n.is_stale)
    return ConfidenceSummary(
        mean=mean(confidences),
        min=min(confidences),
        max=max(confidences),
        low_confidence_count=low_count,
        stale_count=stale_count,
        total=len(nodes),
        trust_level_counts=dict(trust_counts),
    )


def confidence_note(summary: ConfidenceSummary, unresolved_call_count: int) -> str | None:
    if summary.total == 0:
        return "No indexed structure available for this query."
    notes: list[str] = []
    if summary.stale_count > 0:
        notes.append(f"{summary.stale_count} stale nodes")
    if summary.low_confidence_count > 0:
        notes.append(f"{summary.low_confidence_count} low-confidence nodes")
    if unresolved_call_count > 0:
        notes.append(f"{unresolved_call_count} unresolved call edges")
    if not notes:
        return None
    return "; ".join(notes)
