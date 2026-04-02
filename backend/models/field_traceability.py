"""
models/field_traceability.py
────────────────────────────
Bridges clean JSON fields to their source reference tags.
"""
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class FieldTraceability(Base):
    __tablename__ = "field_traceability"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    extraction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extracted_data.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_path: Mapped[str] = mapped_column(String(512), nullable=False) # e.g. "metrics.0.value"
    ref_key: Mapped[str] = mapped_column(String(50), nullable=False)     # e.g. "ref_12"

    # Relationships
    extraction: Mapped["ExtractedData"] = relationship("ExtractedData")

    def __repr__(self) -> str:
        return f"<FieldTraceability path={self.field_path} ref={self.ref_key}>"
