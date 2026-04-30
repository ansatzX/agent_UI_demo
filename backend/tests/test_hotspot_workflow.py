import pytest

from backend.src.hotspots.models import SourceItem
from backend.src.hotspots.profile import default_creator_profile
from backend.src.hotspots.workflow import HotspotWorkflow, render_topic_cards_markdown


@pytest.mark.asyncio
async def test_workflow_dedupes_scores_and_renders_topic_cards():
    profile = default_creator_profile()
    workflow = HotspotWorkflow(profile=profile, collectors=[])
    items = [
        SourceItem(
            source="zhihu",
            title="中美科技公司新一轮AI竞争引发热议",
            url="https://example.com/a",
            summary="科技公司、公共政策和普通人就业受到影响，舆论争议明显。",
            heat=0.9,
        ),
        SourceItem(
            source="jina",
            title="中美科技公司新一轮AI竞争引发热议",
            url="https://example.com/b",
            summary="重复消息",
            heat=0.5,
        ),
    ]

    cards = await workflow.build_topic_cards(items, top_k=5)
    markdown = render_topic_cards_markdown(cards)

    assert len(cards) == 1
    assert cards[0].score.total > 0
    assert "为什么适合热点选题" in cards[0].creator_fit
    assert "```mermaid" in markdown
    assert "中美科技公司" in markdown
    assert "https://example.com/a" in markdown
