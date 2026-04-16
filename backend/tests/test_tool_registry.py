# backend/tests/test_tool_registry.py
import pytest
from backend.src.services.tools.base import Tool, ToolResult
from backend.src.services.tool_registry import ToolRegistry

class MockTool(Tool):
    name = "mock_tool"
    description = "A mock tool for testing"
    parameters = {
        "type": "object",
        "properties": {
            "input": {"type": "string"}
        },
        "required": ["input"]
    }

    async def execute(self, input: str) -> ToolResult:
        return ToolResult(
            success=True,
            output={"result": f"processed: {input}"}
        )

@pytest.mark.asyncio
async def test_tool_registry_register():
    """测试工具注册"""
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)

    assert "mock_tool" in registry.tools
    assert registry.tools["mock_tool"] == tool

@pytest.mark.asyncio
async def test_tool_registry_execute():
    """测试工具执行"""
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)

    result = await registry.execute("mock_tool", input="test")

    assert result.success
    assert result.output["result"] == "processed: test"
