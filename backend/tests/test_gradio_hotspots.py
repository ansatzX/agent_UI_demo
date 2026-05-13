"""Tests for GradioChatHandler hotspot scanning."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.gradio_app.gradio_chat import GradioChatHandler
from src.hotspots.models import SourceItem, TopicCard, TopicScore


def _make_handler():
    state = MagicMock()
    state.llm_service = MagicMock()
    state.tool_registry = MagicMock()
    state.mcp_bridge = MagicMock()
    state.research_holder = MagicMock()
    return GradioChatHandler(state)


@pytest.mark.asyncio
async def test_scan_hotspots_returns_markdown_and_history():
    handler = _make_handler()

    fake_card = TopicCard(
        title="测试选题",
        summary="摘要",
        score=TopicScore(heat=0.5, relevance=0.6, controversy=0.3, explainability=0.4),
        sources=[],
        creator_fit="匹配理由",
        angles=["角度1"],
        title_suggestions=["标题1"],
        mindmap_mermaid="mindmap\n  root((测试))",
        risk_notes=["风险1"],
    )

    fake_workflow = MagicMock()
    fake_workflow.scan = AsyncMock(return_value=[fake_card])
    fake_workflow.collectors = [MagicMock()]

    fake_history = MagicMock()
    fake_history.list_runs = MagicMock(return_value=[])

    handler._state.hotspot_runtime = {
        "llm_collector": MagicMock(),
        "workflow": fake_workflow,
        "history_store": fake_history,
    }

    markdown, history_md = await handler.scan_hotspots("AI", 3, 1)

    assert "测试选题" in markdown
    assert "```mermaid" in markdown
    fake_workflow.scan.assert_awaited_once_with(keywords="AI", limit=3, days=1)
    fake_history.append_run.assert_called_once()
