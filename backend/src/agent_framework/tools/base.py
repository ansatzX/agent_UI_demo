from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """工具执行结果"""

    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None
    follow_up_input: Optional[Dict[str, Any]] = None
    requires_user_input: bool = False


class Tool:
    """工具基类"""

    name: str
    description: str
    parameters: Dict  # JSON Schema
    follow_up_tool: Optional[str] = None

    async def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    def to_definition(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
