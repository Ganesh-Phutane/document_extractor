"""
models/source_mapping.py
────────────────────────
Stores coordinates (bbox, page, grid) for reference tags injected into Markdown.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class SourceMapping(Base):
    __tablename__ = "source_mapping"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ref_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g. "ref_0"
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)           # pdf, excel, etc.
    
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True) # [x, y, w, h]
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    col_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xpath: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document")

    def __repr__(self) -> str:
        return f"<SourceMapping doc={self.document_id} key={self.ref_key}>"
