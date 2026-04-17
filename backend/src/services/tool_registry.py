# backend/src/services/tool_registry.py
from typing import Dict, List

from .tools.base import Tool
from .tools.base import ToolResult


class ToolNotFoundError(Exception):
    """工具未找到异常"""

    pass


class ToolRegistry:
    """工具注册和管理"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool

    def get_tool_definitions(self) -> List[Dict]:
        """返回所有工具的定义（供 LLM 使用）"""
        return [tool.to_definition() for tool in self.tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行工具（支持工具链）"""
        tool = self.tools.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")

        # 执行工具
        result = await tool.execute(**kwargs)

        # 检查是否有后置工具（工具链）
        if (
            tool.follow_up_tool
            and result.success
            and not result.requires_user_input
        ):
            # 自动调用后置工具
            if result.follow_up_input:
                follow_up_result = await self.execute(
                    tool.follow_up_tool, **result.follow_up_input
                )
                return follow_up_result

        return result
