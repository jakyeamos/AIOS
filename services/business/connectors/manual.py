from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from services.business.connectors.base import Connector
from services.business.models import SourceRecord
from services.business.normalize import normalize_manual_file
from services.business.paths import MANUAL_INBOX, MANUAL_PROCESSED


class ManualConnector(Connector):
    name = "manual"

    def __init__(self, inbox_path: Path | None = None) -> None:
        self.inbox_path = inbox_path or MANUAL_INBOX

    def is_configured(self) -> bool:
        return True

    def sync(self, since: datetime | None) -> list[SourceRecord]:
        if not self.inbox_path.exists():
            self.inbox_path.mkdir(parents=True, exist_ok=True)
            return []

        fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        records: list[SourceRecord] = []
        for path in sorted(self.inbox_path.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".txt", ".json"}:
                continue
            record = normalize_manual_file(path, fetched_at=fetched_at)
            if since is not None:
                occurred = datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
                if occurred < since.astimezone(UTC):
                    continue
            records.append(record)
        return records

    def mark_processed(self, source_path: Path) -> Path:
        MANUAL_PROCESSED.mkdir(parents=True, exist_ok=True)
        dest = MANUAL_PROCESSED / source_path.name
        if dest.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            counter = 1
            while dest.exists():
                dest = MANUAL_PROCESSED / f"{stem}-{counter}{suffix}"
                counter += 1
        source_path.rename(dest)
        return dest
