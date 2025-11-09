"""
Seed Data Script

Creates test users, strategies, and sample data for development and testing.
"""
import sys
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.connection import get_db_session, init_database
from shared.models.user import User, UserAccount, AccountAccess, InvestorInvitation, UserRole, InvitationStatus
from shared.models.broker_connection import BrokerConnection
from shared.models.risk_management import RiskLimits, StrategyLimits
from shared.utils.password import hash_password
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pre-defined UUIDs for consistent test data
ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TRADER1_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
TRADER2_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
INVESTOR1_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")
INVESTOR2_ID = uuid.UUID("00000000-0000-0000-0000-000000000005")
ACCOUNT1_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
ACCOUNT2_ID = uuid.UUID("00000000-0000-0000-0000-000000000102")
BROKER1_ID = uuid.UUID("00000000-0000-0000-0000-000000000201")
BROKER2_ID = uuid.UUID("00000000-0000-0000-0000-000000000202")
INVITATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000301")


def create_test_users(session: Session):
    """Create test users with different roles"""
    logger.info("Creating test users...")
    
    try:
        # Admin user
        admin = User(
            id=ADMIN_ID,
            email="admin@tradingplatform.com",
            password_hash=hash_password("Admin@123"),
            role=UserRole.ADMIN,
            created_at=datetime.now(),
            is_locked=False,
            failed_login_attempts=0
        )
        session.add(admin)
        
        # Trader 1
        trader1_account = UserAccount(
            id=ACCOUNT1_ID,
            trader_id=TRADER1_ID,
            name="Trader 1 Account",
            created_at=datetime.now(),
            is_active=True
        )
        session.add(trader1_account)
        
        trader1 = User(
            id=TRADER1_ID,
            email="trader1@example.com",
            password_hash=hash_password("Trader@123"),
            role=UserRole.TRADER,
            created_at=datetime.now(),
            is_locked=False,
            failed_login_attempts=0
        )
        session.add(trader1)
        
        trader1_access = AccountAccess(
            account_id=ACCOUNT1_ID,
            user_id=TRADER1_ID,
            role="trader",
            granted_at=datetime.now()
        )
        session.add(trader1_access)
        
        # Trader 2
        trader2_account = UserAccount(
            id=ACCOUNT2_ID,
            trader_id=TRADER2_ID,
            name="Trader 2 Account",
            created_at=datetime.now(),
            is_active=True
        )
        session.add(trader2_account)
        
        trader2 = User(
            id=TRADER2_ID,
            email="trader2@example.com",
            password_hash=hash_password("Trader@123"),
            role=UserRole.TRADER,
            created_at=datetime.now(),
            is_locked=False,
            failed_login_attempts=0
        )
        session.add(trader2)
        
        trader2_access = AccountAccess(
            account_id=ACCOUNT2_ID,
            user_id=TRADER2_ID,
            role="trader",
            granted_at=datetime.now()
        )
        session.add(trader2_access)
        
        # Investor 1 (has access to trader1's account)
        investor1 = User(
            id=INVESTOR1_ID,
            email="investor1@example.com",
            password_hash=hash_password("Investor@123"),
            role=UserRole.INVESTOR,
            created_at=datetime.now(),
            is_locked=False,
            failed_login_attempts=0
        )
        session.add(investor1)
        
        investor1_access = AccountAccess(
            account_id=ACCOUNT1_ID,
            user_id=INVESTOR1_ID,
            role="investor",
            granted_at=datetime.now()
        )
        session.add(investor1_access)
        
        # Investor 2 (has access to both accounts)
        investor2 = User(
            id=INVESTOR2_ID,
            email="investor2@example.com",
            password_hash=hash_password("Investor@123"),
            role=UserRole.INVESTOR,
            created_at=datetime.now(),
            is_locked=False,
            failed_login_attempts=0
        )
        session.add(investor2)
        
        investor2_access1 = AccountAccess(
            account_id=ACCOUNT1_ID,
            user_id=INVESTOR2_ID,
            role="investor",
            granted_at=datetime.now()
        )
        session.add(investor2_access1)
        
        investor2_access2 = AccountAccess(
            account_id=ACCOUNT2_ID,
            user_id=INVESTOR2_ID,
            role="investor",
            granted_at=datetime.now()
        )
        session.add(investor2_access2)
        
        # Pending invitation
        invitation = InvestorInvitation(
            id=INVITATION_ID,
            account_id=ACCOUNT2_ID,
            inviter_id=TRADER2_ID,
            invitee_email="investor3@example.com",
            status=InvitationStatus.PENDING,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7)
        )
        session.add(invitation)
        
        session.commit()
        logger.info("Test users created successfully")
    except IntegrityError as e:
        session.rollback()
        logger.info("Test users already exist, skipping creation...")
    except Exception as e:
        session.rollback()
        raise


