from __future__ import annotations

from services.session_providers.base import (
    HealthStatus,
    NormalizedSession,
    ProviderCursor,
    RawSession,
    SessionProvider,
    SourcePath,
    SummaryResult,
    WritebackCandidate,
)
from services.session_providers.claude import ClaudeProvider
from services.session_providers.codex import CodexProvider

PROVIDERS: dict[str, type[SessionProvider]] = {
    "claude": ClaudeProvider,
    "codex": CodexProvider,
}

__all__ = [
    "ClaudeProvider",
    "CodexProvider",
    "HealthStatus",
    "NormalizedSession",
    "PROVIDERS",
    "ProviderCursor",
    "RawSession",
    "SessionProvider",
    "SourcePath",
    "SummaryResult",
    "WritebackCandidate",
]
