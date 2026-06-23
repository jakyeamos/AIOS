from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

JsonObject = dict[str, object]
SessionStatus = Literal[
    "pending",
    "imported",
    "summarized",
    "writeback_pending",
    "redaction_incomplete",
    "failed",
]


@dataclass(frozen=True)
class SourcePath:
    """Provider source file plus optional provider-specific metadata."""

    path: Path
    source_type: str
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderCursor:
    """Last observed state for one provider source."""

    provider_id: str
    source_path: str
    last_mtime: float | None = None
    last_size: int | None = None
    last_hash: str | None = None
    last_provider_session_id: str | None = None
    last_scanned_at: str | None = None


@dataclass(frozen=True)
class RawSession:
    """Unnormalized provider payload read from a source."""

    provider: str
    source: SourcePath
    payload: JsonObject
    raw_text: str | None = None


@dataclass(frozen=True)
class NormalizedSession:
    """Provider-independent session shape stored and summarized by AIOS."""

    provider: str
    stable_session_id: str
    provider_session_id: str
    workspace_path: str | None
    workspace_id: str | None
    project_id: str | None
    started_at: str | None
    updated_at: str | None
    imported_at: str
    source_files: list[str]
    source_file_mtimes: dict[str, float]
    content_hash: str
    title: str
    participants: list[str]
    messages: list[JsonObject]
    tool_calls: list[JsonObject]
    file_edits: list[JsonObject]
    commands_run: list[str]
    decisions_extracted: list[str]
    todos_extracted: list[str]
    errors_extracted: list[str]
    summary_status: SessionStatus
    writeback_status: SessionStatus
    confidence: float
    provider_metadata: JsonObject = field(default_factory=dict)
    redaction_incomplete: bool = False

    def with_status(
        self,
        *,
        summary_status: SessionStatus | None = None,
        writeback_status: SessionStatus | None = None,
        redaction_incomplete: bool | None = None,
    ) -> NormalizedSession:
        """Return a copy with updated workflow status fields."""

        return replace(
            self,
            summary_status=summary_status or self.summary_status,
            writeback_status=writeback_status or self.writeback_status,
            redaction_incomplete=(
                self.redaction_incomplete if redaction_incomplete is None else redaction_incomplete
            ),
        )


@dataclass(frozen=True)
class SummaryResult:
    """Result of summarizing a normalized session."""

    session_id: str
    status: SessionStatus
    summary: JsonObject
    confidence: float


@dataclass(frozen=True)
class WritebackCandidate:
    """Governed proposal emitted for reviewable downstream writeback."""

    session_id: str
    candidate_type: str
    destination: str
    payload: JsonObject
    status: Literal["pending", "approved", "rejected", "held"] = "pending"


@dataclass(frozen=True)
class HealthStatus:
    """Provider reachability and source inventory without private content."""

    provider_id: str
    ok: bool
    source_counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class SessionProvider(ABC):
    """Base interface implemented by every local session provider."""

    provider_id: str

    @abstractmethod
    def discover_sources(self) -> list[SourcePath]:
        """Find all candidate source files, directories, or databases."""

    @abstractmethod
    def scan_since(self, last_cursor: ProviderCursor) -> list[SourcePath]:
        """Return sources changed since the last recorded cursor."""

    @abstractmethod
    def extract_raw_session(self, source: SourcePath) -> RawSession:
        """Read provider-specific content from one source."""

    @abstractmethod
    def normalize_session(self, raw: RawSession) -> NormalizedSession:
        """Convert provider-specific content into a normalized session."""

    @abstractmethod
    def compute_fingerprint(self, normalized: NormalizedSession) -> str:
        """Compute a stable content fingerprint for deduplication."""

    @abstractmethod
    def upsert_session(self, normalized: NormalizedSession) -> str:
        """Persist the session and return its stable session id."""

    @abstractmethod
    def summarize_session(self, session_id: str) -> SummaryResult:
        """Generate a structured summary for a persisted session."""

    @abstractmethod
    def emit_writeback_candidates(self, session_id: str) -> list[WritebackCandidate]:
        """Create governed writeback proposals for a persisted session."""

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Report source reachability and counts without private content."""
