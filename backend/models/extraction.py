"""
models/extraction.py
─────────────────────
Extracted_data table — one row per extraction attempt.
Tracks which prompt version was used, confidence, validation status.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
# Using String(36) for MySQL UUID


from core.database import Base


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("prompt_template.id", ondelete="SET NULL"), nullable=True, index=True
    )

    output_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)    # extracted/{doc_id}.json
    approved_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)  # approved copy after human review

    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)   # e.g. "gemini-1.5-pro"
    extraction_version: Mapped[str | None] = mapped_column(String(20), nullable=True)  # prompt version used e.g. "v2"
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–1.0 average across fields

    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active_version: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # When re-extraction happens, old row is set is_active_version=False, new row created

    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ────────────────────────────────────
    document: Mapped["Document"] = relationship("Document", back_populates="extracted_data")
    template: Mapped["PromptTemplate | None"] = relationship("PromptTemplate", back_populates="extracted_data")
    verification_logs: Mapped[list["VerificationLog"]] = relationship("VerificationLog", back_populates="extracted_data")

    def __repr__(self) -> str:
        return f"<ExtractedData id={self.id} doc_id={self.document_id} validated={self.is_validated}>"
