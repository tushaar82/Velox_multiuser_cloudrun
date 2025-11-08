"""create order trade position tables

Revision ID: 005
Revises: 004
Create Date: 2024-01-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='orderside'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=True),
        sa.Column('stop_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('trading_mode', sa.Enum('paper', 'live', name='tradingmode'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'submitted', 'partial', 'filled', 'cancelled', 'rejected', name='orderstatus'), nullable=False),
        sa.Column('filled_quantity', sa.Integer(), default=0),
        sa.Column('average_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('broker_order_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'))
    )
    
    # Create indexes for orders
    op.create_index('idx_orders_account', 'orders', ['account_id', 'created_at'])
    op.create_index('idx_orders_status', 'orders', ['status', 'trading_mode'])
    op.create_index('idx_orders_broker', 'orders', ['broker_order_id'])
    
    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='orderside'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('commission', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('trading_mode', sa.Enum('paper', 'live', name='tradingmode'), nullable=False),
        sa.Column('executed_at', sa.DateTime(), server_default=sa.text('NOW()'))
    )
    
    # Create foreign key for trades
    op.create_foreign_key('fk_trades_order', 'trades', 'orders', ['order_id'], ['id'])
    
    # Create indexes for trades
    op.create_index('idx_trades_account', 'trades', ['account_id', 'executed_at'])
    op.create_index('idx_trades_order', 'trades', ['order_id'])
    op.create_index('idx_trades_symbol', 'trades', ['symbol', 'trading_mode'])
    
    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.Enum('long', 'short', name='positionside'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('entry_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('current_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('unrealized_pnl', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(10, 2), server_default='0'),
        sa.Column('trading_mode', sa.Enum('paper', 'live', name='tradingmode'), nullable=False),
        sa.Column('stop_loss', sa.Numeric(10, 2), nullable=True),
        sa.Column('take_profit', sa.Numeric(10, 2), nullable=True),
        sa.Column('trailing_stop_config', postgresql.JSON(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('closed_at', sa.DateTime(), nullable=True)
    )
    
    # Create indexes for positions
    op.create_index('idx_positions_account', 'positions', ['account_id', 'closed_at'])
    op.create_index('idx_positions_symbol', 'positions', ['symbol', 'trading_mode'])
    op.create_index('idx_positions_strategy', 'positions', ['strategy_id'])


def downgrade():
    # Drop positions table and indexes
    op.drop_index('idx_positions_strategy', 'positions')
    op.drop_index('idx_positions_symbol', 'positions')
    op.drop_index('idx_positions_account', 'positions')
    op.drop_table('positions')
    
    # Drop trades table and indexes
    op.drop_index('idx_trades_symbol', 'trades')
    op.drop_index('idx_trades_order', 'trades')
    op.drop_index('idx_trades_account', 'trades')
    op.drop_constraint('fk_trades_order', 'trades', type_='foreignkey')
    op.drop_table('trades')
    
    # Drop orders table and indexes
    op.drop_index('idx_orders_broker', 'orders')
    op.drop_index('idx_orders_status', 'orders')
    op.drop_index('idx_orders_account', 'orders')
    op.drop_table('orders')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS positionside')
    op.execute('DROP TYPE IF EXISTS orderstatus')
    op.execute('DROP TYPE IF EXISTS tradingmode')
    op.execute('DROP TYPE IF EXISTS orderside')
