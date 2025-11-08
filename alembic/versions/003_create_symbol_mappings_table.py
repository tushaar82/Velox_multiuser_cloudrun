"""create symbol mappings table

Revision ID: 003
Revises: 002
Create Date: 2024-11-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Create symbol_mappings table."""
    op.create_table(
        'symbol_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('standard_symbol', sa.String(50), nullable=False),
        sa.Column('broker_name', sa.String(50), nullable=False),
        sa.Column('broker_symbol', sa.String(100), nullable=False),
        sa.Column('broker_token', sa.String(100), nullable=False),
        sa.Column('exchange', sa.String(10), nullable=False),
        sa.Column('instrument_type', sa.String(10), nullable=False),
        sa.Column('lot_size', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('tick_size', sa.Numeric(10, 4), nullable=False, server_default='0.05'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )
    
    # Create indexes for faster lookups
    op.create_index(
        'idx_symbol_mappings_broker',
        'symbol_mappings',
        ['broker_name', 'standard_symbol'],
        unique=True
    )
    op.create_index(
        'idx_symbol_mappings_token',
        'symbol_mappings',
        ['broker_name', 'broker_token']
    )


def downgrade():
    """Drop symbol_mappings table."""
    op.drop_index('idx_symbol_mappings_token')
    op.drop_index('idx_symbol_mappings_broker')
    op.drop_table('symbol_mappings')
