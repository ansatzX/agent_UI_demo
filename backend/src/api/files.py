from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from ..services.file_service import FileService
from ..services.session_service import SessionService
from typing import List, Optional
import os

router = APIRouter(prefix="/files", tags=["files"])

# 最大文件大小 200MB
MAX_FILE_SIZE = 200 * 1024 * 1024


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None)
):
    """上传文件并关联到会话"""
    # 检查文件格式
    if not file.filename.endswith(('.doc', '.docx')):
        raise HTTPException(status_code=400, detail="只支持 .doc 和 .docx 格式的文件")

    file_service = FileService()
    session_service = SessionService()

    # 读取文件内容
    content = await file.read()

    # 检查文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // (1024*1024)}MB）"
        )

    # 保存文件（使用唯一文件名）
    file_path, unique_filename = file_service.save_upload_file(content, file.filename)

    # 解析文件
    parsed = file_service.parse_docx(file_path)

    # 如果提供了session_id，关联文件到会话
    if session_id and parsed["success"]:
        session_service.add_session_file(
            session_id,
            unique_filename,  # 唯一文件名
            {
                "original_filename": file.filename,  # 原始文件名
                "content": parsed,  # 解析的内容
                "size": len(content)  # 文件大小
            }
        )

    return {
        "filename": file.filename,  # 返回原始文件名用于显示
        "unique_filename": unique_filename,  # 返回唯一文件名用于下载
        "size": len(content),
        "parsed": parsed
    }


@router.get("/list")
async def list_files():
    """列出所有上传的文件"""
    file_service = FileService()
    return file_service.list_uploaded_files()


@router.get("/preview/{filename}")
async def preview_file(filename: str):
    """预览文件内容"""
    file_service = FileService()
    file_info = file_service.get_file_info(filename)

    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    return file_info


@router.get("/download/{filename}")
async def download_file(filename: str):
    """下载文件"""
    file_service = FileService()
    file_path = file_service.uploads_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )


@router.get("/preview-docx/{filename}")
async def preview_docx(filename: str):
    """预览docx文件（返回文件内容供前端组件使用）"""
    file_service = FileService()
    file_path = file_service.uploads_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@router.delete("/{filename}")
async def delete_file(filename: str):
    """删除文件"""
    file_service = FileService()
    file_path = file_service.uploads_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    os.remove(str(file_path))
    return {"message": "文件已删除"}
