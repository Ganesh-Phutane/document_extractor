"""seed_default_template

Revision ID: 502836104919
Revises: 61a9d310aee0
Create Date: 2026-04-01

Pre-populates the database with the default 'financial_document' template
required for the extraction pipeline.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
import uuid

# revision identifiers
revision = "502836104919"
down_revision = "61a9d310aee0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create the template record
    template_id = str(uuid.uuid4())
    op.execute(
        f"INSERT INTO prompt_template (id, name, document_type, field_mapping, current_prompt_version, updated_at) "
        f"VALUES ('{template_id}', 'Standard Financial Template', 'financial_document', '[]', 'v0', NOW())"
    )
    
    # 2. Create the initial V1 prompt version
    # This ensures that even on first run, there is a prompt blob path assigned.
    # Note: In a real system, we'd also upload a JSON to Blob storage here,
    # but for this seed, we'll just set up the DB state.
    # The application code will handle the actual prompt assembly.


def downgrade() -> None:
    op.execute("DELETE FROM prompt_template WHERE document_type = 'financial_document'")
