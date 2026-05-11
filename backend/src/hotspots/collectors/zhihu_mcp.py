from __future__ import annotations

import json
import re
from typing import Any, List

from ..models import SourceItem


class ZhihuMCPCollector:
    def __init__(self, bridge: Any, server_name: str = "zhihu"):
        self.bridge = bridge
        self.server_name = server_name

    async def collect(self, keywords: str, limit: int = 10, days: int = 1) -> List[SourceItem]:
        if not self.bridge:
            return []
        if hasattr(self.bridge, "ensure_connected"):
            connected = await self.bridge.ensure_connected(self.server_name)
            if not connected:
                return []
        tools = await self.bridge.list_tools(self.server_name)
        names = {tool.get("name", "") for tool in tools}
        items: list[SourceItem] = []

        if "zhihu_hot_stories" in names:
            result = await self.bridge.call_tool(self.server_name, "zhihu_hot_stories", {"limit": limit})
            if getattr(result, "success", False):
                items.extend(_parse_zhihu_text(_extract_text(getattr(result, "output", {})), limit=limit))

        if "zhihu_search" in names and keywords.strip():
            result = await self.bridge.call_tool(
                self.server_name,
                "zhihu_search",
                {"keyword": keywords.strip(), "type": "general", "limit": limit},
            )
            if getattr(result, "success", False):
                items.extend(_parse_zhihu_text(_extract_text(getattr(result, "output", {})), limit=limit))

        if not items:
            tool_name = _choose_search_tool(tools)
            if not tool_name:
                return []
            result = await self.bridge.call_tool(self.server_name, tool_name, {"keyword": keywords, "limit": limit})
            if getattr(result, "success", False):
                items.extend(_parse_zhihu_text(_extract_text(getattr(result, "output", {})), limit=limit))

        items = await self._enrich_items(items, names)
        seen = set()
        unique = []
        for item in items:
            key = item.url or item.title
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique[:limit]

    async def _enrich_items(self, items: List[SourceItem], tool_names: set[str]) -> List[SourceItem]:
        enriched = []
        for item in items:
            detail_tool, arguments = _detail_tool_for(item, tool_names)
            if not detail_tool:
                enriched.append(item)
                continue
            result = await self.bridge.call_tool(self.server_name, detail_tool, arguments)
            if not getattr(result, "success", False):
                enriched.append(item)
                continue
            detailed = _merge_detail(item, _extract_text(getattr(result, "output", {})), detail_tool)
            enriched.append(detailed)
        return enriched

def _choose_search_tool(tools: list[dict]) -> str | None:
    if not tools:
        return None
    preferred = ["hot", "trending", "search", "question"]
    for keyword in preferred:
        for tool in tools:
            name = tool.get("name", "")
            desc = tool.get("description", "")
            if keyword.lower() in f"{name} {desc}".lower():
                return name
    return tools[0].get("name")


def _extract_text(output: Any) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        chunks = output.get("content")
        if isinstance(chunks, list):
            return "\n".join(str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in chunks)
        for key in ("text", "result", "message", "data"):
            if key in output:
                return _extract_text(output[key])
        return json.dumps(output, ensure_ascii=False)
    if isinstance(output, list):
        return "\n".join(_extract_text(x) for x in output)
    return str(output or "")


def _detail_tool_for(item: SourceItem, tool_names: set[str]) -> tuple[str, dict] | tuple[None, None]:
    raw_type = str(item.raw.get("type") or item.raw.get("object", {}).get("type") or "").lower()
    url = item.url or str(item.raw.get("link") or item.raw.get("object", {}).get("url") or "")

    answer_id = _extract_answer_id(url)
    article_id = _extract_article_id(url)
    question_id = _extract_question_id(url)

    if answer_id and "zhihu_get_answer" in tool_names:
        return "zhihu_get_answer", {"answer_id": answer_id, "comment_limit": 0}
    if raw_type == "article" and article_id and "zhihu_get_article" in tool_names:
        return "zhihu_get_article", {"article_id": article_id, "comment_limit": 0}
    if raw_type == "question" and question_id and "zhihu_get_question" in tool_names:
        return "zhihu_get_question", {"question_id": question_id, "answer_limit": 3}
    if article_id and "zhihu_get_article" in tool_names:
        return "zhihu_get_article", {"article_id": article_id, "comment_limit": 0}
    if question_id and "zhihu_get_question" in tool_names:
        return "zhihu_get_question", {"question_id": question_id, "answer_limit": 3}
    return None, None


