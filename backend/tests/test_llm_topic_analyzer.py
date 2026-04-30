import pytest

from backend.src.hotspots.models import SourceItem
from backend.src.hotspots.profile import default_creator_profile
from backend.src.hotspots.workflow import HotspotWorkflow


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
    workflow = HotspotWorkflow(profile=default_creator_profile(), collectors=[], analyzer=analyzer)

    cards = await workflow.build_topic_cards([
        SourceItem(source="zhihu", title="科技产业争议", summary="摘要", heat=0.8)
    ])

    assert analyzer.called is True
    assert cards[0].summary == "LLM摘要"
    assert cards[0].creator_fit == "LLM账号匹配理由"
    assert cards[0].angles == ["LLM角度1", "LLM角度2"]
