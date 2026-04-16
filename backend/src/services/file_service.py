from pathlib import Path
from typing import Optional, Dict, Any
from docx import Document
from ..config import settings
import uuid
import re
from datetime import datetime


class FileService:
    def __init__(self):
        # 上传文件存储在项目根目录的uploads目录
        self.uploads_dir = settings.project_root / "uploads"
        self.uploads_dir.mkdir(exist_ok=True)

    def generate_unique_filename(self, original_filename: str) -> str:
        """生成唯一的文件名，避免特殊字符问题"""
        # 提取文件扩展名
        ext = Path(original_filename).suffix.lower()

        # 清理原始文件名，移除特殊字符
        clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', Path(original_filename).stem)
        clean_name = clean_name.strip('_')[:50]  # 限制长度

        # 生成唯一ID
        unique_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]

        # 组合成唯一文件名
        unique_filename = f"{unique_id}_{clean_name}{ext}"

        return unique_filename

    def save_upload_file(self, file_content: bytes, original_filename: str) -> tuple[Path, str]:
        """保存上传的文件，返回文件路径和唯一文件名"""
        unique_filename = self.generate_unique_filename(original_filename)
        file_path = self.uploads_dir / unique_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        return file_path, unique_filename

    def parse_docx(self, file_path: Path) -> Dict[str, Any]:
        """解析Word文档，提取文本内容"""
        try:
            doc = Document(str(file_path))

            # 提取所有段落文本
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)

            # 提取表格内容
            tables = []
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                tables.append(table_data)

            return {
                "success": True,
                "paragraphs": paragraphs,
                "tables": tables,
                "full_text": "\n".join(paragraphs)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        file_path = self.uploads_dir / filename
        if not file_path.exists():
            return None

        # 解析文档
        parsed = self.parse_docx(file_path)

        return {
            "filename": filename,
            "path": str(file_path),
            "parsed": parsed
        }

    def list_uploaded_files(self) -> list:
        """列出所有上传的文件"""
        files = []
        for file_path in self.uploads_dir.glob("*.docx"):
            files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size
            })
        for file_path in self.uploads_dir.glob("*.doc"):
            files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size
            })
        return files
