from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session
from typing import List
from ..database import get_session
from ..models.contract import Contract
from ..schemas.contract import (
    ContractCreate, ContractResponse, ContractFillRequest,
    ContractFillResponse, RiskReviewResponse
)
from ..services.contract_service import ContractService
from ..services.llm_service import LLMService

router = APIRouter(prefix="/contracts", tags=["contracts"])


def get_contract_service(session: Session = Depends(get_session)) -> ContractService:
    return ContractService(session, LLMService())


@router.post("", response_model=ContractResponse)
def create_contract(
    request: ContractCreate,
    contract_service: ContractService = Depends(get_contract_service)
):
    contract = contract_service.create_contract(
        name=request.name,
        type=request.type,
        template_id=request.template_id
    )
    return ContractResponse.model_validate(contract)


@router.get("", response_model=List[ContractResponse])
def list_contracts(
    contract_service: ContractService = Depends(get_contract_service)
):
    contracts = contract_service.list_contracts()
    return [ContractResponse.model_validate(c) for c in contracts]


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: int,
    session: Session = Depends(get_session)
):
    contract = session.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractResponse.model_validate(contract)


@router.patch("/{contract_id}/fields", response_model=ContractResponse)
def fill_contract_fields(
    contract_id: int,
    request: ContractFillRequest,
    contract_service: ContractService = Depends(get_contract_service)
):
    contract = contract_service.update_contract_fields(
        contract_id,
        request.field_updates
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractResponse.model_validate(contract)


@router.post("/{contract_id}/generate")
def generate_contract(
    contract_id: int,
    contract_service: ContractService = Depends(get_contract_service)
):
    content = contract_service.fill_contract_document(contract_id)
    if not content:
        raise HTTPException(status_code=404, detail="Contract not found")

    contract = contract_service.get_contract(contract_id)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={contract.name}.docx"}
    )


@router.post("/{contract_id}/review", response_model=RiskReviewResponse)
async def review_contract(
    contract_id: int,
    contract_service: ContractService = Depends(get_contract_service)
):
    result = await contract_service.review_contract(contract_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contract not found")
    return RiskReviewResponse(**result)


@router.patch("/{contract_id}/status", response_model=ContractResponse)
def update_status(
    contract_id: int,
    status: str,
    contract_service: ContractService = Depends(get_contract_service)
):
    contract = contract_service.update_status(contract_id, status)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractResponse.model_validate(contract)
