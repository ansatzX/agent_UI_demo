from backend.src.gradio_app.app import GradioChatHandler


def test_history_to_agent_supports_gradio_messages_format():
    handler = GradioChatHandler(auto_load_mcp=False)
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你？"},
    ]

    assert handler._history_to_agent(history) == history


def test_history_to_agent_supports_legacy_tuple_format():
    handler = GradioChatHandler(auto_load_mcp=False)
    history = [("你好", "你好，有什么可以帮你？")]

    assert handler._history_to_agent(history) == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你？"},
    ]
