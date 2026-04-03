"""add_master_data_records

Revision ID: a1b2c3d4e5f6
Revises: 650c1f8c1fb6
Create Date: 2026-03-30

Creates the `master_data_records` table — one structured row per
financial period. Stores all fixed schema columns (gross_sales, ebita, etc.)
plus a JSON blob for dynamically-extracted extra fields.

This migration is additive and does NOT alter any existing table.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "650c1f8c1fb6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create master_data parent table ──
    op.create_table(
        "master_data",
        sa.Column("id",               sa.String(36),  primary_key=True),
        sa.Column("document_id",      sa.String(36),  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extraction_id",    sa.String(36),  sa.ForeignKey("extracted_data.id", ondelete="SET NULL"), nullable=True),
        sa.Column("blob_path",        sa.Text(),      nullable=False),
        sa.Column("company_name",     sa.String(255), nullable=True),
        sa.Column("confidence_score", sa.Float(),     nullable=True),
        sa.Column("is_approved",      sa.Boolean(),   nullable=False, server_default=sa.text("false")),
        sa.Column("version",          sa.String(20),  nullable=False, server_default="v3"),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_master_data_document_id", "master_data", ["document_id"])
    op.create_index("ix_master_data_company_name", "master_data", ["company_name"])

    # ── Create master_data_records child table ──
    op.create_table(
        "master_data_records",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("master_data_id", sa.String(36),  sa.ForeignKey("master_data.id",  ondelete="CASCADE"), nullable=False),
        sa.Column("document_id",    sa.String(36),  sa.ForeignKey("documents.id",    ondelete="CASCADE"), nullable=False),

        # Fixed schema columns
        sa.Column("company_name",   sa.String(255), nullable=True),
        sa.Column("period",         sa.String(100), nullable=True),
        sa.Column("frequency",      sa.String(50),  nullable=True),
        sa.Column("gross_sales",    sa.Float(),     nullable=True),
        sa.Column("ebita",          sa.Float(),     nullable=True),
        sa.Column("net_revenue",    sa.Float(),     nullable=True),
        sa.Column("gross_profit",   sa.Float(),     nullable=True),
        sa.Column("total_debt",     sa.Float(),     nullable=True),

        # Dynamic extra fields — serialised JSON string
        sa.Column("extra_fields",   sa.Text(),      nullable=True),

        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mdr_master_data_id", "master_data_records", ["master_data_id"])
    op.create_index("ix_mdr_document_id",    "master_data_records", ["document_id"])
    op.create_index("ix_mdr_company_name",   "master_data_records", ["company_name"])
    op.create_index("ix_mdr_period",         "master_data_records", ["period"])


def downgrade() -> None:
    # ── Drop master_data_records ──
    op.drop_index("ix_mdr_period",         table_name="master_data_records")
    op.drop_index("ix_mdr_company_name",   table_name="master_data_records")
    op.drop_index("ix_mdr_document_id",    table_name="master_data_records")
    op.drop_index("ix_mdr_master_data_id", table_name="master_data_records")
    op.drop_table("master_data_records")

    # ── Drop master_data ──
    op.drop_index("ix_master_data_company_name", table_name="master_data")
    op.drop_index("ix_master_data_document_id",    table_name="master_data")
    op.drop_table("master_data")
