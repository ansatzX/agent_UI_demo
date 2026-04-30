from __future__ import annotations

import json
import logging
from typing import Any, Dict

from json_repair import repair_json

from .models import CreatorProfile, SourceItem

logger = logging.getLogger(__name__)


class LLMTopicAnalyzer:
    """Generate creator-specific topic analysis with the configured chat LLM."""

    def __init__(self, llm_service):
        self.llm = llm_service

    async def analyze(self, item: SourceItem, profile: CreatorProfile) -> Dict[str, Any]:
        system_prompt = "你是热点视频选题策划助手，擅长从热点新闻中提炼可讲述、可争议、可验证的分析角度。只输出JSON。"
        user_prompt = f"""请基于以下热点，为目标创作者生成定制化视频选题分析。

选题目标：{profile.goal}
关注领域：{', '.join(profile.focus_domains)}
分析视角：{', '.join(profile.analysis_lens)}
避免方向：{', '.join(profile.avoid)}

热点标题：{item.title}
热点摘要：{item.summary}
来源：{item.source} {item.url}

请输出 JSON：
{{
  "summary": "100-200字事件摘要，包含关键事实和为什么值得关注",
  "creator_fit": "为什么适合目标账号，必须结合关注领域和分析视角",
  "angles": ["3-5个具体分析角度"],
  "title_suggestions": ["3-5个视频标题"],
  "mindmap_mermaid": "Mermaid mindmap 文本，不要代码围栏",
  "risk_notes": ["事实核验和表达风险"]
}}
"""
        response = await self.llm.generate_response(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=1800,
        )
        content = response.get("content", "")
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(repair_json(content[start:end]))
        except Exception as e:
            logger.warning("LLM topic analysis JSON parse failed: %s", e)
        return {}
