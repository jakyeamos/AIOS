from __future__ import annotations

import base64
import re
from dataclasses import replace
from typing import Any

from services.session_providers.base import JsonObject, NormalizedSession

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("bearer_token", re.compile(r"Bearer [A-Za-z0-9._-]{10,}")),
    ("auth_header", re.compile(r"Authorization: [^\n]+", re.IGNORECASE)),
    ("env_secret", re.compile(r"\b[A-Z_]{3,}=[A-Za-z0-9._~\-+/]{8,}")),
    ("pem_key", re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", re.DOTALL)),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("slack_token", re.compile(r"xoxb-[0-9]+-[A-Za-z0-9]+")),
)

OPAQUE_SECRET_HINTS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^[A-Za-z0-9+/]{80,}={0,2}$"),
    re.compile(r"^[A-Fa-f0-9]{96,}$"),
)


def redact_session(normalized: NormalizedSession) -> NormalizedSession:
    """Return a redacted copy of a normalized session without DB or file access."""

    redaction_incomplete = normalized.redaction_incomplete
    title, title_incomplete = redact_value(normalized.title)
    redaction_incomplete = redaction_incomplete or title_incomplete

    messages, messages_incomplete = redact_json_list(normalized.messages)
    tool_calls, tool_calls_incomplete = redact_json_list(normalized.tool_calls)
    file_edits, file_edits_incomplete = redact_json_list(normalized.file_edits)
    commands_run, commands_incomplete = redact_string_list(normalized.commands_run)
    decisions, decisions_incomplete = redact_string_list(normalized.decisions_extracted)
    todos, todos_incomplete = redact_string_list(normalized.todos_extracted)
    errors, errors_incomplete = redact_string_list(normalized.errors_extracted)

    redaction_incomplete = redaction_incomplete or any(
        [
            messages_incomplete,
            tool_calls_incomplete,
            file_edits_incomplete,
            commands_incomplete,
            decisions_incomplete,
            todos_incomplete,
            errors_incomplete,
        ]
    )

    summary_status = normalized.summary_status
    writeback_status = normalized.writeback_status
    if redaction_incomplete:
        summary_status = "redaction_incomplete"
        writeback_status = "redaction_incomplete"

    return replace(
        normalized,
        title=str(title),
        messages=messages,
        tool_calls=tool_calls,
        file_edits=file_edits,
        commands_run=commands_run,
        decisions_extracted=decisions,
        todos_extracted=todos,
        errors_extracted=errors,
        summary_status=summary_status,
        writeback_status=writeback_status,
        redaction_incomplete=redaction_incomplete,
    )


def redact_json_list(items: list[JsonObject]) -> tuple[list[JsonObject], bool]:
    redacted: list[JsonObject] = []
    incomplete = False
    for item in items:
        value, item_incomplete = redact_value(item)
        incomplete = incomplete or item_incomplete
        redacted.append(value if isinstance(value, dict) else {"value": value})
    return redacted, incomplete


def redact_string_list(items: list[str]) -> tuple[list[str], bool]:
    redacted: list[str] = []
    incomplete = False
    for item in items:
        value, item_incomplete = redact_value(item)
        incomplete = incomplete or item_incomplete
        redacted.append(str(value))
    return redacted, incomplete


def redact_value(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, bytes):
        return "[REDACTION_INCOMPLETE:binary]", True
    if isinstance(value, list):
        redacted_items: list[Any] = []
        incomplete = False
        for item in value:
            redacted, item_incomplete = redact_value(item)
            incomplete = incomplete or item_incomplete
            redacted_items.append(redacted)
        return redacted_items, incomplete
    if isinstance(value, dict):
        redacted_dict: dict[str, Any] = {}
        incomplete = False
        for key, item in value.items():
            redacted, item_incomplete = redact_value(item)
            incomplete = incomplete or item_incomplete
            redacted_dict[str(key)] = redacted
        return redacted_dict, incomplete
    return value, False


def redact_text(text: str) -> tuple[str, bool]:
    redacted = text
    incomplete = False
    for label, pattern in SECRET_PATTERNS:
        redacted = pattern.sub(f"[REDACTED:{label}]", redacted)
    if looks_like_opaque_secret(text) and redacted == text:
        return "[REDACTION_INCOMPLETE:opaque_secret]", True
    return redacted, incomplete


def looks_like_opaque_secret(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 80 or any(char.isspace() for char in stripped):
        return False
    if any(pattern.fullmatch(stripped) for pattern in OPAQUE_SECRET_HINTS):
        return not _is_decodable_plain_text(stripped)
    return False


def _is_decodable_plain_text(value: str) -> bool:
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception:
        return False
    if not decoded:
        return False
    printable = sum(32 <= byte <= 126 or byte in {9, 10, 13} for byte in decoded)
    return printable / len(decoded) > 0.8
