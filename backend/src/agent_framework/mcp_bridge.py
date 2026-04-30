"""MCP 协议桥 - 管理多个 MCP 服务器的连接与工具调用"""

import asyncio
from dataclasses import dataclass, field
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class MCPToolResult:
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None


class MCPServerConnection:
    """单个 MCP 服务器连接"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._request_id = 0

    async def connect(self, timeout: float = 30.0):
        self._drop_if_bound_to_different_loop()
        env = None
        if self.config.env:
            env = {**os.environ, **self.config.env}
        self.process = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            ),
            timeout=timeout,
        )
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        self._loop = asyncio.get_running_loop()
        logger.info(f"MCP 服务器 '{self.config.name}' 已连接")

    def is_connected_in_current_loop(self) -> bool:
        return (
            self.process is not None
            and self.process.returncode is None
            and self.reader is not None
            and self.writer is not None
            and self._loop is asyncio.get_running_loop()
        )

    def _drop_if_bound_to_different_loop(self) -> None:
        if self.process is None or self._loop is asyncio.get_running_loop():
            return
        logger.warning("MCP 服务器 '%s' 连接属于旧事件循环，将重新连接", self.config.name)
        try:
            if self.writer:
                self.writer.close()
        except Exception:
            pass
        try:
            if self.process.returncode is None:
                self.process.terminate()
        except Exception:
            pass
        self.process = None
        self.reader = None
        self.writer = None
        self._loop = None

    async def close(self):
        if self.process:
            self.process.terminate()
            if self._loop is asyncio.get_running_loop():
                await self.process.wait()
            self.process = None
            self.reader = None
            self.writer = None
            self._loop = None
            logger.info(f"MCP 服务器 '{self.config.name}' 已断开")

    async def request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        self._drop_if_bound_to_different_loop()
        if not self.writer or not self.reader:
            raise RuntimeError("MCP client not connected")
        self._request_id += 1
        request = {"jsonrpc": "2.0", "id": self._request_id, "method": method}
        if params is not None:
            request["params"] = params
        self.writer.write((json.dumps(request) + "\n").encode())
        await self.writer.drain()
        response_line = await asyncio.wait_for(self.reader.readline(), timeout=30.0)
        if not response_line:
            raise RuntimeError("MCP server closed stdout")
        response = json.loads(response_line.decode())
        if "error" in response:
            raise RuntimeError(response["error"].get("message", str(response["error"])))
        return response.get("result", {})

    async def notify(self, method: str, params: Optional[Dict] = None) -> None:
        self._drop_if_bound_to_different_loop()
        if not self.writer:
            raise RuntimeError("MCP client not connected")
        notification = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            notification["params"] = params
        self.writer.write((json.dumps(notification) + "\n").encode())
        await self.writer.drain()

    async def initialize(self) -> Dict[str, Any]:
        result = await self.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "agent-ui-demo", "version": "0.1.0"},
        })
        await self.notify("notifications/initialized")
        return result

    async def list_tools(self) -> List[Dict[str, Any]]:
        result = await self.request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: Dict) -> MCPToolResult:
        try:
            result = await self.request("tools/call", {"name": tool_name, "arguments": arguments})
            return MCPToolResult(success=result.get("success", True), output=result)
        except Exception as e:
            logger.error(f"MCP 工具调用失败: {e}", exc_info=True)
            return MCPToolResult(success=False, output={}, error=str(e))


class MCPBridge:
    """多 MCP 服务器管理器"""

    def __init__(self):
        self.servers: Dict[str, MCPServerConnection] = {}

    async def register(self, config: MCPServerConfig):
        if config.name in self.servers:
            logger.warning(f"MCP 服务器 '{config.name}' 已存在，将被覆盖")
        self.servers[config.name] = MCPServerConnection(config)
        logger.info(f"MCP 服务器已注册: {config.name} -> {config.description}")

    async def connect_all(self):
        async def _connect_and_initialize(conn):
            await conn.connect(timeout=15.0)
            try:
                await conn.initialize()
            except Exception as e:
                logger.warning(f"MCP 服务器 '{conn.config.name}' initialize 失败: {e}")

        results = await asyncio.gather(
            *[_connect_and_initialize(conn) for conn in self.servers.values()],
            return_exceptions=True,
        )
        for (name, _), result in zip(self.servers.items(), results):
            if isinstance(result, Exception):
                logger.error(f"MCP 服务器 '{name}' 连接失败: {result}")


    async def connect_server(self, server_name: str) -> bool:
        conn = self.servers.get(server_name)
        if not conn:
            return False
        if conn.is_connected_in_current_loop():
            return True
        try:
            await conn.connect(timeout=15.0)
            try:
                await conn.initialize()
            except Exception as e:
                logger.warning(f"MCP 服务器 '{server_name}' initialize 失败: {e}")
            return True
        except Exception as e:
            logger.error(f"MCP 服务器 '{server_name}' 连接失败: {e}", exc_info=True)
            return False

    async def disconnect_all(self):
        tasks = []
        for conn in self.servers.values():
            tasks.append(conn.close())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> MCPToolResult:
        conn = self.servers.get(server_name)
        if not conn:
            return MCPToolResult(
                success=False,
                output={},
                error=f"MCP 服务器 '{server_name}' 未注册",
            )
        return await conn.call_tool(tool_name, arguments)

    async def ensure_connected(self, server_name: str) -> bool:
        conn = self.servers.get(server_name)
        if not conn:
            return False
        if conn.is_connected_in_current_loop():
            return True
        return await self.connect_server(server_name)

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        conn = self.servers.get(server_name)
        if not conn:
            return []
        if not conn.is_connected_in_current_loop():
            logger.info(f"MCP 服务器 '{server_name}' 未连接，跳过工具列表获取")
            return []
        try:
            return await conn.list_tools()
        except Exception as e:
            logger.error(f"MCP 工具列表获取失败: {server_name} - {e}", exc_info=True)
            return []

    def list_servers(self) -> List[Dict[str, str]]:
        return [
            {
                "name": conn.config.name,
                "description": conn.config.description,
                "connected": conn.process is not None and conn.process.returncode is None,
                "status": "已连接" if conn.process is not None and conn.process.returncode is None else "已配置，未连接",
            }
            for conn in self.servers.values()
        ]

    def get_server(self, name: str) -> Optional[MCPServerConnection]:
        return self.servers.get(name)
