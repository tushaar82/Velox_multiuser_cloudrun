"""
Seed Data Script

Creates test users, strategies, and sample data for development and testing.
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.connection import get_db_session
from shared.models.user import User, UserAccount, AccountAccess, InvestorInvitation
from shared.models.broker_connection import BrokerConnection
from shared.models.risk_management import RiskLimits, StrategyLimits
from shared.utils.password import hash_password
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_users(session: Session):
    """Create test users with different roles"""
    logger.info("Creating test users...")
    
    # Admin user
    admin = User(
        id="admin-001",
        email="admin@tradingplatform.com",
        password_hash=hash_password("Admin@123"),
        role="admin",
        account_id=None,
        created_at=datetime.now(),
        is_locked=False,
        failed_login_attempts=0
    )
    session.add(admin)
    
    # Trader 1
    trader1_account = UserAccount(
        id="account-001",
        trader_id="trader-001",
        name="Trader 1 Account",
        created_at=datetime.now(),
        is_active=True
    )
    session.add(trader1_account)
    
    trader1 = User(
        id="trader-001",
        email="trader1@example.com",
        password_hash=hash_password("Trader@123"),
        role="trader",
        account_id="account-001",
        created_at=datetime.now(),
        is_locked=False,
        failed_login_attempts=0
    )
    session.add(trader1)
    
    trader1_access = AccountAccess(
        account_id="account-001",
        user_id="trader-001",
        role="trader",
        granted_at=datetime.now()
    )
    session.add(trader1_access)
    
    # Trader 2
    trader2_account = UserAccount(
        id="account-002",
        trader_id="trader-002",
        name="Trader 2 Account",
        created_at=datetime.now(),
        is_active=True
    )
    session.add(trader2_account)
    
    trader2 = User(
        id="trader-002",
        email="trader2@example.com",
        password_hash=hash_password("Trader@123"),
        role="trader",
        account_id="account-002",
        created_at=datetime.now(),
        is_locked=False,
        failed_login_attempts=0
    )
    session.add(trader2)
    
    trader2_access = AccountAccess(
        account_id="account-002",
        user_id="trader-002",
        role="trader",
        granted_at=datetime.now()
    )
    session.add(trader2_access)
    
    # Investor 1 (has access to trader1's account)
    investor1 = User(
        id="investor-001",
        email="investor1@example.com",
        password_hash=hash_password("Investor@123"),
        role="investor",
        account_id=None,
        created_at=datetime.now(),
        is_locked=False,
        failed_login_attempts=0
    )
    session.add(investor1)
    
    investor1_access = AccountAccess(
        account_id="account-001",
        user_id="investor-001",
        role="investor",
        granted_at=datetime.now()
    )
    session.add(investor1_access)
    
    # Investor 2 (has access to both accounts)
    investor2 = User(
        id="investor-002",
        email="investor2@example.com",
        password_hash=hash_password("Investor@123"),
        role="investor",
        account_id=None,
        created_at=datetime.now(),
        is_locked=False,
        failed_login_attempts=0
    )
    session.add(investor2)
    
    investor2_access1 = AccountAccess(
        account_id="account-001",
        user_id="investor-002",
        role="investor",
        granted_at=datetime.now()
    )
    session.add(investor2_access1)
    
    investor2_access2 = AccountAccess(
        account_id="account-002",
        user_id="investor-002",
        role="investor",
        granted_at=datetime.now()
    )
    session.add(investor2_access2)
    
    # Pending invitation
    invitation = InvestorInvitation(
        id="invite-001",
        account_id="account-002",
        inviter_id="trader-002",
        invitee_email="investor3@example.com",
        status="pending",
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=7)
    )
    session.add(invitation)
    
    session.commit()
    logger.info("Test users created successfully")


def create_risk_limits(session: Session):
    """Create default risk limits"""
    logger.info("Creating risk limits...")
    
    # Risk limits for account 1
    risk_limits_paper_1 = RiskLimits(
        account_id="account-001",
        trading_mode="paper",
        max_loss_limit=50000.0,
        current_loss=0.0,
        is_breached=False,
        breached_at=None,
        acknowledged=False
    )
    session.add(risk_limits_paper_1)
    
    risk_limits_live_1 = RiskLimits(
        account_id="account-001",
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
        account_id="account-002",
        trading_mode="paper",
        max_loss_limit=100000.0,
        current_loss=0.0,
        is_breached=False,
        breached_at=None,
        acknowledged=False
    )
    session.add(risk_limits_paper_2)
    
    risk_limits_live_2 = RiskLimits(
        account_id="account-002",
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
    
    # Paper trading limit
    paper_limit = StrategyLimits(
        trading_mode="paper",
        max_concurrent_strategies=10,
        current_active_count=0,
        last_updated=datetime.now(),
        updated_by="admin-001"
    )
    session.add(paper_limit)
    
    # Live trading limit
    live_limit = StrategyLimits(
        trading_mode="live",
        max_concurrent_strategies=5,
        current_active_count=0,
        last_updated=datetime.now(),
        updated_by="admin-001"
    )
    session.add(live_limit)
    
    session.commit()
    logger.info("Strategy limits created successfully")


def create_mock_broker_connections(session: Session):
    """Create mock broker connections for testing"""
    logger.info("Creating mock broker connections...")
    
    # Mock broker for trader 1
    broker1 = BrokerConnection(
        id="broker-001",
        account_id="account-001",
        broker_name="Mock Broker",
        encrypted_credentials="mock_encrypted_credentials",
        is_connected=True,
        last_connected_at=datetime.now(),
        created_at=datetime.now()
    )
    session.add(broker1)
    
    # Mock broker for trader 2
    broker2 = BrokerConnection(
        id="broker-002",
        account_id="account-002",
        broker_name="Mock Broker",
        encrypted_credentials="mock_encrypted_credentials",
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
        session = get_db_session()
        
        # Create test data
        create_test_users(session)
        create_risk_limits(session)
        create_strategy_limits(session)
        create_mock_broker_connections(session)
        
        logger.info("Seed data script completed successfully!")
        
    except Exception as e:
        logger.error(f"Error seeding data: {e}", exc_info=True)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
