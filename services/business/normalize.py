from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from services.business.citations import content_hash, make_source_id, parse_occurred_at
from services.business.models import SourceRecord

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


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
            return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def normalize_manual_file(path: Path, *, fetched_at: str | None = None) -> SourceRecord:
    text = path.read_text(encoding="utf-8")
    fetched = fetched_at or datetime.now(UTC).replace(microsecond=0).isoformat()

    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if "source_id" in data and "hash" in data:
            return SourceRecord.from_json_dict(data)
        body = str(data.get("body_text") or data.get("body") or "")
        occurred = parse_occurred_at(data.get("timestamp"))
        digest = content_hash(body, "manual", data.get("external_id"))
        source_id = make_source_id("manual", occurred, digest)
        return SourceRecord(
            source_id=source_id,
            source_type="manual",
            external_id=data.get("external_id"),
            author_name=data.get("author_name"),
            author_handle=data.get("author_handle"),
            timestamp=occurred,
            fetched_at=fetched,
            channel_or_thread=data.get("channel_or_thread"),
            subject_or_title=data.get("subject_or_title") or data.get("title"),
            body_text=body,
            url=data.get("url"),
            attachments=list(data.get("attachments") or []),
            tags=list(data.get("tags") or []),
            hash=digest,
            privacy_level=str(data.get("privacy_level") or "internal"),
        )

    fields, body = _parse_simple_frontmatter(text)
    subject = fields.get("subject_or_title") or fields.get("title") or path.stem.replace("-", " ")
    occurred = parse_occurred_at(fields.get("timestamp") or fields.get("date"))
    digest = content_hash(body, "manual", path.name)
    source_id = make_source_id("manual", occurred, digest)
    return SourceRecord(
        source_id=source_id,
        source_type="manual",
        external_id=fields.get("external_id") or path.name,
        author_name=fields.get("author_name"),
        author_handle=fields.get("author_handle"),
        timestamp=occurred,
        fetched_at=fetched,
        channel_or_thread=fields.get("channel_or_thread"),
        subject_or_title=subject,
        body_text=body.strip(),
        url=fields.get("url"),
        attachments=[],
        tags=_tags_from_frontmatter(fields),
        hash=digest,
        privacy_level=fields.get("privacy_level") or "internal",
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