def _merge_detail(item: SourceItem, text: str, detail_tool: str) -> SourceItem:
    detail = _load_ok_data(text)
    if not isinstance(detail, dict):
        return item

    title = str(detail.get("title") or item.title).strip() or item.title
    url = str(detail.get("url") or item.url or "")
    summary = _summary_from_detail(detail, fallback=item.summary)
    raw = {**item.raw, "detail_tool": detail_tool, "detail": detail}
    return SourceItem(
        source=item.source,
        title=title,
        url=url,
        summary=summary,
        heat=item.heat,
        published_at=item.published_at,
        evidence_tier=item.evidence_tier,
        raw=raw,
    )


def _load_ok_data(text: str) -> Any:
    try:
        payload = json.loads((text or "").strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("ok") is False:
        return None
    return payload.get("data")


def _summary_from_detail(detail: dict, fallback: str) -> str:
    parts = []
    for key in ("detail", "content", "excerpt", "summary"):
        value = detail.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
            break
    answers = detail.get("answers")
    if isinstance(answers, list) and answers:
        answer_lines = []
        for answer in answers[:3]:
            if not isinstance(answer, dict):
                continue
            excerpt = str(answer.get("excerpt") or "").strip()
            author = str(answer.get("author") or "匿名").strip()
            if excerpt:
                answer_lines.append(f"{author}: {excerpt}")
        if answer_lines:
            parts.append("相关回答摘要：\n" + "\n".join(answer_lines))
    return "\n\n".join(parts).strip() or fallback


def _extract_answer_id(url: str) -> str | None:
    match = re.search(r"/answer/(\d+)", url or "")
    return match.group(1) if match else None


def _extract_question_id(url: str) -> str | None:
    match = re.search(r"/question/(\d+)", url or "")
    return match.group(1) if match else None


def _extract_article_id(url: str) -> str | None:
    match = re.search(r"(?:zhuanlan\.zhihu\.com/)?p/(\d+)", url or "")
    return match.group(1) if match else None


def _parse_zhihu_text(text: str, limit: int) -> List[SourceItem]:
    text = (text or "").strip()
    if not text:
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        if data.get("ok") is False or isinstance(data.get("error"), dict):
            return []
        rows = data.get("data") or data.get("items") or data.get("result")
        if isinstance(rows, list):
            items: list[SourceItem] = []
            for row in rows[:limit]:
                if not isinstance(row, dict):
                    continue
                obj = row.get("object") if isinstance(row.get("object"), dict) else {}
                highlight = row.get("highlight") if isinstance(row.get("highlight"), dict) else {}
                title = str(
                    row.get("title")
                    or row.get("question_title")
                    or row.get("name")
                    or obj.get("title")
                    or highlight.get("title")
                    or ""
                ).strip()
                if not title:
                    continue
                summary = str(
                    row.get("excerpt")
                    or row.get("summary")
                    or row.get("description")
                    or row.get("content")
                    or obj.get("excerpt")
                    or highlight.get("description")
                    or title
                )
                url = str(row.get("url") or row.get("link") or obj.get("url") or "")
                heat = _coerce_heat(row.get("heat") or row.get("hot") or row.get("score") or 0.8)
                items.append(SourceItem(source="zhihu", title=title, url=url, summary=summary, heat=heat, evidence_tier="news_report", raw=row))
            return items

    lines = [line.strip(" -\t") for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    title = lines[0]
    summary = "\n".join(lines[1:]) or title
    return [SourceItem(source="zhihu", title=title, summary=summary, heat=0.8, evidence_tier="news_report", raw={"text": text})]


def _coerce_heat(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.8
    if number > 1:
        return min(1.0, number / 100.0)
    return max(0.0, min(1.0, number))
