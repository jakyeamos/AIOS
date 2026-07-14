from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from services.business.citations import content_hash, make_source_id, parse_occurred_at
from services.business.models import SourceRecord
from services.capture_v1 import CaptureInputError, build_capture, validate_capture_envelope

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MANUAL_SOURCE_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".json", ".html", ".htm", ".csv"})


def _parse_simple_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    body = text[match.end() :].lstrip()
    return fields, body


def _tags_from_frontmatter(fields: dict[str, str]) -> list[str]:
    raw = fields.get("tags", "")
    if not raw:
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            return [str(item) for item in parsed]
        except json.JSONDecodeError:
            raw = raw.strip("[]")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _tags_from_value(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return _tags_from_frontmatter({"tags": value})
    return []


def _attachments_from_value(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _capture_adapter_payload(
    *,
    input_format: str,
    content: str,
    source_uri: str | None,
    metadata: Mapping[str, object],
    path: Path,
    captured_at: str,
) -> dict[str, object]:
    return {
        "source": {
            "provider": "business.manual",
            "input_format": input_format,
            "source_uri": source_uri,
            "content": content,
        },
        "metadata": dict(metadata),
        "adapter": {
            "name": "business.manual",
            "version": "capture.v1",
            "trigger": "manual-inbox",
            "field_sources": [
                {"canonical_field": "body_text", "source_expression": "source.content"},
                {"canonical_field": "subject_or_title", "source_expression": "metadata.title"},
            ],
        },
        "provenance": {
            "extractor": "services.business.normalize",
            "content_selector": None,
            "options": {"path": str(path), "captured_at": captured_at},
            "retries": 0,
            "profile": "business.manual",
            "removals": [],
        },
    }


def _capture_content(envelope: Mapping[str, object]) -> str:
    content = envelope.get("content")
    if not isinstance(content, Mapping):
        raise CaptureInputError("capture.v1 content must be an object")
    markdown = content.get("markdown")
    if not isinstance(markdown, str) or not markdown.strip():
        raise CaptureInputError("capture.v1 content.markdown must be non-empty")
    return markdown.strip()


def _capture_metadata(envelope: Mapping[str, object]) -> dict[str, object]:
    return {
        key: envelope[key]
        for key in ("schema_version", "source", "adapter", "provenance", "validation", "enrichment")
        if key in envelope
    }


def normalize_manual_file(path: Path, *, fetched_at: str | None = None) -> SourceRecord:
    text = path.read_text(encoding="utf-8")
    fetched = fetched_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    suffix = path.suffix.lower()
    if suffix not in MANUAL_SOURCE_SUFFIXES:
        raise CaptureInputError(f"Unsupported manual source suffix: {suffix or '<none>'}")

    if suffix == ".json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise CaptureInputError("manual JSON source must be an object")
        if "source_id" in data and "hash" in data:
            return SourceRecord.from_json_dict(data)
        fields: dict[str, object] = data
        input_format = "JSON"
        body = text
    else:
        parsed_fields, body = _parse_simple_frontmatter(text)
        fields = dict(parsed_fields)
        input_format = {
            ".md": "Markdown",
            ".markdown": "Markdown",
            ".txt": "Markdown",
            ".html": "HTML",
            ".htm": "HTML",
            ".csv": "CSV",
        }[suffix]

    external_id_value = fields.get("external_id")
    external_id = str(external_id_value) if external_id_value is not None else path.name
    source_uri_value = fields.get("url") or fields.get("source_uri")
    source_uri = str(source_uri_value) if source_uri_value is not None else None
    payload = _capture_adapter_payload(
        input_format=input_format,
        content=body,
        source_uri=source_uri,
        metadata=fields,
        path=path,
        captured_at=fetched,
    )
    envelope = build_capture(payload, captured_at=fetched, profile="business.manual")
    errors = validate_capture_envelope(envelope)
    if errors:
        raise CaptureInputError("capture.v1 validation failed: " + "; ".join(errors))
    normalized_body = _capture_content(envelope)
    source_metadata = _capture_metadata(envelope)
    subject = str(
        fields.get("subject_or_title") or fields.get("title") or path.stem.replace("-", " ")
    )
    occurred_value = fields.get("timestamp") or fields.get("date")
    occurred = parse_occurred_at(str(occurred_value) if occurred_value is not None else None)
    digest = content_hash(normalized_body, "manual", external_id)
    source_id = make_source_id("manual", occurred, digest)
    return SourceRecord(
        source_id=source_id,
        source_type="manual",
        external_id=external_id,
        author_name=str(fields["author_name"]) if fields.get("author_name") is not None else None,
        author_handle=str(fields["author_handle"]) if fields.get("author_handle") is not None else None,
        timestamp=occurred,
        fetched_at=fetched,
        channel_or_thread=(
            str(fields["channel_or_thread"])
            if fields.get("channel_or_thread") is not None
            else None
        ),
        subject_or_title=subject,
        body_text=normalized_body,
        url=source_uri,
        attachments=_attachments_from_value(fields.get("attachments")),
        tags=_tags_from_value(fields.get("tags")),
        hash=digest,
        privacy_level=str(fields.get("privacy_level") or "internal"),
        capture=source_metadata,
    )


def write_immutable_raw(record: SourceRecord, raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / f"{record.source_id}.json"
    if dest.exists():
        return dest
    dest.write_text(
        json.dumps(record.to_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return dest
