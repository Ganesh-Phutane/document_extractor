"""
models/template.py
──────────────────
Prompt_template table — defines a document type and how to extract it.
One template per document type (e.g. "invoice", "purchase_order").
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
# Using generic JSON for MySQL compatibility


from core.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_template"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)         # e.g. "Invoice Extractor"
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)  # e.g. "invoice"

    # field_mapping: JSON list of FieldConfig objects
    # [{"field_name": "invoice_date", "data_type": "date", "required": true, ...}]
    field_mapping: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


    base_prompt_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)        # prompts/invoice/v1.json
    optimized_prompt_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)   # prompts/invoice/latest.json
    current_prompt_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="template")
    extracted_data: Mapped[list["ExtractedData"]] = relationship("ExtractedData", back_populates="template")
    prompt_versions: Mapped[list["PromptVersion"]] = relationship("PromptVersion", back_populates="template")

    def __repr__(self) -> str:
        return f"<PromptTemplate doc_type={self.document_type} version={self.current_prompt_version}>"
