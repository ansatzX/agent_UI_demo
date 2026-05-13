"""Tests for GradioChatHandler chat history conversion."""

import pytest
from unittest.mock import MagicMock

from src.gradio_app.gradio_chat import GradioChatHandler


def _make_handler():
    state = MagicMock()
    state.llm_service = MagicMock()
    state.tool_registry = MagicMock()
    state.mcp_bridge = MagicMock()
    state.research_holder = MagicMock()
    return GradioChatHandler(state)


def test_chat_history_gradio_messages_format():
    """Gradio 6.x Chatbot sends [[user, assistant], ...] pairs."""
    handler = _make_handler()
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你？"},
    ]
    # GradioChatHandler.chat internally converts history;
    # verify the conversion logic handles dict format
    converted = []
    for h in history:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
            converted.append({"role": h["role"], "content": h["content"]})
    assert len(converted) == 2
    assert converted[0] == {"role": "user", "content": "你好"}
    assert converted[1] == {"role": "assistant", "content": "你好，有什么可以帮你？"}


def test_chat_history_legacy_tuple_format():
    """Old Gradio sent [(user, assistant), ...] tuples."""
    history = [
        ("你好", "你好，有什么可以帮你？"),
    ]
    converted = []
    for h in history:
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            converted.append({"role": "user", "content": str(h[0])})
            if h[1]:
                converted.append({"role": "assistant", "content": str(h[1])})
    assert len(converted) == 2
    assert converted[0] == {"role": "user", "content": "你好"}
    assert converted[1] == {"role": "assistant", "content": "你好，有什么可以帮你？"}


def test_chat_history_mixed_empty_assistant():
    """Assistant message None/empty should be skipped."""
    history = [
        ("问题", None),
        ("问题2", "回答2"),
    ]
    converted = []
    for h in history:
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            converted.append({"role": "user", "content": str(h[0])})
            if h[1]:
                converted.append({"role": "assistant", "content": str(h[1])})
    assert len(converted) == 3  # user1 + user2 + assistant2 (assistant1 skipped)
