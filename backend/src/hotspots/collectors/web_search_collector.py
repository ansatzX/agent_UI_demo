"""Web search collector — wraps WebSearchTool as a hotspot data source."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import SourceItem

if TYPE_CHECKING:
    from ...services.tools.web_search import WebSearchTool


class WebSearchCollector:
    """General web search collector for hotspot inspection."""

    def __init__(self, web_search: WebSearchTool):
        self._search = web_search

    async def collect(self, keywords: str, limit: int = 10, days: int = 1) -> list[SourceItem]:
        if self._search is None:
            return []

        result = await self._search.execute(
            query=f"{keywords} 热点新闻 {days}天",
            max_results=limit,
            fetch_full=False,
        )

        if not result.success:
            return []

        items: list[SourceItem] = []
        for r in result.output.get("results", [])[:limit]:
            items.append(
                SourceItem(
                    source="web",
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    summary=r.get("content", "")[:300],
                    heat=0.5,
                    evidence_tier=r.get("evidence_tier", "news_report"),
                )
            )
        return items