def create_risk_limits(session: Session):
    """Create default risk limits"""
    logger.info("Creating risk limits...")
    
    # Check if risk limits already exist
    existing_limit = session.query(RiskLimits).filter_by(account_id=ACCOUNT1_ID, trading_mode="paper").first()
    if existing_limit:
        logger.info("Risk limits already exist, skipping creation...")
        return
    
    # Risk limits for account 1
    risk_limits_paper_1 = RiskLimits(
        account_id=ACCOUNT1_ID,
        trading_mode="paper",
        max_loss_limit=50000.0,
        current_loss=0.0,
        is_breached=False,
        breached_at=None,
        acknowledged=False
    )
    session.add(risk_limits_paper_1)
    
    risk_limits_live_1 = RiskLimits(
        account_id=ACCOUNT1_ID,
        trading_mode="live",
        max_loss_limit=25000.0,
        current_loss=0.0,
        is_breached=False,
        breached_at=None,
        acknowledged=False
    )
    session.add(risk_limits_live_1)
    
    # Risk limits for account 2
    risk_limits_paper_2 = RiskLimits(
        account_id=ACCOUNT2_ID,
        trading_mode="paper",
        max_loss_limit=100000.0,
        current_loss=0.0,
        is_breached=False,
        breached_at=None,
        acknowledged=False
    )
    session.add(risk_limits_paper_2)
    
    risk_limits_live_2 = RiskLimits(
        account_id=ACCOUNT2_ID,
        trading_mode="live",
        max_loss_limit=50000.0,
        current_loss=0.0,
        is_breached=False,
        breached_at=None,
        acknowledged=False
    )
    session.add(risk_limits_live_2)
    
    session.commit()
    logger.info("Risk limits created successfully")


def create_strategy_limits(session: Session):
    """Create global strategy limits"""
    logger.info("Creating strategy limits...")
    
    # Check if strategy limits already exist
    existing_limit = session.query(StrategyLimits).filter_by(trading_mode="paper").first()
    if existing_limit:
        logger.info("Strategy limits already exist, skipping creation...")
        return
    
    # Paper trading limit
    paper_limit = StrategyLimits(
        trading_mode="paper",
        max_concurrent_strategies=10,
        last_updated=datetime.now(),
        updated_by=ADMIN_ID
    )
    session.add(paper_limit)
    
    # Live trading limit
    live_limit = StrategyLimits(
        trading_mode="live",
        max_concurrent_strategies=5,
        last_updated=datetime.now(),
        updated_by=ADMIN_ID
    )
    session.add(live_limit)
    
    session.commit()
    logger.info("Strategy limits created successfully")


def create_mock_broker_connections(session: Session):
    """Create mock broker connections for testing"""
    logger.info("Creating mock broker connections...")
    
    # Check if broker connections already exist
    existing_broker = session.query(BrokerConnection).filter_by(id=BROKER1_ID).first()
    if existing_broker:
        logger.info("Mock broker connections already exist, skipping creation...")
        return
    
    # Mock broker for trader 1
    broker1 = BrokerConnection(
        id=BROKER1_ID,
        account_id=ACCOUNT1_ID,
        broker_name="Mock Broker",
        credentials_encrypted="mock_encrypted_credentials",
        is_connected=True,
        last_connected_at=datetime.now(),
        created_at=datetime.now()
    )
    session.add(broker1)
    
    # Mock broker for trader 2
    broker2 = BrokerConnection(
        id=BROKER2_ID,
        account_id=ACCOUNT2_ID,
        broker_name="Mock Broker",
        credentials_encrypted="mock_encrypted_credentials",
        is_connected=True,
        last_connected_at=datetime.now(),
        created_at=datetime.now()
    )
    session.add(broker2)
    
    session.commit()
    logger.info("Mock broker connections created successfully")


def main():
    """Main seed data function"""
    logger.info("Starting seed data script...")
    
    try:
        # Initialize database connection
        init_database()
        
        with get_db_session() as session:
            # Create test data
            create_test_users(session)
            create_risk_limits(session)
            create_strategy_limits(session)
            create_mock_broker_connections(session)
            
            logger.info("Seed data script completed successfully!")
        
    except Exception as e:
        logger.error(f"Error seeding data: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
