from datetime import datetime
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


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
    message: str = Field(
        ..., min_length=1, max_length=10000, description="用户消息内容"
    )
    session_id: Optional[str] = Field(
        None, description="会话ID，格式为 YYYYMMDD_HHMMSS"
    )
    option_id: Optional[str] = Field(None, description="选项ID")
    uploaded_file: Optional[UploadedFile] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """验证消息内容"""
        v = v.strip()
        if not v:
            raise ValueError("消息不能为空")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """验证session_id格式"""
        if v and not re.match(r"^\d{8}_\d{6}$", v):
            raise ValueError("session_id格式错误，应为 YYYYMMDD_HHMMSS")
        return v


class ChatResponse(BaseModel):
    message: str
    options: List[Option] = []
    session_id: Optional[str] = None
    token_usage: Optional[TokenUsage] = None
    response_time: Optional[float] = None  # 响应时间（秒）
    tool_results: Optional[List[Dict[str, Any]]] = None


class SubmitFormRequest(BaseModel):
    form_id: str = Field(..., min_length=1, description="表单ID")
    values: Dict[str, Any] = Field(..., min_length=1, description="表单值")
    session_id: str = Field(..., description="会话ID，格式为 YYYYMMDD_HHMMSS")

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: Dict) -> Dict:
        """验证表单值"""
        if not v:
            raise ValueError("表单值不能为空")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """验证session_id格式"""
        if not re.match(r"^\d{8}_\d{6}$", v):
            raise ValueError("session_id格式错误，应为 YYYYMMDD_HHMMSS")
        return v


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    options: List[Option] = []
    timestamp: datetime

    class Config:
        from_attributes = True
