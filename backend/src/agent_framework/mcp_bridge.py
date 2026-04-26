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
        self._request_id = 0

    async def connect(self, timeout: float = 30.0):
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
        logger.info(f"MCP 服务器 '{self.config.name}' 已连接")

    async def close(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None
            logger.info(f"MCP 服务器 '{self.config.name}' 已断开")

    async def call_tool(self, tool_name: str, arguments: Dict) -> MCPToolResult:
        if not self.writer or not self.reader:
            return MCPToolResult(
                success=False, output={}, error="MCP client not connected"
            )
        try:
            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
            self.writer.write((json.dumps(request) + "\n").encode())
            await self.writer.drain()

            response_line = await self.reader.readline()
            response = json.loads(response_line.decode())

            if "error" in response:
                error_msg = response["error"].get("message", str(response["error"]))
                return MCPToolResult(success=False, output={}, error=error_msg)

            result = response.get("result", {})
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
        results = await asyncio.gather(
            *[conn.connect() for conn in self.servers.values()],
            return_exceptions=True,
        )
        for (name, _), result in zip(self.servers.items(), results):
            if isinstance(result, Exception):
                logger.error(f"MCP 服务器 '{name}' 连接失败: {result}")

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

    def list_servers(self) -> List[Dict[str, str]]:
        return [
            {
                "name": conn.config.name,
                "description": conn.config.description,
                "connected": conn.process is not None,
            }
            for conn in self.servers.values()
        ]

    def get_server(self, name: str) -> Optional[MCPServerConnection]:
        return self.servers.get(name)
