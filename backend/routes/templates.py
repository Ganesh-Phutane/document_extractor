"""
routes/templates.py
───────────────────
Endpoints for managing document extraction templates and field mappings.
"""
from typing import Annotated, List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.dependencies import get_db, get_current_user
from models.user import User
from models.template import PromptTemplate
from services.template_service import TemplateService

router = APIRouter(tags=["Templates"])

@router.get("/", response_model=List[Dict[str, Any]])
def list_templates(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Lists all available extraction templates.
    """
    templates = db.query(PromptTemplate).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "document_type": t.document_type,
            "field_mapping": t.field_mapping,
            "current_version": t.current_prompt_version
        }
        for t in templates
    ]

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_template(
    name: str,
    doc_type: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    field_mapping: Optional[List[Dict[str, Any]]] = None,
):
    """
    Creates a new extraction template.
    """
    service = TemplateService(db)
    try:
        template = service.create_template(name, doc_type, field_mapping)
        return template
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{template_id}", response_model=Dict[str, Any])
def get_template(
    template_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves a specific template by ID.
    """
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": template.id,
        "name": template.name,
        "document_type": template.document_type,
        "field_mapping": template.field_mapping,
        "current_version": template.current_prompt_version
    }
