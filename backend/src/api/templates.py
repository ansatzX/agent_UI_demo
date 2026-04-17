from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile
from sqlmodel import Session

from ..database import get_session
from ..models.template import Template
from ..schemas.template import FieldInfo
from ..schemas.template import TemplateCreate
from ..schemas.template import TemplateParseResponse
from ..schemas.template import TemplateResponse
from ..services.llm_service import LLMService
from ..services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


def get_template_service(
    session: Session = Depends(get_session),
) -> TemplateService:
    return TemplateService(session, LLMService())


@router.post("", response_model=TemplateResponse)
async def upload_template(
    name: str,
    type: str = "goods",
    description: str = "",
    file: UploadFile = File(...),
    template_service: TemplateService = Depends(get_template_service),
):
    content = await file.read()
    template = await template_service.create_template(
        name=name, type=type, description=description, file_content=content
    )
    return TemplateResponse.model_validate(template)


@router.get("", response_model=List[TemplateResponse])
def list_templates(type: str = None, session: Session = Depends(get_session)):
    query = TemplateService(session, LLMService())
    templates = query.list_templates(type_filter=type)
    return [TemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int, session: Session = Depends(get_session)):
    template = session.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse.model_validate(template)


@router.post("/{template_id}/analyze", response_model=TemplateParseResponse)
async def analyze_template(
    template_id: int,
    template_service: TemplateService = Depends(get_template_service),
):
    template = template_service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    fields = await template_service.analyze_template_fields(template.content)
    return TemplateParseResponse(fields=fields)
