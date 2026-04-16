from sqlmodel import Session, select
from typing import List, Optional, Dict
from docx import Document
from docxtpl import DocxTemplate
import io
from datetime import datetime
from ..models.contract import Contract, ContractField
from ..models.template import Template
from .llm_service import LLMService


class ContractService:
    def __init__(self, session: Session, llm_service: LLMService):
        self.session = session
        self.llm_service = llm_service

    def create_contract(
        self,
        name: str,
        type: str,
        template_id: Optional[int] = None
    ) -> Contract:
        contract = Contract(name=name, type=type, template_id=template_id)

        if template_id:
            template = self.session.get(Template, template_id)
            if template:
                contract.content = template.content
                field_config = template.get_field_config()
                for i, field_data in enumerate(field_config):
                    field = ContractField(
                        name=field_data.get("name", f"field_{i}"),
                        label=field_data.get("label", f"字段{i}"),
                        placeholder=field_data.get("placeholder"),
                        field_type=field_data.get("field_type", "text"),
                        group=field_data.get("group"),
                        required=field_data.get("required", True),
                        order=i
                    )
                    contract.fields.append(field)

        self.session.add(contract)
        self.session.commit()
        self.session.refresh(contract)
        return contract

    def get_contract(self, contract_id: int) -> Optional[Contract]:
        return self.session.get(Contract, contract_id)

    def list_contracts(self) -> List[Contract]:
        return self.session.exec(
            select(Contract).order_by(Contract.updated_at.desc())
        ).all()

    def update_contract_fields(
        self,
        contract_id: int,
        field_updates: Dict[str, str]
    ) -> Optional[Contract]:
        contract = self.session.get(Contract, contract_id)
        if not contract:
            return None

        for field in contract.fields:
            if field.name in field_updates:
                field.value = field_updates[field.name]

        contract.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(contract)
        return contract

    def fill_contract_document(self, contract_id: int) -> Optional[bytes]:
        contract = self.session.get(Contract, contract_id)
        if not contract or not contract.content:
            return None

        try:
            context = contract.get_fields_dict()

            doc = DocxTemplate(io.BytesIO(contract.content))
            doc.render(context)

            output = io.BytesIO()
            doc.save(output)
            output.seek(0)

            return output.read()
        except Exception as e:
            print(f"Error filling contract: {e}")
            return contract.content

    async def review_contract(self, contract_id: int) -> Optional[Dict]:
        contract = self.session.get(Contract, contract_id)
        if not contract or not contract.content:
            return None

        try:
            doc = Document(io.BytesIO(contract.content))
            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            full_text = "\n".join(text_parts)
            return await self.llm_service.review_contract(full_text[:12000])
        except Exception as e:
            print(f"Error reviewing contract: {e}")
            return None

    def update_status(self, contract_id: int, status: str) -> Optional[Contract]:
        contract = self.session.get(Contract, contract_id)
        if not contract:
            return None

        contract.status = status
        contract.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(contract)
        return contract
