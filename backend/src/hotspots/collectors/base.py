from __future__ import annotations

from typing import Protocol

from ..models import SourceItem


class HotspotCollector(Protocol):
    async def collect(self, keywords: str, limit: int = 10, days: int = 1) -> list[SourceItem]:
        ...
