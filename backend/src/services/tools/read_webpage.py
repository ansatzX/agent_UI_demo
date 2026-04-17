# backend/src/services/tools/read_webpage.py
from bs4 import BeautifulSoup
import httpx

from .base import Tool
from .base import ToolResult


class ReadWebpageTool(Tool):
    """网页爬取工具"""

    name = "read_webpage"
    description = "爬取网页内容并提取文本"
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "网页 URL"},
            "selector": {
                "type": "string",
                "description": "可选的 CSS 选择器，用于提取特定内容（如 'article', '.content'）",
            },
        },
        "required": ["url"],
    }

    async def execute(self, url: str, selector: str = None) -> ToolResult:
        """爬取网页"""
        try:
            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 移除脚本、样式等
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            # 提取文本
            if selector:
                elements = soup.select(selector)
                text = "\n".join(el.get_text(strip=True) for el in elements)
            else:
                text = soup.get_text(strip=True, separator="\n")

            # 清理多余空行
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            clean_text = "\n".join(lines)

            # 提取标题
            title = soup.title.string if soup.title else "无标题"

            return ToolResult(
                success=True,
                output={
                    "url": url,
                    "title": title,
                    "content": clean_text[:5000],  # 限制长度
                    "word_count": len(clean_text),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, output={}, error=f"爬取网页失败: {str(e)}"
            )
