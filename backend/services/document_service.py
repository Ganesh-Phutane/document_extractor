"""
services/document_service.py
────────────────────────────
Business logic for Document management: upload, retrieval, and status tracking.
"""
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import UploadFile, HTTPException, status
import uuid
import os

from models.document import Document
from services.blob_service import BlobService
from core.logger import get_logger

logger = get_logger(__name__)

def upload_document(db: Session, file: UploadFile, user_id: str) -> Document:
    """
    Handles the end-to-end document upload:
    1. Creates a database record.
    2. Uploads the file to Azure Blob Storage.
    3. Returns the Document object.
    """
    # 1. Basic Validation
    extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".pdf", ".docx", ".jpg", ".png", ".jpeg", ".csv", ".xlsx", ".xml"]
    if extension not in allowed_extensions:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension}. Supported: {', '.join(allowed_extensions)}"
        )

    # 2. Create DB Record
    doc_id = str(uuid.uuid4())
    blob_service = BlobService()
    blob_path = blob_service.raw_path(doc_id, extension)

    db_doc = Document(
        id=doc_id,
        user_id=user_id,
        filename=file.filename,
        blob_path=blob_path,
        file_size=file.size,
        status="uploaded"
    )
    
    try:
        # 3. Upload to Blob Storage
        file_content = file.file.read()
        blob_service.upload_bytes(data=file_content, blob_path=blob_path)
        
        # 4. Commit to DB
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        logger.info("Document successfully uploaded", extra={"doc_id": doc_id, "user_id": user_id})
        return db_doc
    except Exception as e:
        logger.error(f"Failed to upload document: {e}", extra={"filename": file.filename})
        db.rollback()
        # Cleanup blob if possible? (Optional refinement)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store document. Please try again later."
        )

def get_user_documents(db: Session, user_id: str) -> List[Document]:
    """Retrieves all documents belonging to a specific user."""
    result = db.execute(select(Document).where(Document.user_id == user_id).order_by(Document.uploaded_at.desc()))
    return result.scalars().all()

def get_document_by_id(db: Session, doc_id: str, user_id: str) -> Document | None:
    """Finds a specific document by ID, restricted to the owner."""
    result = db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user_id))
    return result.scalar_one_or_none()

def get_document_preview(db: Session, doc_id: str, user_id: str) -> str:
    """Fetches the extracted Markdown content for a document."""
    doc = get_document_by_id(db, doc_id, user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    allowed_statuses = ["di_processed", "extracted", "verified", "manual_review_required"]
    if doc.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Document is in state '{doc.status}', extraction must be at least 'di_processed' to preview."
        )

    blob_service = BlobService()
    processed_path = blob_service.processed_path(doc_id)
    
    if not blob_service.exists(processed_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extracted Markdown file not found in storage.")
    
    return blob_service.download_text(processed_path)

def get_document_blob(db: Session, doc_id: str, user_id: str, is_markdown: bool = False) -> tuple[bytes, str, str]:
    """
    Fetches raw bytes for a document from Blob Storage.
    Returns (bytes, filename, content_type)
    """
    doc = get_document_by_id(db, doc_id, user_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    blob_service = BlobService()
    
    if is_markdown:
        allowed_statuses = ["di_processed", "extracted", "verified", "manual_review_required"]
        if doc.status not in allowed_statuses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Extraction not yet complete.")
        
        path = blob_service.processed_path(doc_id)
        filename = f"{os.path.splitext(doc.filename)[0]}.md"
        content_type = "text/markdown"
    else:
        path = doc.blob_path
        filename = doc.filename
        # Simple content type detection based on extension
        ext = os.path.splitext(filename)[1].lower()
        content_type = "application/octet-stream"
        if ext == ".pdf": content_type = "application/pdf"
        elif ext == ".docx": content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext in [".jpg", ".jpeg"]: content_type = "image/jpeg"
        elif ext == ".png": content_type = "image/png"

    if not blob_service.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage.")

    return blob_service.download_bytes(path), filename, content_type
