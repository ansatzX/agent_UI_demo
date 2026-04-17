from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ContractFieldResponse(BaseModel):
    id: int
    name: str
    label: str
    value: Optional[str] = None
    placeholder: Optional[str] = None
    field_type: str = "text"
    group: Optional[str] = None
    required: bool = True
    order: int = 0

    class Config:
        from_attributes = True


class ContractCreate(BaseModel):
    name: str
    type: str = "goods"
    template_id: Optional[int] = None


class ContractResponse(BaseModel):
    id: int
    name: str
    type: str
    status: str
    template_id: Optional[int] = None
    fields: List[ContractFieldResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContractFillRequest(BaseModel):
    field_updates: Dict[str, str]


class ContractFillResponse(BaseModel):
    contract_id: int
    fields: List[ContractFieldResponse]


class RiskIssue(BaseModel):
    level: str
    title: str
    description: str
    suggestion: Optional[str] = None


class RiskReviewResponse(BaseModel):
    issues: List[RiskIssue]
    summary: str
