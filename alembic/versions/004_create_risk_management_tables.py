"""create risk management tables

Revision ID: 004
Revises: 003
Create Date: 2024-11-08 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create risk_limits and strategy_limits tables."""
    
    # Create risk_limits table
    op.create_table(
        'risk_limits',
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trading_mode', sa.String(10), nullable=False),
        sa.Column('max_loss_limit', sa.Numeric(15, 2), nullable=False),
        sa.Column('current_loss', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('is_breached', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('breached_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('account_id', 'trading_mode'),
        sa.ForeignKeyConstraint(['account_id'], ['user_accounts.id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "trading_mode IN ('paper', 'live')",
            name='check_risk_limits_trading_mode'
        )
    )
    
    # Create strategy_limits table
    op.create_table(
        'strategy_limits',
        sa.Column('trading_mode', sa.String(10), nullable=False),
        sa.Column('max_concurrent_strategies', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('trading_mode'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "trading_mode IN ('paper', 'live')",
            name='check_strategy_limits_trading_mode'
        )
    )
    
    # Insert default strategy limits
    op.execute("""
        INSERT INTO strategy_limits (trading_mode, max_concurrent_strategies)
        VALUES ('paper', 5), ('live', 5)
    """)


def downgrade():
    """Drop risk_limits and strategy_limits tables."""
    op.drop_table('strategy_limits')
    op.drop_table('risk_limits')
