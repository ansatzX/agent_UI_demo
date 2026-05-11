from __future__ import annotations

import os
import re
from typing import Callable, List
import logging

import httpx

logger = logging.getLogger(__name__)

from ..models import SourceItem


class JinaDeepSearchCollector:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "jina-deepsearch-v1",
        timeout: float | None = None,
        http_client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ):
        self.api_key = api_key or os.getenv("AIHUBMIX_API_KEY")
        self.base_url = (base_url or os.getenv("AIHUBMIX_BASE_URL") or "https://aihubmix.com/v1").rstrip("/")
        self.model = model
        self.timeout = timeout or float(os.getenv("JINA_DEEPSEARCH_TIMEOUT", "180"))
        self.http_client_factory = http_client_factory

    async def collect(self, keywords: str, limit: int = 10, days: int = 1) -> List[SourceItem]:
        if not self.api_key:
            return []

        prompt = (
            f"请搜索并整理最近{days}天内与以下关键词相关的中文热点新闻/讨论：{keywords}\n"
            f"最多返回{limit}条。每条包含标题、摘要、热度线索、来源线索。"
        )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            async with self.http_client_factory(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            logger.warning("Jina DeepSearch request failed: %s: %s", type(e).__name__, str(e) or repr(e))
            return []

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _parse_deepsearch_content(content, limit=limit)


def _parse_deepsearch_content(content: str, limit: int) -> List[SourceItem]:
    blocks = [b.strip() for b in re.split(r"\n(?=#{1,3}\s|\d+[\.、]\s)", content) if b.strip()]
    if not blocks and content.strip():
        blocks = [content.strip()]

    items: list[SourceItem] = []
    for block in blocks[:limit]:
        lines = [line.strip(" #-\t") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        title = re.sub(r"^\d+[\.、]\s*", "", lines[0]).strip()
        summary = "\n".join(lines[1:]).strip() or title
        items.append(SourceItem(source="jina-deepsearch", title=title, summary=summary, heat=0.65, evidence_tier="inference", raw={"content": block}))
    return items
