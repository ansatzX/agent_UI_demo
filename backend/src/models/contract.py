from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime
import json


class ContractField(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract.id")
    name: str
    label: str
    value: Optional[str] = None
    placeholder: Optional[str] = None
    field_type: str = "text"
    group: Optional[str] = None
    required: bool = True
    order: int = 0

    contract: "Contract" = Relationship(back_populates="fields")


class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str = "goods"
    status: str = "draft"
    template_id: Optional[int] = Field(default=None, foreign_key="template.id")
    content: Optional[bytes] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    fields: List[ContractField] = Relationship(
        back_populates="contract",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    messages: List["Message"] = Relationship(back_populates="contract")

    def get_fields_dict(self) -> dict:
        return {f.name: f.value for f in self.fields if f.value}
