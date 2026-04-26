"""agent_framework - 通用 AI Agent 框架

提供可复用的 ReAct Agent、工具注册、LLM 集成、会话管理和 MCP 桥接。
"""

from .agent import ReActAgent, AgentResult
from .llm import LLMService
from .mcp_bridge import MCPBridge, MCPServerConfig, MCPToolResult
from .session import SessionService
from .tool_registry import ToolRegistry, ToolNotFoundError
from .tools.base import Tool, ToolResult

__all__ = [
    "ReActAgent",
    "AgentResult",
    "LLMService",
    "ToolRegistry",
    "ToolNotFoundError",
    "Tool",
    "ToolResult",
    "SessionService",
    "MCPBridge",
    "MCPServerConfig",
    "MCPToolResult",
]
