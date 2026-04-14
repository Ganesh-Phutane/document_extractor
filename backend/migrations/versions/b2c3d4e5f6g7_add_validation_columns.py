"""add validation columns

Revision ID: b2c3d4e5f6g7
Revises: 4f7a2d8e9c3b
Create Date: 2026-04-06 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = '4f7a2d8e9c3b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to master_data table
    op.add_column('master_data', sa.Column('validation_status', sa.String(length=50), nullable=True))
    op.add_column('master_data', sa.Column('validation_issues', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Set default values for existing records
    op.execute("UPDATE master_data SET validation_status = 'validation_passed' WHERE validation_status IS NULL")
    op.execute("UPDATE master_data SET validation_issues = '{}' WHERE validation_issues IS NULL")
    
    # Make non-nullable if desired, but for now we keep them nullable for safety or set a server default
    op.alter_column('master_data', 'validation_status', nullable=False, server_default='pending')


def downgrade() -> None:
    op.drop_column('master_data', 'validation_issues')
    op.drop_column('master_data', 'validation_status')
