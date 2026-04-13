from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class NodeKind(StrEnum):
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    TYPE = "Type"
    TEST = "Test"


class EdgeKind(StrEnum):
    CALLS = "CALLS"
    IMPORTS_FROM = "IMPORTS_FROM"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    CONTAINS = "CONTAINS"
    TESTED_BY = "TESTED_BY"
    DEPENDS_ON = "DEPENDS_ON"


class ExtractionMethod(StrEnum):
    TREE_SITTER = "tree_sitter"
    LSP = "lsp"
    INFERRED = "inferred"
    MANUAL = "manual"


class ResolutionMethod(StrEnum):
    STATIC = "static"
    ALIAS_RESOLVED = "alias_resolved"
    LSP = "lsp"
    UNRESOLVED = "unresolved"
    INFERRED = "inferred"


class IndexStatus(StrEnum):
    CURRENT = "current"
    NEEDS_UPDATE = "needs_update"
    BUILDING = "building"
    FAILED = "failed"
    EMPTY = "empty"


class FallbackType(StrEnum):
    FTS = "fts"
    FILE_EXPLORATION = "file_exploration"


class TrustLevel(StrEnum):
    STRUCTURAL_FACT = "Structural fact"
    INFERRED_RELATION = "Inferred relation"
    SEMANTICALLY_DEGRADED = "Semantically degraded"
    STALE = "Stale / unreliable"


class FallbackReason(StrEnum):
    STALE_INDEX = "stale_index"
    LOW_CONFIDENCE = "low_confidence"
    NOT_INDEXED = "not_indexed"
    LSP_UNAVAILABLE = "lsp_unavailable"
    GRAPH_ERROR = "graph_error"
    NO_RESULTS = "no_results"


class FallbackAction(StrEnum):
    USE_FTS = "use_fts"
    USE_FILE_EXPLORATION = "use_file_exploration"
    REBUILD_INDEX = "rebuild_index"
    ESCALATE_TO_AGENT = "escalate_to_agent"
    VERIFY_SOURCE_BEFORE_ACTING = "verify_source_before_acting"


@dataclass(slots=True)
class CTSNode:
    id: str
    repo_id: str
    kind: NodeKind
    name: str
    qualified_name: str
    file_path: str
    line_start: int
    line_end: int
    language: str
    parent_qualified: str | None = None
    params: str | None = None
    return_type: str | None = None
    modifiers: list[str] = field(default_factory=list)
    is_test: bool = False
    file_hash: str = ""
    confidence: float = 0.0
    extraction_method: ExtractionMethod = ExtractionMethod.INFERRED
    last_verified_at: str | None = None
    is_stale: bool = False
    unresolved_call_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


@dataclass(slots=True)
class CTSEdge:
    id: str
    repo_id: str
    kind: EdgeKind
    source_qualified: str
    target_qualified: str
    file_path: str
    line: int
    confidence: float
    resolution_method: ResolutionMethod
    extraction_method: ExtractionMethod
    last_verified_at: str | None = None
    is_stale: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    updated_at: str = ""


@dataclass(slots=True)
class ConfidenceSummary:
    mean: float
    min: float
    max: float
    low_confidence_count: int
    stale_count: int
    total: int
    trust_level_counts: dict[str, int]


@dataclass(slots=True)
class CTSQueryResult:
    query_type: str
    repo_id: str
    index_age_seconds: int
    index_status: IndexStatus
    coverage_pct: float
    has_low_confidence_results: bool
    has_stale_results: bool
    fallback_used: FallbackType | None
    confidence_summary: ConfidenceSummary
    warnings: list[str]
    results: list[dict[str, Any]]
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MinimalContextBundle:
    repo_name: str
    index_status: IndexStatus
    architecture_summary: str
    directly_relevant_nodes: list[str]
    estimated_blast_radius: int
    confidence_note: str | None
    suggested_next_tools: list[str]


@dataclass(slots=True)
class BlastRadiusResult:
    changed_nodes: list[CTSNode]
    impacted_nodes: list[CTSNode]
    impacted_files: list[str]
    edges: list[CTSEdge]
    truncated: bool
    total_impacted: int
    risk_summary: dict[str, Any]
    low_confidence_count: int
    stale_count: int
    unindexed_changed_files: list[str]


@dataclass(slots=True)
class FallbackTrigger:
    reason: FallbackReason
    affected_files: list[str]
    recommended_action: FallbackAction
    confidence_at_trigger: float

