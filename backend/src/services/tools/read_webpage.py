# backend/src/services/tools/read_webpage.py
"""Webpage reader with URL classification and two-phase retrieval.

Phase 1: classify URL → return source type + snippet
Phase 2 (on demand): fetch full content for relevant URLs only.
"""

from bs4 import BeautifulSoup
import httpx

from .base import Tool, ToolResult
from .url_classifier import URLClassifier


class ReadWebpageTool(Tool):
    """网页爬取工具，含源分类"""

    name = "read_webpage"
    description = (
        "Fetch and extract text from a webpage. "
        "Automatically classifies the source type (academic/news/official/wiki). "
        "Use preview=True to get a snippet first, then fetch full content."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "网页 URL"},
            "selector": {
                "type": "string",
                "description": "可选的 CSS 选择器",
            },
            "preview": {
                "type": "boolean",
                "description": "仅返回摘要（前 800 字符）+ 源分类，用于相关性初筛。默认 false",
                "default": False,
            },
        },
        "required": ["url"],
    }

    async def execute(
        self, url: str, selector: str = None, preview: bool = False
    ) -> ToolResult:
        url_info = URLClassifier.classify(url)

        try:
            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (compatible; ResearchBot/1.0)"
                        ),
                    },
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            if selector:
                elements = soup.select(selector)
                text = "\n".join(el.get_text(strip=True) for el in elements)
            else:
                text = soup.get_text(strip=True, separator="\n")

            lines = [line.strip() for line in text.split("\n") if line.strip()]
            clean_text = "\n".join(lines)
            title = soup.title.string.strip() if soup.title else "无标题"

            output = {
                "url": url,
                "title": title,
                "source_type": url_info.source_name,
                "evidence_tier": url_info.evidence_tier,
            }

            if preview:
                # Phase 1: snippet only — for relevance filtering
                snippet = clean_text[:800]
                if len(clean_text) > 800:
                    snippet += f"... (全文 {len(clean_text)} 字符)"
                output["snippet"] = snippet
                output["full_length"] = len(clean_text)
                output["_preview"] = True
            else:
                # Phase 2: full content
                output["content"] = clean_text[:8000]
                output["word_count"] = len(clean_text)

            return ToolResult(success=True, output=output)

        except Exception as e:
            return ToolResult(
                success=False,
                output={"url": url, "source_type": url_info.source_name},
                error=f"爬取失败: {e}",
            )
