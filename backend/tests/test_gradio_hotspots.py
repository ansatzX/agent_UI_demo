import pytest

from backend.src.gradio_app.app import GradioChatHandler


@pytest.mark.asyncio
async def test_gradio_handler_scans_hotspots_with_injected_workflow():
    handler = GradioChatHandler(auto_load_mcp=False)

    class FakeWorkflow:
        async def scan(self, keywords, limit, days):
            assert keywords == "AI"
            assert limit == 3
            assert days == 1
            return []

    handler.hotspot_workflow = FakeWorkflow()

    result = await handler.scan_hotspots("AI", 3, 1, ["Jina DeepSearch"])

    assert "暂无候选选题" in result
