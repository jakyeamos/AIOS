from __future__ import annotations

import os
from datetime import datetime

from services.business.connectors.base import Connector
from services.business.models import SourceRecord


class XConnector(Connector):
    name = "x"

    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    def is_configured(self) -> bool:
        if not self._config.get("enabled", False):
            return False
        return bool(os.environ.get("X_BEARER_TOKEN") or os.environ.get("X_API_BEARER_TOKEN"))

    def sync(self, since: datetime | None) -> list[SourceRecord]:
        if not self.is_configured():
            return []
        raise NotImplementedError(
            "X connector skeleton only — set X_BEARER_TOKEN (official API; no scraping)"
        )
