from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

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

AIOS_ROOT = Path(__file__).resolve().parents[2]
IMPORT_AI_HISTORY_PATH = AIOS_ROOT / "bin" / "import_ai_history.py"


def _load_import_ai_history() -> ModuleType:
    spec = importlib.util.spec_from_file_location("aios_import_ai_history", IMPORT_AI_HISTORY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {IMPORT_AI_HISTORY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _now() -> str:
    return datetime.now(UTC).isoformat()


class CodexProvider(SessionProvider):
    """Adapter over the existing Codex rollout import parser."""

    provider_id = "codex"

    def __init__(
        self,
        *,
        source_root: Path | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.source_root = source_root or Path.home() / ".codex" / "sessions"
        self.db_path = db_path or Path.home() / "AIOS" / "data" / "aios.db"
        self._import_ai_history = _load_import_ai_history()

    def discover_sources(self) -> list[SourcePath]:
        if not self.source_root.exists():
            return []
        return [
            SourcePath(path=path, source_type="codex_rollout_jsonl")
            for path in sorted(self.source_root.glob("**/*.jsonl"))
            if path.name != "session_index.jsonl"
        ]

    def scan_since(self, last_cursor: ProviderCursor) -> list[SourcePath]:
        changed: list[SourcePath] = []
        for source in self.discover_sources():
            stat = source.path.stat()
            if (
                str(source.path) == last_cursor.source_path
                and last_cursor.last_mtime is not None
                and stat.st_mtime <= last_cursor.last_mtime
                and stat.st_size == last_cursor.last_size
            ):
                continue
            changed.append(source)
        return changed

    def extract_raw_session(self, source: SourcePath) -> RawSession:
        title_index = self._import_ai_history.load_codex_title_index(source.path)
        session = self._import_ai_history.load_codex_rollout(source.path, title_index)
        if session is None:
            return RawSession(provider=self.provider_id, source=source, payload={})
        return RawSession(provider=self.provider_id, source=source, payload=session)

    def normalize_session(self, raw: RawSession) -> NormalizedSession:
        session_id = str(raw.payload.get("session_id") or raw.source.path.stem)
        raw_messages = raw.payload.get("messages")
        messages: list[dict[str, object]] = []
        if isinstance(raw_messages, list):
            for message in raw_messages:
                if not isinstance(message, dict):
                    continue
                messages.append(
                    {
                        "role": str(message.get("role") or ""),
                        "phase": str(message.get("phase") or ""),
                        "text": str(message.get("text") or ""),
                    }
                )
        content_hash = self.compute_fingerprint_from_payload(raw.payload)
        source_path = str(raw.source.path)
        stat = raw.source.path.stat()
        return NormalizedSession(
            provider=self.provider_id,
            stable_session_id=f"{self.provider_id}:{session_id}",
            provider_session_id=session_id,
            workspace_path=None,
            workspace_id=None,
            project_id=None,
            started_at=str(raw.payload.get("created_at") or "") or None,
            updated_at=str(raw.payload.get("created_at") or "") or None,
            imported_at=_now(),
            source_files=[source_path],
            source_file_mtimes={source_path: stat.st_mtime},
            content_hash=content_hash,
            title=str(raw.payload.get("title") or session_id),
            participants=["user", "assistant"],
            messages=messages,
            tool_calls=[],
            file_edits=[],
            commands_run=[],
            decisions_extracted=[],
            todos_extracted=[],
            errors_extracted=[],
            summary_status="pending",
            writeback_status="pending",
            confidence=0.6 if messages else 0.0,
            provider_metadata={
                "source": raw.payload.get("source"),
                "model_provider": raw.payload.get("model_provider"),
                "rollout_path": raw.payload.get("rollout_path"),
            },
        )

    def compute_fingerprint(self, normalized: NormalizedSession) -> str:
        payload = {
            "provider": normalized.provider,
            "provider_session_id": normalized.provider_session_id,
            "messages": normalized.messages,
            "source_files": normalized.source_files,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def compute_fingerprint_from_payload(self, payload: dict[str, object]) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def upsert_session(self, normalized: NormalizedSession) -> str:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    id, project_id, tool, started_at, ended_at, objective, status, cwd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    started_at = excluded.started_at,
                    objective = excluded.objective,
                    cwd = excluded.cwd
                """,
                (
                    normalized.stable_session_id,
                    normalized.project_id or "project-aios",
                    "codex",
                    normalized.started_at or normalized.imported_at,
                    normalized.updated_at,
                    normalized.title,
                    "closed",
                    normalized.workspace_path,
                ),
            )
        return normalized.stable_session_id

    def summarize_session(self, session_id: str) -> SummaryResult:
        return SummaryResult(session_id=session_id, status="pending", summary={}, confidence=0.0)

    def emit_writeback_candidates(self, session_id: str) -> list[WritebackCandidate]:
        return []

    def health_check(self) -> HealthStatus:
        sources = self.discover_sources()
        warnings = [] if self.source_root.exists() else [f"Missing source root: {self.source_root}"]
        return HealthStatus(
            provider_id=self.provider_id,
            ok=self.source_root.exists(),
            source_counts={"codex_rollout_jsonl": len(sources)},
            warnings=warnings,
        )
