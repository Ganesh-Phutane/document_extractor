"""
models/audit.py
────────────────
Audit_logs table — every user action is recorded here for traceability.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Using String(36) for MySQL


from core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # action: what the user did
    # e.g. "login", "upload_document", "view_extraction", "export_data", "manual_correction"
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


    # export_blob_path: if the action resulted in an export, where is it stored
    export_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ────────────────────────────────────
    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")
    document: Mapped["Document | None"] = relationship("Document", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} user_id={self.user_id}>"
