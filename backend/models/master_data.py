"""
models/master_data.py
───────────────────────
Master_data       — one header row per document (links to blob).
MasterDataRecord  — one structured row per (document_id, period),
                    stores all fixed schema columns + extra_fields JSON.
"""
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class MasterData(Base):
    __tablename__ = "master_data"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extraction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("extracted_data.id", ondelete="SET NULL"), nullable=True
    )

    blob_path: Mapped[str] = mapped_column(Text, nullable=False)  # master_data/{doc_id}_result.json
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # ── Validation ───────────────────────────────────────
    # status: pending, validation_passed, validation_failed, conflict_detected, approved
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    validation_issues: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    version: Mapped[str] = mapped_column(String(20), nullable=False, default="v3")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────
    document: Mapped["Document"] = relationship("Document")
    records: Mapped[list["MasterDataRecord"]] = relationship(
        "MasterDataRecord", back_populates="master_data", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MasterData id={self.id} doc_id={self.document_id} company={self.company_name}>"


class MasterDataRecord(Base):
    """
    One structured row per financial period extracted from a document.
    Fixed columns mirror the target schema; any dynamic columns discovered
    by Gemini when extract_extra_fields=True are stored as JSON in extra_fields.
    """
    __tablename__ = "master_data_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    master_data_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("master_data.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Fixed schema columns ─────────────────────────────
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    period: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gross_sales: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ebita: Mapped[str | None] = mapped_column(String(100), nullable=True)
    net_revenue: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gross_profit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total_debt: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Dynamic columns (extra fields from Gemini when flag is on) ───
    _extra_fields_json: Mapped[str | None] = mapped_column(
        "extra_fields", Text, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────
    master_data: Mapped["MasterData"] = relationship("MasterData", back_populates="records")

    # ── extra_fields helper (serialize/deserialize JSON) ─
    @property
    def extra_fields(self) -> dict:
        if self._extra_fields_json:
            try:
                return json.loads(self._extra_fields_json)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @extra_fields.setter
    def extra_fields(self, value: dict) -> None:
        self._extra_fields_json = json.dumps(value, default=str) if value else None

    def to_dict(self) -> dict:
        """Serialise to the fixed DB schema shape for API responses."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "company_name": self.company_name,
            "period": self.period,
            "frequency": self.frequency,
            "currency": self.currency,
            "unit": self.unit,
            "gross_sales": self.gross_sales,
            "ebita": self.ebita,
            "net_revenue": self.net_revenue,
            "gross_profit": self.gross_profit,
            "total_debt": self.total_debt,
            "extra_fields": self.extra_fields,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<MasterDataRecord doc={self.document_id} period={self.period}>"
