"""
models/__init__.py
──────────────────
Import all models here so that:
1. SQLAlchemy's metadata is fully populated when Alembic runs
2. All relationship back-references resolve correctly
3. Any module can do: from models import User, Document, etc.
"""
from models.user import User
from models.template import PromptTemplate
from models.document import Document, DocumentPage
from models.extraction import ExtractedData
from models.verification import VerificationLog
from models.prompt_version import PromptVersion
from models.audit import AuditLog
from models.source_mapping import SourceMapping
from models.field_traceability import FieldTraceability
from models.master_data import MasterData

__all__ = [
    "User",
    "PromptTemplate",
    "Document",
    "DocumentPage",
    "ExtractedData",
    "VerificationLog",
    "PromptVersion",
    "AuditLog",
    "SourceMapping",
    "FieldTraceability",
    "MasterData",
]
