"""
routes/documents.py
───────────────────
Endpoints for document upload, listing, and metadata retrieval.
"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.orm import Session

from core.dependencies import get_db, get_current_user
from models.user import User
from schemas.document import (
    DocumentUploadResponse, 
    DocumentListItem, 
    DocumentStatusResponse
)
from services import document_service

router = APIRouter(tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...)
):
    """
    Uploads a document to Azure Blob Storage and creates a record in the database.
    """
    doc = document_service.upload_document(db, file=file, user_id=current_user.id)
    
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "message": "Document uploaded successfully and queued for processing."
    }


@router.get("/", response_model=List[DocumentListItem])
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Lists all documents belonging to the authenticated user.
    """
    return document_service.get_user_documents(db, user_id=current_user.id)


@router.get("/{document_id}", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves the status and metadata for a specific document.
    """
    doc = document_service.get_document_by_id(db, doc_id=document_id, user_id=current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return doc


@router.get("/{document_id}/preview/markdown")
def preview_markdown(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Returns the content of the extracted Markdown file.
    """
    content = document_service.get_document_preview(db, document_id, current_user.id)
    return {"content": content}


@router.get("/{document_id}/download/original")
def download_original(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Downloads the original uploaded file.
    """
    content, filename, content_type = document_service.get_document_blob(
        db, document_id, current_user.id, is_markdown=False
    )
    return StreamingResponse(
        BytesIO(content),
        media_type=content_type,
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.get("/{document_id}/download/markdown")
def download_markdown(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Downloads the extracted Markdown file.
    """
    content, filename, content_type = document_service.get_document_blob(
        db, document_id, current_user.id, is_markdown=True
    )
    return StreamingResponse(
        BytesIO(content),
        media_type=content_type,
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )
