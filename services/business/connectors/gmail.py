from __future__ import annotations

import os
from datetime import datetime

from services.business.connectors.base import Connector
from services.business.models import SourceRecord


class GmailConnector(Connector):
    name = "gmail"

    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    def is_configured(self) -> bool:
        if not self._config.get("enabled", False):
            return False
        return bool(
            os.environ.get("GMAIL_CLIENT_ID")
            and os.environ.get("GMAIL_CLIENT_SECRET")
            and os.environ.get("GMAIL_REFRESH_TOKEN")
        )

    def sync(self, since: datetime | None) -> list[SourceRecord]:
        if not self.is_configured():
            return []
        raise NotImplementedError(
            "Gmail connector skeleton only — configure GMAIL_CLIENT_ID, "
            "GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN for future sync"
        )
