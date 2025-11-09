"""create notifications table

Revision ID: 007
Revises: 006
Create Date: 2024-01-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notification_type enum
    notification_type_enum = postgresql.ENUM(
        'order_executed',
        'strategy_error',
        'threshold_alert',
        'connection_lost',
        'system_alert',
        'trailing_stop_triggered',
        'investor_invitation',
        'account_access_granted',
        'session_timeout_warning',
        'account_locked',
        'loss_limit_breached',
        'strategy_paused',
        name='notification_type',
        create_type=True
    )
    notification_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create notification_severity enum
    notification_severity_enum = postgresql.ENUM(
        'info',
        'warning',
        'error',
        'critical',
        name='notification_severity',
        create_type=True
    )
    notification_severity_enum.create(op.get_bind(), checkfirst=True)
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', notification_type_enum, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', notification_severity_enum, nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Create indexes
    op.create_index(
        'idx_notifications_user',
        'notifications',
        ['user_id', 'created_at'],
        postgresql_using='btree'
    )
    
    op.create_index(
        'idx_notifications_unread',
        'notifications',
        ['user_id', 'read_at'],
        postgresql_using='btree'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_notifications_unread', table_name='notifications')
    op.drop_index('idx_notifications_user', table_name='notifications')
    
    # Drop table
    op.drop_table('notifications')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS notification_severity')
    op.execute('DROP TYPE IF EXISTS notification_type')
