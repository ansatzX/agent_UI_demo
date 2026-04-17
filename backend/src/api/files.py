import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import UploadFile
from fastapi.responses import FileResponse
import magic

from ..services.file_service import FileService
from ..services.session_service import SessionService

router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)

# 最大文件大小 200MB
MAX_FILE_SIZE = 200 * 1024 * 1024


def validate_file_path(filename: str, uploads_dir: Path) -> Path:
    """验证文件路径，防止路径遍历攻击"""
    file_path = (uploads_dir / filename).resolve()
    if not str(file_path).startswith(str(uploads_dir.resolve())):
        logger.error(f"路径遍历攻击检测: {filename}")
        raise HTTPException(status_code=400, detail="Invalid file path")
    return file_path


def validate_file_type(file_content: bytes, filename: str) -> None:
    """验证文件类型（MIME类型 + 魔数验证）"""
    try:
        mime = magic.from_buffer(file_content, mime=True)
        if (
            mime
            != "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            logger.error(f"无效的文件类型: {mime}, 文件名: {filename}")
            raise HTTPException(
                status_code=400, detail=f"Invalid file type: {mime}"
            )
    except Exception as e:
        logger.error(f"文件类型验证失败: {e}")
        raise HTTPException(
            status_code=400, detail="File type validation failed"
        )

    if not filename.endswith(".docx"):
        logger.error(f"无效的文件扩展名: {filename}")
        raise HTTPException(
            status_code=400, detail="Only .docx files are allowed"
        )


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None),
):
    """上传文件并关联到会话"""
    # 检查文件格式（只允许 .docx）
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 格式的文件")

    file_service = request.app.state.file_service
    session_service = SessionService()

    # 读取文件内容
    content = await file.read()

    # 检查文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // (1024*1024)}MB）",
        )

    # 验证文件类型（MIME + 魔数）
    validate_file_type(content, file.filename)

    # 保存文件（使用唯一文件名）
    file_path, unique_filename = file_service.save_upload_file(
        content, file.filename
    )

    # 使用 python-docx 解析文件
    parsed = await file_service.process_uploaded_file(
        file_path, unique_filename
    )

    # 如果解析成功，关联文件到会话
    if parsed["success"]:
        # 如果没有提供 session_id，自动创建
        if not session_id:
            session_id = session_service.create_session()

        session_service.add_session_file(
            session_id,
            unique_filename,  # 唯一文件名
            {
                "original_filename": file.filename,  # 原始文件名
                "content": parsed,  # 解析的内容
                "size": len(content),  # 文件大小
            },
        )

    return {
        "filename": file.filename,  # 返回原始文件名用于显示
        "unique_filename": unique_filename,  # 返回唯一文件名用于下载
        "size": len(content),
        "parsed": parsed,
        "session_id": session_id,  # 返回 session_id（可能是新创建的）
    }


@router.get("/list")
async def list_files(request: Request):
    """列出所有上传的文件"""
    file_service = request.app.state.file_service
    return file_service.list_uploaded_files()


@router.get("/preview/{filename}")
async def preview_file(filename: str, request: Request):
    """预览文件内容"""
    file_service = request.app.state.file_service

    # 验证文件路径
    validate_file_path(filename, file_service.uploads_dir)

    file_info = file_service.get_file_info(filename)

    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    return file_info


@router.get("/download/{filename}")
async def download_file(filename: str, request: Request):
    """下载文件"""
    file_service = request.app.state.file_service

    # 验证文件路径
    file_path = validate_file_path(filename, file_service.uploads_dir)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/preview-docx/{filename}")
async def preview_docx(filename: str, request: Request):
    """预览docx文件（返回文件内容供前端组件使用）"""
    file_service = request.app.state.file_service

    # 验证文件路径
    file_path = validate_file_path(filename, file_service.uploads_dir)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.delete("/{filename}")
async def delete_file(filename: str, request: Request):
    """删除文件"""
    file_service = request.app.state.file_service

    # 验证文件路径
    file_path = validate_file_path(filename, file_service.uploads_dir)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    os.remove(str(file_path))
    return {"message": "文件已删除"}
