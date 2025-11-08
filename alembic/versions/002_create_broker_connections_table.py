"""create broker connections table

Revision ID: 002
Revises: 001
Create Date: 2024-11-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Create broker_connections table."""
    op.create_table(
        'broker_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id'), nullable=False),
        sa.Column('broker_name', sa.String(50), nullable=False),
        sa.Column('credentials_encrypted', sa.Text(), nullable=False),
        sa.Column('is_connected', sa.Boolean(), default=False),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Create index for faster lookups
    op.create_index('idx_broker_connections_account', 'broker_connections', ['account_id'])


def downgrade():
    """Drop broker_connections table."""
    op.drop_index('idx_broker_connections_account')
    op.drop_table('broker_connections')
