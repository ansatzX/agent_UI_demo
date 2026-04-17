from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    type: str = "goods"
    description: Optional[str] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FieldInfo(BaseModel):
    name: str
    label: str
    placeholder: Optional[str] = None
    field_type: str = "text"
    group: Optional[str] = None
    required: bool = True


class TemplateParseResponse(BaseModel):
    fields: List[FieldInfo]
