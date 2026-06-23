from __future__ import annotations

from services.session_providers.antigravity import AntigravityProvider
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
from services.session_providers.cursor import CursorProvider

PROVIDERS: dict[str, type[SessionProvider]] = {
    "antigravity": AntigravityProvider,
    "claude": ClaudeProvider,
    "codex": CodexProvider,
    "cursor": CursorProvider,
}

__all__ = [
    "AntigravityProvider",
    "ClaudeProvider",
    "CodexProvider",
    "CursorProvider",
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
