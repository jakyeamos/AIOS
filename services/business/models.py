from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceRecord:
    source_id: str
    source_type: str
    timestamp: str
    fetched_at: str
    body_text: str
    hash: str
    external_id: str | None = None
    author_name: str | None = None
    author_handle: str | None = None
    channel_or_thread: str | None = None
    subject_or_title: str | None = None
    url: str | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    privacy_level: str = "internal"
    capture: dict[str, object] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["attachments"] = list(self.attachments)
        data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> SourceRecord:
        return cls(
            source_id=str(data["source_id"]),
            source_type=str(data["source_type"]),
            external_id=data.get("external_id"),
            author_name=data.get("author_name"),
            author_handle=data.get("author_handle"),
            timestamp=str(data["timestamp"]),
            fetched_at=str(data["fetched_at"]),
            channel_or_thread=data.get("channel_or_thread"),
            subject_or_title=data.get("subject_or_title"),
            body_text=str(data.get("body_text") or ""),
            url=data.get("url"),
            attachments=list(data.get("attachments") or []),
            tags=list(data.get("tags") or []),
            hash=str(data["hash"]),
            privacy_level=str(data.get("privacy_level") or "internal"),
            capture=dict(data.get("capture") or {}),
        )


@dataclass
class IngestRunSummary:
    run_id: str
    source_type: str
    status: str
    records_fetched: int
    records_new: int
    records_duplicate: int
    errors: list[str] = field(default_factory=list)
