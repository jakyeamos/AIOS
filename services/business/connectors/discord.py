from __future__ import annotations

import os
from datetime import datetime

from services.business.connectors.base import Connector
from services.business.models import SourceRecord


class DiscordConnector(Connector):
    name = "discord"

    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    def is_configured(self) -> bool:
        if not self._config.get("enabled", False):
            return False
        token = os.environ.get("DISCORD_BOT_TOKEN")
        guild_ids = self._config.get("guild_ids") or []
        channel_ids = self._config.get("channel_ids") or []
        return bool(token and (guild_ids or channel_ids))

    def sync(self, since: datetime | None) -> list[SourceRecord]:
        if not self.is_configured():
            return []
        raise NotImplementedError(
            "Discord connector skeleton only — set DISCORD_BOT_TOKEN and guild_ids/channel_ids"
        )
