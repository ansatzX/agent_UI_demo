from src.hotspots.collectors.zhihu_mcp import _parse_zhihu_text


def test_parse_zhihu_json_data_items():
    text = '{"ok": true, "data": [{"title": "标题A", "excerpt": "摘要A", "url": "https://z/a"}, {"title": "标题B", "excerpt": "摘要B"}]}'

    items = _parse_zhihu_text(text, limit=10)

    assert len(items) == 2
    assert items[0].title == "标题A"
    assert items[0].summary == "摘要A"
    assert items[0].url == "https://z/a"
