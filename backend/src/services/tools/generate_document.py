# backend/src/services/tools/generate_document.py
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import uuid

from .base import Tool
from .base import ToolResult


class GenerateDocumentTool(Tool):
    """基于会话上传模板生成合同文档"""

    name = "generate_document"
    description = "基于用户上传的 .docx 模板生成填好字段的合同文档"
    parameters = {
        "type": "object",
        "properties": {
            "template_filename": {
                "type": "string",
                "description": "模板文件的唯一文件名（来自 uploads/ 目录，如 20260417_061104_95b697de_合同模板.docx）",
            },
            "fields": {
                "type": "object",
                "description": "要填充的字段，键值对形式（键与模板中的 {{占位符}} 对应）",
            },
            "filename": {
                "type": "string",
                "description": "输出文件名，如 填写完成的合同.docx",
            },
        },
        "required": ["template_filename", "fields", "filename"],
    }

    def __init__(self, doc_generator, uploads_dir: Path):
        self.generator = doc_generator
        self.uploads_dir = Path(uploads_dir)

    async def execute(
        self, template_filename: str, fields: dict, filename: str
    ) -> ToolResult:
        """生成文档"""
        template_path = self.uploads_dir / template_filename
        if not template_path.exists():
            return ToolResult(
                success=False,
                output={},
                error=f"模板文件不存在: {template_filename}",
            )

        # 所有字段强制转成字符串（python-docx 的 replace 只接受 str）
        str_fields = {k: str(v) for k, v in fields.items()}

        # 给输出文件名加上时间戳 + uuid 前缀，避免重复
        prefix = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )
        stem = Path(filename).stem
        suffix = Path(filename).suffix or ".docx"
        unique_filename = f"{prefix}_{stem}{suffix}"

        output_path = self.uploads_dir / unique_filename
        try:
            await self.generator.fill_template_simple(
                template_path=template_path,
                fields=str_fields,
                output_path=output_path,
            )
            return ToolResult(
                success=True,
                output={
                    "file_path": str(output_path),
                    "filename": unique_filename,
                    "display_name": filename,
                    "download_url": f"/api/files/download/{quote(unique_filename)}",
                },
            )
        except Exception as e:
            return ToolResult(success=False, output={}, error=str(e))
