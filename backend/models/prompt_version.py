"""
models/prompt_version.py
─────────────────────────
Prompt_versions table — immutable record of every prompt version ever created.
One new row per learning cycle. Older rows are never deleted.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
# Using String(36) for MySQL


from core.database import Base


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prompt_template.id", ondelete="CASCADE"), nullable=False, index=True
    )

    version_number: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "v3"

    # prompt_blob_path: full prompt file e.g. prompts/invoice/v3.json
    prompt_blob_path: Mapped[str] = mapped_column(Text, nullable=False)

    # correction_blob_path: the learning notes/diff that produced this version
    correction_blob_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # trigger_reason: why this version was created
    # "initial_manual" | "learning_agent" | "manual_override"
    trigger_reason: Mapped[str] = mapped_column(String(50), nullable=False, default="initial_manual")

    # Metrics — measured before and after this version was applied
    avg_confidence_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_confidence_after: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ────────────────────────────────────
    template: Mapped["PromptTemplate"] = relationship("PromptTemplate", back_populates="prompt_versions")

    def __repr__(self) -> str:
        return f"<PromptVersion template={self.template_id} version={self.version_number} trigger={self.trigger_reason}>"
