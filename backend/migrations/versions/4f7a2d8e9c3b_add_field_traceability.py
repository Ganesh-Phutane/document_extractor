"""add field_traceability

Revision ID: 4f7a2d8e9c3b
Revises: 502836104919
Create Date: 2026-04-01 11:18:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4f7a2d8e9c3b'
down_revision = '502836104919'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'field_traceability',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('extraction_id', sa.String(length=36), nullable=False),
        sa.Column('field_path', sa.String(length=512), nullable=False),
        sa.Column('ref_key', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['extraction_id'], ['extracted_data.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_field_traceability_extraction_id'), 'field_traceability', ['extraction_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_field_traceability_extraction_id'), table_name='field_traceability')
    op.drop_table('field_traceability')
