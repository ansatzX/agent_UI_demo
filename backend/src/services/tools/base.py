"""Tool base classes — standalone, no agent_framework dependency."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    follow_up_input: Optional[Dict[str, Any]] = None
    requires_user_input: bool = False


class Tool:
    name: str = ""
    description: str = ""
    parameters: Dict = field(default_factory=dict)
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
