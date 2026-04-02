"""add_source_mapping

Revision ID: 61a9d310aee0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-01

Creates the `source_mapping` table — stores coordinates (bbox, page, grid) 
for reference tags injected into Markdown.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "61a9d310aee0"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_mapping",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("document_id",    sa.String(36),  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ref_key",        sa.String(50),  nullable=False),
        sa.Column("file_type",      sa.String(20),  nullable=False),
        
        sa.Column("page_number",    sa.Integer(),   nullable=True),
        sa.Column("bbox",           sa.JSON(),      nullable=True),
        sa.Column("row_index",      sa.Integer(),   nullable=True),
        sa.Column("col_index",      sa.Integer(),   nullable=True),
        sa.Column("xpath",          sa.Text(),      nullable=True),
        
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_source_mapping_document_id", "source_mapping", ["document_id"])
    op.create_index("ix_source_mapping_ref_key",    "source_mapping", ["ref_key"])


def downgrade() -> None:
    op.drop_index("ix_source_mapping_ref_key",    table_name="source_mapping")
    op.drop_index("ix_source_mapping_document_id", table_name="source_mapping")
    op.drop_table("source_mapping")
