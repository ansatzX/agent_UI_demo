import pytest
from unittest.mock import AsyncMock

from src.hotspots.models import SourceItem
from src.hotspots.profile import default_creator_profile
from src.hotspots.workflow import HotspotWorkflow


class FakeAnalyzer:
    def __init__(self):
        self.called = False

    async def analyze(self, item, profile):
        self.called = True
        return {
            "summary": "LLM摘要",
            "creator_fit": "LLM账号匹配理由",
            "angles": ["LLM角度1", "LLM角度2"],
            "title_suggestions": ["LLM标题1"],
            "mindmap_mermaid": "mindmap\n  root((LLM))",
            "risk_notes": ["LLM风险"],
        }


@pytest.mark.asyncio
async def test_workflow_uses_llm_analyzer_for_topic_cards():
    analyzer = FakeAnalyzer()
    fake_llm = AsyncMock()
    fake_llm.generate_response = AsyncMock(return_value={"content": "[]"})
    workflow = HotspotWorkflow(
        profile=default_creator_profile(), collectors=[],
        analyzer=analyzer, llm_service=fake_llm,
    )

    cards = await workflow.build_topic_cards([
        SourceItem(source="zhihu", title="科技产业争议", summary="摘要", heat=0.8)
    ])

    assert analyzer.called is True
    assert cards[0].summary == "LLM摘要"
    assert cards[0].creator_fit == "LLM账号匹配理由"
    assert cards[0].angles == ["LLM角度1", "LLM角度2"]
