"""
schemas/template.py
────────────────────
Pydantic v2 schemas for PromptTemplate (document type + field config).
"""
import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel


# ── FieldConfig (nested inside TemplateCreate) ───────────────
class FieldConfig(BaseModel):
    """Defines one extractable field for a document type."""
    field_name: str                    # snake_case e.g. "invoice_date"
    display_name: str                  # Human readable e.g. "Invoice Date"
    data_type: Literal["string", "number", "date", "boolean", "list", "enum"]
    required: bool = True
    description: str                   # Injected into LLM prompt
    example_value: str                 # Shown to LLM as example
    allowed_values: list[str] = []     # For enum type only
    min_value: float | None = None     # For number type
    max_value: float | None = None     # For number type
    max_length: int | None = None      # For string type
    cross_check: str | None = None     # e.g. "total == sum(line_items[*].amount)"


# ── Template CRUD Schemas ─────────────────────────────────────
class TemplateCreate(BaseModel):
    """POST /templates body"""
    name: str
    document_type: str
    fields: list[FieldConfig]


class TemplateResponse(BaseModel):
    """GET /templates/{id}"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    document_type: str
    field_mapping: Any              # Raw JSONB — list of FieldConfig dicts
    current_prompt_version: str
    base_prompt_blob_path: str | None
    optimized_prompt_blob_path: str | None
    updated_at: datetime


class TemplateListItem(BaseModel):
    """Item in GET /templates/ list"""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    document_type: str
    current_prompt_version: str
    updated_at: datetime
