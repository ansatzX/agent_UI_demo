import pytest

from backend.src.hotspots.collectors.jina_deepsearch import JinaDeepSearchCollector


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": "# 热点A\n摘要A\n\n# 热点B\n摘要B"
                    }
                }
            ]
        }


class FakeClient:
    def __init__(self):
        self.payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        self.url = url
        self.headers = headers
        self.payload = json
        return FakeResponse()


@pytest.mark.asyncio
async def test_jina_deepsearch_collector_calls_openai_compatible_endpoint():
    fake = FakeClient()
    collector = JinaDeepSearchCollector(
        api_key="key",
        base_url="https://aihubmix.com/v1",
        http_client_factory=lambda **kwargs: fake,
    )

    items = await collector.collect("科技 热点", limit=2, days=1)

    assert fake.url == "https://aihubmix.com/v1/chat/completions"
    assert fake.headers["Authorization"] == "Bearer key"
    assert fake.payload["model"] == "jina-deepsearch-v1"
    assert "科技 热点" in fake.payload["messages"][0]["content"]
    assert len(items) == 2
    assert items[0].source == "jina-deepsearch"
    assert "热点A" in items[0].title

class TimeoutClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        import httpx
        raise httpx.ReadTimeout("slow deepsearch")


@pytest.mark.asyncio
async def test_jina_deepsearch_collector_returns_empty_on_timeout():
    collector = JinaDeepSearchCollector(
        api_key="key",
        base_url="https://aihubmix.com/v1",
        http_client_factory=lambda **kwargs: TimeoutClient(),
    )

    items = await collector.collect("科技 热点", limit=2, days=1)

    assert items == []
