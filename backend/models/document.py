"""
models/document.py
──────────────────
Documents table — one row per uploaded file.
Document_pages table — one row per page of the document.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, BigInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
# Using generic JSON and String(36) for MySQL


from core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("prompt_template.id", ondelete="SET NULL"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_path: Mapped[str] = mapped_column(Text, nullable=False)           # raw/{id}.pdf
    doc_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "invoice"
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # bytes
    # stats: any extra metadata (pages, tables count, etc.)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="uploaded", index=True
        # uploaded → di_processing → di_processed → extracting →
        # extracted → verification_failed → verified →
        # reextracting → manual_review_required
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="documents")
    template: Mapped["PromptTemplate | None"] = relationship("PromptTemplate", back_populates="documents")
    pages: Mapped[list["DocumentPage"]] = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    extracted_data: Mapped[list["ExtractedData"]] = relationship("ExtractedData", back_populates="document", cascade="all, delete-orphan")
    verification_logs: Mapped[list["VerificationLog"]] = relationship("VerificationLog", back_populates="document")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="document")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    page_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)    # processed/{doc_id}_page_{n}.md
    azure_operation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Azure DI operation ID
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────
    document: Mapped["Document"] = relationship("Document", back_populates="pages")

    def __repr__(self) -> str:
        return f"<DocumentPage doc_id={self.document_id} page={self.page_number}>"
