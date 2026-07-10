from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from services.business.models import SourceRecord


class Connector(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def sync(self, since: datetime | None) -> list[SourceRecord]: ...
