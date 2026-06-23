# ruff: noqa: E402
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.session_providers.base import NormalizedSession
from services.session_redaction import redact_session


def _session(text: str) -> NormalizedSession:
    return NormalizedSession(
        provider="fixture",
        stable_session_id="fixture:1",
        provider_session_id="1",
        workspace_path=None,
        workspace_id=None,
        project_id=None,
        started_at=None,
        updated_at=None,
        imported_at=datetime.now(UTC).isoformat(),
        source_files=[],
        source_file_mtimes={},
        content_hash="hash",
        title=text,
        participants=["user"],
        messages=[{"text": text}],
        tool_calls=[{"command": text}],
        file_edits=[],
        commands_run=[text],
        decisions_extracted=[text],
        todos_extracted=[],
        errors_extracted=[],
        summary_status="pending",
        writeback_status="pending",
        confidence=0.7,
    )


def test_each_secret_pattern_is_replaced() -> None:
    raw = "\n".join(
        [
            "sk-" + "a" * 24,
            "Bearer abcdefghijklmnop",
            "Authorization: token abcdefgh",
            "SECRET_TOKEN=abcdefgh",
            "-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----",
            "ghp_" + "b" * 36,
            "xoxb-123-abcdef",
        ]
    )
    redacted = redact_session(_session(raw))
    combined = str(redacted)
    for label in (
        "api_key",
        "bearer_token",
        "auth_header",
        "env_secret",
        "pem_key",
        "github_token",
        "slack_token",
    ):
        assert f"[REDACTED:{label}]" in combined


def test_field_without_secret_is_unchanged() -> None:
    redacted = redact_session(_session("ordinary implementation note"))
    assert redacted.title == "ordinary implementation note"
    assert redacted.redaction_incomplete is False


def test_opaque_blob_sets_redaction_incomplete() -> None:
    redacted = redact_session(_session("A" * 100))
    assert redacted.redaction_incomplete is True
    assert redacted.summary_status == "redaction_incomplete"
    assert redacted.writeback_status == "redaction_incomplete"
