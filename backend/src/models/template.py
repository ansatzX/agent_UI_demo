from datetime import datetime
from typing import Optional

from sqlmodel import Field
from sqlmodel import SQLModel


class Template(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str = "goods"
    description: Optional[str] = None
    content: bytes
    field_config: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_field_config(self) -> dict:
        if self.field_config:
            import json

            return json.loads(self.field_config)
        return {}
