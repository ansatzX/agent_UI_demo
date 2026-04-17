from typing import List

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request

from ..schemas.chat import ChatRequest
from ..schemas.chat import ChatResponse
from ..schemas.chat import MessageResponse
from ..schemas.chat import SubmitFormRequest
from ..services.session_service import SessionService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    # 从 app.state 获取已初始化的 AgentService
    agent_service = req.app.state.agent_service

    # 转换文件信息为dict
    uploaded_file_dict = None
    if request.uploaded_file:
        uploaded_file_dict = request.uploaded_file.model_dump()

    result = await agent_service.handle_message(
        request.message,
        request.session_id,
        request.option_id,
        uploaded_file_dict,
    )
    return ChatResponse(**result)


@router.get("/history/{session_id}", response_model=List[dict])
async def get_history(session_id: str):
    """获取会话历史"""
    session_service = SessionService()
    messages = session_service.get_messages(session_id)
    return messages


@router.get("/sessions", response_model=List[dict])
async def list_sessions():
    """列出所有会话"""
    session_service = SessionService()
    return session_service.list_sessions()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    session_service = SessionService()
    success = session_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@router.get("/sessions/{session_id}/file")
async def get_session_file(session_id: str):
    """获取会话关联的文件"""
    session_service = SessionService()
    uploaded_file = session_service.get_session_file(session_id)

    if not uploaded_file:
        return None

    return {
        "filename": uploaded_file.get("filename"),
        "original_filename": uploaded_file.get("original_filename"),
        "content": uploaded_file.get("content"),
        "uploaded_at": uploaded_file.get("uploaded_at"),
    }


@router.post("/submit-form", response_model=ChatResponse)
async def submit_form(request: SubmitFormRequest, req: Request):
    """处理表单提交"""
    agent_service = req.app.state.agent_service

    result = await agent_service.handle_form_submission(
        request.form_id, request.values, request.session_id
    )
    return ChatResponse(**result)
