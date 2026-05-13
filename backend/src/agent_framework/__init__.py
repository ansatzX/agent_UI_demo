"""agent_framework - 通用 AI Agent 框架

提供可复用的 ReAct Agent、工具注册、LLM 集成、会话管理和 MCP 桥接。
"""

from .agent import ReActAgent, AgentResult
from .llm import BaseLLMService
from .llm import LLMService  # backward compat alias
from .mcp_bridge import MCPBridge, MCPServerConfig, MCPToolResult
from .session import SessionService
from .tool_registry import ToolRegistry, ToolNotFoundError
from ..services.tools.base import Tool, ToolResult

__all__ = [
    "ReActAgent",
    "AgentResult",
    "BaseLLMService",
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
