from backend.src.gradio_app.app import GradioChatHandler


def test_handler_has_no_background_mcp_connect_method():
    assert not hasattr(GradioChatHandler, "start_background_mcp_connect")
    GradioChatHandler(auto_load_mcp=True)
