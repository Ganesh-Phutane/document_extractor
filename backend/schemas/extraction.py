"""
schemas/extraction.py
──────────────────────
Pydantic v2 schemas for extraction results, verification logs, and field issues.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


# ── Field Issue (used inside VerificationLogResponse) ───────
class FieldIssue(BaseModel):
    field_name: str
    issue_type: str        # "missing" | "wrong_type" | "out_of_range" | "format_error" | "low_confidence" | ...
    expected: str | None
    actual: str | None
    severity: str          # "critical" | "warning"
    suggestion: str | None = None


# ── Extraction ───────────────────────────────────────────────
class ExtractionResponse(BaseModel):
    """GET /extractions/{doc_id}"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    document_id: uuid.UUID
    extraction_version: str | None
    model_used: str | None
    confidence_score: float | None
    is_validated: bool
    is_active_version: bool
    output_blob_path: str | None
    extracted_at: datetime


# ── Verification ─────────────────────────────────────────────
class VerificationLogResponse(BaseModel):
    """One verification run"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    document_id: uuid.UUID
    extracted_data_id: uuid.UUID
    status: str
    overall_confidence: float | None
    report_blob_path: str | None
    triggered_reextraction: bool
    verified_at: datetime
    field_issues_summary: list[dict] | None = None
