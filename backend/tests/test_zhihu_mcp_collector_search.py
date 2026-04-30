import pytest

from backend.src.hotspots.collectors.zhihu_mcp import ZhihuMCPCollector


class Result:
    success = True
    error = None

    def __init__(self, output):
        self.output = output


class FakeBridge:
    def __init__(self):
        self.connected = False
        self.called = []

    async def ensure_connected(self, server_name):
        self.connected = True
        return True

    async def list_tools(self, server_name):
        return [
            {"name": "zhihu_hot_stories", "description": "获取知乎热榜当前热门内容。"},
            {"name": "zhihu_search", "description": "搜索知乎内容（问题、回答、文章等）。"},
        ]

    async def call_tool(self, server_name, tool_name, arguments):
        self.called.append((tool_name, arguments))
        if tool_name == "zhihu_hot_stories":
            return Result({"content": [{"type": "text", "text": '{"ok": true, "data": [{"title": "热榜A", "excerpt": "摘要A"}]}' }]})
        return Result({"content": [{"type": "text", "text": '{"ok": true, "data": [{"title": "搜索B", "excerpt": "摘要B"}]}' }]})


@pytest.mark.asyncio
async def test_zhihu_collector_calls_hot_and_search_tools():
    bridge = FakeBridge()
    collector = ZhihuMCPCollector(bridge=bridge, server_name="zhihu")

    items = await collector.collect("科技产业", limit=5, days=1)

    assert bridge.connected is True
    assert ("zhihu_hot_stories", {"limit": 5}) in bridge.called
    assert any(name == "zhihu_search" and args["keyword"] == "科技产业" for name, args in bridge.called)
    assert [item.title for item in items] == ["热榜A", "搜索B"]


class DetailBridge:
    def __init__(self):
        self.called = []

    async def ensure_connected(self, server_name):
        return True

    async def list_tools(self, server_name):
        return [
            {"name": "zhihu_search"},
            {"name": "zhihu_get_answer"},
            {"name": "zhihu_get_question"},
            {"name": "zhihu_get_article"},
        ]

    async def call_tool(self, server_name, tool_name, arguments):
        self.called.append((tool_name, arguments))
        if tool_name == "zhihu_search":
            return Result({"content": [{"type": "text", "text": """{"ok": true, "data": [
                {"type": "answer", "title": "回答A", "link": "/question/1/answer/123", "excerpt": "短摘要"},
                {"type": "article", "title": "文章B", "link": "//zhuanlan.zhihu.com/p/456", "excerpt": "短摘要"},
                {"type": "question", "title": "问题C", "link": "/question/789", "excerpt": "短摘要"}
            ]}""" }]})
        if tool_name == "zhihu_get_answer":
            return Result({"content": [{"type": "text", "text": '{"ok": true, "data": {"title": "回答A详情", "content": "回答全文内容", "url": "https://www.zhihu.com/question/1/answer/123"}}'}]})
        if tool_name == "zhihu_get_article":
            return Result({"content": [{"type": "text", "text": '{"ok": true, "data": {"title": "文章B详情", "content": "文章全文内容", "url": "https://zhuanlan.zhihu.com/p/456"}}'}]})
        if tool_name == "zhihu_get_question":
            return Result({"content": [{"type": "text", "text": '{"ok": true, "data": {"title": "问题C详情", "detail": "问题详情", "answers": [{"author": "作者", "excerpt": "回答摘要"}]}}'}]})
        raise AssertionError(tool_name)


@pytest.mark.asyncio
async def test_zhihu_collector_enriches_search_results_with_detail_tools():
    bridge = DetailBridge()
    collector = ZhihuMCPCollector(bridge=bridge, server_name="zhihu")

    items = await collector.collect("科技产业", limit=5, days=1)

    assert ("zhihu_get_answer", {"answer_id": "123", "comment_limit": 0}) in bridge.called
    assert ("zhihu_get_article", {"article_id": "456", "comment_limit": 0}) in bridge.called
    assert ("zhihu_get_question", {"question_id": "789", "answer_limit": 3}) in bridge.called
    assert [item.title for item in items] == ["回答A详情", "文章B详情", "问题C详情"]
    assert "回答全文内容" in items[0].summary
    assert "文章全文内容" in items[1].summary
    assert "问题详情" in items[2].summary
    assert "回答摘要" in items[2].summary
