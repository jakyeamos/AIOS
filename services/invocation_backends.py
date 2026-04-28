from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Transport = Literal["managed_session", "manual_session"]
Surface = Literal["codex", "claude_code", "manual"]

INVOCATION_CONTRACT_FIELDS = [
    "run_id",
    "invocation_id",
    "backend_key",
    "objective",
    "project_id",
    "workflow_key",
    "packet_id",
    "lifecycle_events",
    "artifacts",
    "closeout_evaluation",
]


@dataclass(frozen=True)
class InvocationBackend:
    key: str
    label: str
    summary: str
    transport: Transport
    surface: Surface
    supports_cancel: bool
    requires_strict_handshake: bool
    deprecated: bool = False

    def to_json(self) -> dict[str, object]:
        return asdict(self)


BACKENDS = [
    InvocationBackend(
        key="codex-managed-runtime",
        label="Codex Managed Runtime",
        summary="Managed Codex-oriented local runtime with explicit run/invocation handshake.",
        transport="managed_session",
        surface="codex",
        supports_cancel=True,
        requires_strict_handshake=True,
    ),
    InvocationBackend(
        key="claude-managed-runtime",
        label="Claude Managed Runtime",
        summary="Managed Claude-oriented local runtime using the same invocation contract.",
        transport="managed_session",
        surface="claude_code",
        supports_cancel=True,
        requires_strict_handshake=True,
    ),
    InvocationBackend(
        key="manual-session-legacy",
        label="Manual Session (Legacy)",
        summary="Deprecated manual path; allowed only with strict handshake metadata for new runs.",
        transport="manual_session",
        surface="manual",
        supports_cancel=False,
        requires_strict_handshake=True,
        deprecated=True,
    ),
]


def list_invocation_backends() -> list[InvocationBackend]:
    return BACKENDS


def get_invocation_backend(key: str) -> InvocationBackend:
    for backend in BACKENDS:
        if backend.key == key:
            return backend
    return BACKENDS[0]
