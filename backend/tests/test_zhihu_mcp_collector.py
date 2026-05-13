import pytest

from src.hotspots.collectors.zhihu_mcp import ZhihuMCPCollector


class Result:
    success = True
    error = None
    output = {
        "content": [
            {"type": "text", "text": "知乎热榜：AI公司争议\n普通人就业影响"}
        ]
    }


class FakeBridge:
    def __init__(self):
        self.called = []

    async def list_tools(self, server_name):
        assert server_name == "zhihu"
        return [{"name": "search", "description": "搜索知乎内容"}]

    async def call_tool(self, server_name, tool_name, arguments):
        self.called.append((server_name, tool_name, arguments))
        return Result()


@pytest.mark.asyncio
async def test_zhihu_collector_uses_search_tool_from_mcp_bridge():
    bridge = FakeBridge()
    collector = ZhihuMCPCollector(bridge=bridge, server_name="zhihu")

    items = await collector.collect("AI 公司", limit=3, days=1)

    assert bridge.called[0][0] == "zhihu"
    assert bridge.called[0][1] == "search"
    assert "AI 公司" in str(bridge.called[0][2])
    assert len(items) == 1
    assert items[0].source == "zhihu"
    assert "知乎热榜" in items[0].title
