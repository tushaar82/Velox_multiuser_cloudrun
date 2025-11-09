"""
Import Test Scenario

Imports database state and configuration from exported test scenarios.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.connection import get_db_session
from shared.models.user import User, UserAccount, AccountAccess
from shared.models.order import Order, Trade
from shared.models.position import Position
from shared.models.risk_management import RiskLimits, StrategyLimits
from shared.utils.password import hash_password
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_users(session: Session, data: dict):
    """Import user data"""
    logger.info("Importing users...")
    
    # Import accounts
    for account_data in data.get('accounts', []):
        account = UserAccount(
            id=account_data['id'],
            trader_id=account_data['trader_id'],
            name=account_data['name'],
            created_at=datetime.now(),
            is_active=account_data['is_active']
        )
        session.merge(account)
    
    # Import users
    for user_data in data.get('users', []):
        user = User(
            id=user_data['id'],
            email=user_data['email'],
            password_hash=hash_password("Test@123"),  # Default password
            role=user_data['role'],
            account_id=user_data.get('account_id'),
            created_at=datetime.now(),
            is_locked=user_data.get('is_locked', False),
            failed_login_attempts=0
        )
        session.merge(user)
    
    # Import access
    for access_data in data.get('access', []):
        access = AccountAccess(
            account_id=access_data['account_id'],
            user_id=access_data['user_id'],
            role=access_data['role'],
            granted_at=datetime.now()
        )
        session.merge(access)
    
    session.commit()
    logger.info("Users imported successfully")


def import_trading_data(session: Session, data: dict):
    """Import orders and positions"""
    logger.info("Importing trading data...")
    
    # Import orders
    for order_data in data.get('orders', []):
        order = Order(
            id=order_data['id'],
            account_id=order_data['account_id'],
            strategy_id=None,
            symbol=order_data['symbol'],
            side=order_data['side'],
            quantity=order_data['quantity'],
            order_type=order_data['order_type'],
            price=order_data.get('price'),
            stop_price=None,
            trading_mode=order_data['trading_mode'],
            status=order_data['status'],
            filled_quantity=order_data['quantity'],
            average_price=order_data.get('price', 0),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.merge(order)
    
    # Import trades
    for trade_data in data.get('trades', []):
        trade = Trade(
            id=trade_data['id'],
            order_id=trade_data['order_id'],
            account_id=trade_data['account_id'],
            symbol=trade_data['symbol'],
            side=trade_data['side'],
            quantity=trade_data['quantity'],
            price=trade_data['price'],
            commission=trade_data['commission'],
            trading_mode=trade_data['trading_mode'],
            executed_at=datetime.now()
        )
        session.merge(trade)
    
    # Import positions
    for position_data in data.get('positions', []):
        position = Position(
            id=position_data['id'],
            account_id=position_data['account_id'],
            strategy_id=None,
            symbol=position_data['symbol'],
            side=position_data['side'],
            quantity=position_data['quantity'],
            entry_price=position_data['entry_price'],
            current_price=position_data['current_price'],
            unrealized_pnl=position_data['unrealized_pnl'],
            realized_pnl=position_data['realized_pnl'],
            trading_mode=position_data['trading_mode'],
            stop_loss=None,
            take_profit=None,
            trailing_stop_loss=None,
            opened_at=datetime.now(),
            closed_at=None
        )
        session.merge(position)
    
    session.commit()
    logger.info("Trading data imported successfully")


def import_risk_config(session: Session, data: dict):
    """Import risk management configuration"""
    logger.info("Importing risk configuration...")
    
    # Import risk limits
    for risk_data in data.get('risk_limits', []):
        risk_limit = RiskLimits(
            account_id=risk_data['account_id'],
            trading_mode=risk_data['trading_mode'],
            max_loss_limit=risk_data['max_loss_limit'],
            current_loss=risk_data['current_loss'],
            is_breached=risk_data['is_breached'],
            breached_at=None,
            acknowledged=False
        )
        session.merge(risk_limit)
    
    # Import strategy limits
    for strategy_data in data.get('strategy_limits', []):
        strategy_limit = StrategyLimits(
            trading_mode=strategy_data['trading_mode'],
            max_concurrent_strategies=strategy_data['max_concurrent_strategies'],
            current_active_count=strategy_data['current_active_count'],
            last_updated=datetime.now(),
            updated_by='admin-001'
        )
        session.merge(strategy_limit)
    
    session.commit()
    logger.info("Risk configuration imported successfully")


def import_scenario(input_file: str):
    """Import complete test scenario"""
    logger.info(f"Importing test scenario from {input_file}...")
    
    try:
        # Read scenario file
        with open(input_file, 'r') as f:
            scenario = json.load(f)
        
        logger.info(f"Scenario version: {scenario.get('version')}")
        logger.info(f"Exported at: {scenario.get('exported_at')}")
        
        session = get_db_session()
        
        # Import data
        import_users(session, scenario.get('users', {}))
        import_trading_data(session, scenario.get('trading', {}))
        import_risk_config(session, scenario.get('risk_config', {}))
        
        logger.info(f"Scenario imported successfully from {input_file}")
        
    except Exception as e:
        logger.error(f"Error importing scenario: {e}", exc_info=True)
        sys.exit(1)
    finally:
        session.close()


def main():
    """Main import function"""
    if len(sys.argv) < 2:
        print("Usage: python import_test_scenario.py <scenario_file.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if not Path(input_file).exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    import_scenario(input_file)


if __name__ == "__main__":
    main()
