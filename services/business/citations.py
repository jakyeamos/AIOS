from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime


def content_hash(body_text: str, source_type: str, external_id: str | None = None) -> str:
    payload = f"{source_type}\0{external_id or ''}\0{body_text}".encode()
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def short_hash(content_hash_value: str) -> str:
    digest = content_hash_value.removeprefix("sha256:")
    return digest[:6]


def make_source_id(source_type: str, occurred_at_iso: str, content_hash_value: str) -> str:
    date = occurred_at_iso[:10].replace("-", "_")
    return f"src_{source_type}_{date}_{short_hash(content_hash_value)}"


def citation_token(source_id: str) -> str:
    return f"[src:{source_id.removeprefix('src_')}]"


def parse_occurred_at(value: str | None, fallback: datetime | None = None) -> str:
    if value:
        normalized = value.replace("Z", "+00:00")
        try:
            return (
                datetime.fromisoformat(normalized)
                .astimezone(UTC)
                .replace(microsecond=0)
                .isoformat()
            )
        except ValueError:
            pass
    when = fallback or datetime.now(UTC)
    return when.replace(microsecond=0).isoformat()


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_len: int = 80) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug[:max_len] or "untitled"
