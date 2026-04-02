"""
schemas/document.py
────────────────────
Pydantic v2 schemas for Documents and DocumentPages.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """Returned immediately after a file upload is accepted"""
    document_id: uuid.UUID
    filename: str
    status: str
    message: str


class DocumentStatusResponse(BaseModel):
    """GET /documents/{id}"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    filename: str
    doc_type: str | None
    status: str
    file_size: int | None
    uploaded_at: datetime
    processed_at: datetime | None
    template_id: uuid.UUID | None


class DocumentListItem(BaseModel):
    """Item in GET /documents/ list"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    filename: str
    doc_type: str | None
    status: str
    file_size: int | None
    uploaded_at: datetime
    stats: dict | None = None


class DocumentPageResponse(BaseModel):
    """One page entry"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    page_number: int
    page_blob_path: str | None
    extracted_at: datetime | None
