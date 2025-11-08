"""create user authentication tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user authentication and management tables."""
    
    # Create user_role enum (skip if already exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('admin', 'trader', 'investor');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create invitation_status enum (skip if already exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'rejected', 'expired');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'trader', 'investor', name='user_role', create_type=False), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'))
    )
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Create user_accounts table
    op.create_table(
        'user_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trader_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['trader_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create account_access table
    op.create_table(
        'account_access',
        sa.Column('account_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['account_id'], ['user_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("role IN ('trader', 'investor')", name='check_account_access_role')
    )
    
    # Create investor_invitations table
    op.create_table(
        'investor_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('inviter_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invitee_email', sa.String(255), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'accepted', 'rejected', 'expired', name='invitation_status', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['user_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_invitations_email', 'investor_invitations', ['invitee_email', 'status'])
    
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('token', sa.String(512), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_sessions_user', 'sessions', ['user_id', 'last_activity'])
    op.create_index('idx_sessions_expiry', 'sessions', ['expires_at'])


def downgrade() -> None:
    """Drop user authentication and management tables."""
    
    # Drop tables in reverse order
    op.drop_index('idx_sessions_expiry', table_name='sessions')
    op.drop_index('idx_sessions_user', table_name='sessions')
    op.drop_table('sessions')
    
    op.drop_index('idx_invitations_email', table_name='investor_invitations')
    op.drop_table('investor_invitations')
    
    op.drop_table('account_access')
    op.drop_table('user_accounts')
    
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE invitation_status')
    op.execute('DROP TYPE user_role')
