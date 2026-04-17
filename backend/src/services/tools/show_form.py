# backend/src/services/tools/show_form.py
from typing import Dict, List
import uuid

from .base import Tool
from .base import ToolResult


class ShowFormTool(Tool):
    """显示动态表单工具（A2UI）"""

    name = "show_form"
    description = "向用户显示一个动态表单，收集多个字段的输入"
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "表单标题"},
            "fields": {
                "type": "array",
                "description": "表单字段列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "label": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "text",
                                "number",
                                "date",
                                "select",
                                "textarea",
                            ],
                        },
                        "required": {"type": "boolean"},
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "default": {"type": "string"},
                        "placeholder": {"type": "string"},
                    },
                },
            },
        },
        "required": ["title", "fields"],
    }

    async def execute(self, title: str, fields: List[Dict]) -> ToolResult:
        """返回表单定义，由前端渲染"""
        form_id = f"form_{uuid.uuid4().hex[:8]}"
        return ToolResult(
            success=True,
            output={
                "type": "form",
                "form_id": form_id,
                "title": title,
                "fields": fields,
            },
            requires_user_input=True,
        )
