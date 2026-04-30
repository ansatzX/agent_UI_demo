from backend.src.gradio_app.app import GradioChatHandler, create_app


def test_hotspot_tab_uses_markdown_not_dataframe_for_status_and_history():
    app = create_app()
    components = app.config.get("components", [])
    bad = [c for c in components if c.get("type") == "dataframe" and c.get("props", {}).get("label") in {"MCP 连接状态", "最近巡检记录"}]
    assert bad == []


def test_mcp_status_markdown_lists_configured_servers():
    handler = GradioChatHandler(auto_load_mcp=False)
    text = handler.format_mcp_status_markdown()
    assert "| 名称 | 描述 | 状态 |" in text


def test_handler_does_not_initialize_hotspot_runtime_until_scan():
    handler = GradioChatHandler(auto_load_mcp=False)

    assert handler._hotspot_runtime is None
