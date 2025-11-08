"""create backtests table

Revision ID: 006
Revises: 005
Create Date: 2024-01-06 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create backtests table
    op.create_table(
        'backtests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=False),
        sa.Column('metrics', postgresql.JSON(), nullable=True),
        sa.Column('status', sa.Enum('running', 'completed', 'failed', name='backteststatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True)
    )
    
    # Create indexes for backtests
    op.create_index('idx_backtests_strategy', 'backtests', ['strategy_id', 'created_at'])
    op.create_index('idx_backtests_account', 'backtests', ['account_id', 'created_at'])
    op.create_index('idx_backtests_status', 'backtests', ['status'])


def downgrade():
    # Drop backtests table and indexes
    op.drop_index('idx_backtests_status', 'backtests')
    op.drop_index('idx_backtests_account', 'backtests')
    op.drop_index('idx_backtests_strategy', 'backtests')
    op.drop_table('backtests')
    
    # Drop enum
    op.execute('DROP TYPE IF EXISTS backteststatus')
