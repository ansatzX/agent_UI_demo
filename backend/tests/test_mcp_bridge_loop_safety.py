import asyncio

import pytest

from backend.src.agent_framework.mcp_bridge import MCPBridge, MCPServerConfig, MCPServerConnection


class FakeProcess:
    returncode = None

    def terminate(self):
        pass


def test_connection_bound_to_old_event_loop_is_not_reused():
    conn = MCPServerConnection(MCPServerConfig(name="zhihu", command="node", args=[]))

    async def bind_connection_to_loop():
        conn.process = FakeProcess()
        conn.reader = object()
        conn.writer = object()
        conn._loop = asyncio.get_running_loop()

    asyncio.run(bind_connection_to_loop())

    async def check_from_new_loop():
        assert conn.is_connected_in_current_loop() is False

    asyncio.run(check_from_new_loop())


def test_bridge_reconnects_when_existing_connection_belongs_to_old_loop(monkeypatch):
    bridge = MCPBridge()
    conn = MCPServerConnection(MCPServerConfig(name="zhihu", command="node", args=[]))
    bridge.servers["zhihu"] = conn

    async def bind_connection_to_loop():
        conn.process = FakeProcess()
        conn.reader = object()
        conn.writer = object()
        conn._loop = asyncio.get_running_loop()

    asyncio.run(bind_connection_to_loop())

    calls = []

    async def fake_connect(timeout=30.0):
        calls.append(timeout)
        conn.process = FakeProcess()
        conn.reader = object()
        conn.writer = object()
        conn._loop = asyncio.get_running_loop()

    async def fake_initialize():
        return {}

    monkeypatch.setattr(conn, "connect", fake_connect)
    monkeypatch.setattr(conn, "initialize", fake_initialize)

    assert asyncio.run(bridge.ensure_connected("zhihu")) is True
    assert calls == [15.0]
