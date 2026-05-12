"""LLM-based hotspot collector — uses LLM knowledge directly."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import SourceItem

if TYPE_CHECKING:
    from ...services.llm_service import LLMService


class LLMCollector:
    """Generate hotspot topics directly from LLM knowledge.

    When web search is unavailable, use the LLM's training data to
    suggest current topics. Not a replacement for real search, but
    functional when network search is blocked.
    """

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service

    async def collect(self, keywords: str, limit: int = 10, days: int = 1) -> list[SourceItem]:
        if self._llm is None:
            return []

        prompt = f"""基于你对近期的了解，请列出与"{keywords}"相关的热点话题。

每条包含：
1. 话题标题
2. 简短摘要（2-3句话）
3. 为什么这是热点（热度证据）

请输出 JSON 列表，最多 {limit} 条：
[{{"title": "...", "summary": "...", "heat_reason": "..."}}]

只输出 JSON，不要其他文字。"""

        try:
            resp = await self._llm.generate_response(
                system_prompt="你是热点新闻分析师。你诚实：不确定的内容就标注出来。只输出 JSON。",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            content = resp.get("content", "[]")

            import json as _json
            from json_repair import repair_json
            start = content.find("[")
            end = content.rfind("]") + 1
            if start < 0 or end <= start:
                return []
            data = _json.loads(repair_json(content[start:end]))

            items: list[SourceItem] = []
            for d in data[:limit]:
                items.append(SourceItem(
                    source="LLM",
                    title=d.get("title", ""),
                    summary=d.get("summary", ""),
                    heat=0.6,
                    evidence_tier="inference",
                ))
            return items
        except Exception:
            return []
