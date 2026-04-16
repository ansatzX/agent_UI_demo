# backend/src/services/tools/read_file.py
from pathlib import Path
from .base import Tool, ToolResult

class ReadFileTool(Tool):
    """读取文本文件工具"""

    name = "read_file"
    description = "读取文本文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "文件路径"
            }
        },
        "required": ["file_path"]
    }

    async def execute(self, file_path: str) -> ToolResult:
        """读取文件"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    output={},
                    error=f"File not found: {file_path}"
                )

            content = path.read_text(encoding="utf-8")
            return ToolResult(
                success=True,
                output={"content": content}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output={},
                error=str(e)
            )
