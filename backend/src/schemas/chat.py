from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime


class Option(BaseModel):
    id: str
    label: str
    description: str
    action: str
    payload: Optional[dict] = None


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class UploadedFile(BaseModel):
    filename: str
    original_filename: Optional[str] = None
    size: Optional[int] = None
    content: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    option_id: Optional[str] = None
    uploaded_file: Optional[UploadedFile] = None


class ChatResponse(BaseModel):
    message: str
    options: List[Option] = []
    session_id: Optional[str] = None
    token_usage: Optional[TokenUsage] = None
    response_time: Optional[float] = None  # 响应时间（秒）


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    options: List[Option] = []
    timestamp: datetime

    class Config:
        from_attributes = True
