# backend/src/services/tools/base.py
from typing import Dict, Any, Optional
from dataclasses import dataclass

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
        """执行工具"""
        raise NotImplementedError

    def to_definition(self) -> Dict:
        """转换为 LLM 工具定义"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
