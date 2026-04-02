"""
models/verification.py
───────────────────────
Verification_logs table — one row per verification run.
Stores overall result, confidence, and detailed field issues as JSONB.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
# Using generic JSON and String(36) for MySQL


from core.database import Base


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    extracted_data_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extracted_data.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0–1.0

    # report_blob_path: e.g. logs/{doc_id}_{unix_ts}.json
    # Full FieldIssue list stored here as a JSON file in Blob
    report_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # status: "passed" | "failed"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="failed", index=True)

    triggered_reextraction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # field_issues_summary: lightweight summary stored in DB (full report in blob)
    # [{"field_name": "invoice_date", "issue_type": "format_error", "severity": "critical"}]
    field_issues_summary: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)


    # ── Relationships ────────────────────────────────────
    extracted_data: Mapped["ExtractedData"] = relationship("ExtractedData", back_populates="verification_logs")
    document: Mapped["Document"] = relationship("Document", back_populates="verification_logs")

    def __repr__(self) -> str:
        return f"<VerificationLog id={self.id} status={self.status} doc_id={self.document_id}>"
