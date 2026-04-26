from typing import Dict, List

from .tools.base import Tool, ToolResult


class ToolNotFoundError(Exception):
    pass


class ToolRegistry:
    """通用工具注册和管理"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def get_tool_definitions(self) -> List[Dict]:
        return [tool.to_definition() for tool in self.tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        tool = self.tools.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")

        result = await tool.execute(**kwargs)

        if tool.follow_up_tool and result.success and not result.requires_user_input:
            if result.follow_up_input:
                follow_up_result = await self.execute(
                    tool.follow_up_tool, **result.follow_up_input
                )
                return follow_up_result

        return result

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())
