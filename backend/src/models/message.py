from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import json


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    role: str
    content: str
    options_data: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    contract: Optional["Contract"] = Relationship(back_populates="messages")

    @property
    def options(self) -> list:
        if self.options_data:
            return json.loads(self.options_data)
        return []

    @options.setter
    def options(self, value: list):
        self.options_data = json.dumps(value, ensure_ascii=False)
