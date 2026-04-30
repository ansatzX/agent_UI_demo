import pytest

from backend.src.gradio_app.app import GradioChatHandler, create_app
from backend.src.hotspots.models import SourceItem, TopicCard, TopicScore


class FakeWorkflow:
    def __init__(self, profile=None, collectors=None, analyzer=None):
        self.collectors = collectors or []

    async def scan(self, keywords, limit, days):
        return [TopicCard(
            title="选题A",
            summary="摘要",
            score=TopicScore(heat=0.8, relevance=0.8, controversy=0.5, explainability=0.8),
            sources=[SourceItem(source="fake", title="选题A", summary="摘要", heat=0.8)],
            creator_fit="适合该账号",
            angles=["角度1"],
            title_suggestions=["标题1"],
            mindmap_mermaid="mindmap\n  root((选题A))",
            risk_notes=["风险1"],
        )]


@pytest.mark.asyncio
async def test_scan_hotspots_progress_yields_status_and_records_history(tmp_path):
    handler = GradioChatHandler(auto_load_mcp=False)
    handler._hotspot_workflow_cls = FakeWorkflow
    handler.history_store.path = tmp_path / "history.jsonl"

    chunks = []
    async for chunk in handler.scan_hotspots_progress("科技", 3, 1, ["知乎 MCP"]):
        chunks.append(chunk)

    assert "开始巡检" in chunks[0][0]
    assert "巡检完成" in chunks[-1][0]
    assert "科技" in chunks[-1][1]
    assert handler.history_store.list_runs()[0]["keywords"] == "科技"


def test_create_app_has_no_specific_up_owner_name():
    app = create_app()
    config_text = str(app.config)
    assert "老猫" not in config_text
