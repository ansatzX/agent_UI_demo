# backend/src/services/tools/write_article.py
from .base import Tool
from .base import ToolResult


class WriteArticleTool(Tool):
    """智能写作工具"""

    name = "write_article"
    description = "根据主题和素材生成文章结构和风格指南"
    parameters = {
        "type": "object",
        "properties": {
            "article_type": {
                "type": "string",
                "enum": [
                    "project_report",
                    "news_release",
                    "wechat_article",
                    "general",
                ],
                "description": "文章类型：project_report(项目总结报告), news_release(新闻稿), wechat_article(公众号推文), general(通用文章)",
            },
            "topic": {"type": "string", "description": "文章主题或标题"},
            "style": {
                "type": "string",
                "enum": ["formal", "casual", "academic", "lively"],
                "description": "写作风格：formal(正式), casual(轻松), academic(学术), lively(活泼)",
            },
            "source_material": {
                "type": "string",
                "description": "素材内容（从网页、文档或用户提供的信息）",
            },
            "output_format": {
                "type": "string",
                "enum": ["text", "markdown", "slide_outline"],
                "description": "输出格式：markdown(推荐), text(纯文本), slide_outline(幻灯片大纲)",
            },
        },
        "required": ["article_type", "topic"],
    }

    async def execute(
        self,
        article_type: str,
        topic: str,
        style: str = "formal",
        source_material: str = "",
        output_format: str = "markdown",
    ) -> ToolResult:
        """生成文章结构和风格指南（实际内容由 LLM 在 Agent 循环中生成）"""

        structure = self._get_article_structure(article_type)
        style_guide = self._get_style_guide(style)

        return ToolResult(
            success=True,
            output={
                "article_type": article_type,
                "topic": topic,
                "style": style,
                "style_guide": style_guide,
                "structure": structure,
                "source_material": source_material,
                "output_format": output_format,
                "ready": True,
            },
        )

    def _get_article_structure(self, article_type: str) -> dict:
        """返回文章结构模板"""
        structures = {
            "project_report": {
                "sections": [
                    "项目背景",
                    "目标与范围",
                    "实施过程",
                    "主要成果",
                    "经验总结",
                    "后续计划",
                ]
            },
            "news_release": {
                "sections": [
                    "导语（5W1H）",
                    "主体内容",
                    "背景介绍",
                    "相关引用",
                    "结语",
                ]
            },
            "wechat_article": {
                "sections": [
                    "吸引人的标题",
                    "引入段落（引发共鸣）",
                    "核心内容（分点阐述）",
                    "案例/故事",
                    "总结与行动号召",
                ]
            },
            "general": {"sections": ["标题", "引言", "主体内容", "结论"]},
        }
        return structures.get(article_type, structures["general"])

    def _get_style_guide(self, style: str) -> str:
        """返回风格指南"""
        guides = {
            "formal": "正式严谨，使用专业术语，客观陈述，适合官方报告和商务文档",
            "casual": "轻松友好，口语化表达，贴近生活，适合内部沟通和博客文章",
            "academic": "学术规范，引用数据，逻辑严密，适合论文和研究报告",
            "lively": "活泼生动，比喻形象，富有感染力，适合公众号和社交媒体",
        }
        return guides.get(style, guides["formal"])
