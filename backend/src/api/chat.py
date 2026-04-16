from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from ..database import get_session
from ..schemas.chat import ChatRequest, ChatResponse, MessageResponse
from ..services.agent_service import AgentService
from ..services.llm_service import LLMService
from ..services.contract_service import ContractService
from ..services.template_service import TemplateService
from ..services.session_service import SessionService
from typing import List

router = APIRouter(prefix="/chat", tags=["chat"])


def get_agent_service(session: Session = Depends(get_session)) -> AgentService:
    llm = LLMService()
    contract = ContractService(session, llm)
    template = TemplateService(session, llm)
    return AgentService(session, llm, contract, template)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    # 转换文件信息为dict
    uploaded_file_dict = None
    if request.uploaded_file:
        uploaded_file_dict = request.uploaded_file.model_dump()

    result = await agent_service.handle_message(
        request.message,
        request.session_id,
        request.option_id,
        uploaded_file_dict
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
        "uploaded_at": uploaded_file.get("uploaded_at")
    }
