"""
Export Test Scenario

Exports database state and configuration for sharing test scenarios.
"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.connection import get_db_session
from shared.models.user import User, UserAccount, AccountAccess
from shared.models.order import Order, Trade
from shared.models.position import Position
from shared.models.risk_management import RiskLimits, StrategyLimits
from sqlalchemy.orm import Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_users(session: Session) -> Dict[str, Any]:
    """Export user data"""
    users = session.query(User).all()
    accounts = session.query(UserAccount).all()
    access = session.query(AccountAccess).all()
    
    return {
        'users': [
            {
                'id': u.id,
                'email': u.email,
                'role': u.role,
                'account_id': u.account_id,
                'is_locked': u.is_locked
            }
            for u in users
        ],
        'accounts': [
            {
                'id': a.id,
                'trader_id': a.trader_id,
                'name': a.name,
                'is_active': a.is_active
            }
            for a in accounts
        ],
        'access': [
            {
                'account_id': a.account_id,
                'user_id': a.user_id,
                'role': a.role
            }
            for a in access
        ]
    }


def export_orders_and_positions(session: Session) -> Dict[str, Any]:
    """Export orders and positions"""
    orders = session.query(Order).all()
    trades = session.query(Trade).all()
    positions = session.query(Position).all()
    
    return {
        'orders': [
            {
                'id': o.id,
                'account_id': o.account_id,
                'symbol': o.symbol,
                'side': o.side,
                'quantity': o.quantity,
                'order_type': o.order_type,
                'price': o.price,
                'status': o.status,
                'trading_mode': o.trading_mode
            }
            for o in orders
        ],
        'trades': [
            {
                'id': t.id,
                'order_id': t.order_id,
                'account_id': t.account_id,
                'symbol': t.symbol,
                'side': t.side,
                'quantity': t.quantity,
                'price': t.price,
                'commission': t.commission,
                'trading_mode': t.trading_mode
            }
            for t in trades
        ],
        'positions': [
            {
                'id': p.id,
                'account_id': p.account_id,
                'symbol': p.symbol,
                'side': p.side,
                'quantity': p.quantity,
                'entry_price': p.entry_price,
                'current_price': p.current_price,
                'unrealized_pnl': p.unrealized_pnl,
                'realized_pnl': p.realized_pnl,
                'trading_mode': p.trading_mode
            }
            for p in positions
        ]
    }


def export_risk_config(session: Session) -> Dict[str, Any]:
    """Export risk management configuration"""
    risk_limits = session.query(RiskLimits).all()
    strategy_limits = session.query(StrategyLimits).all()
    
    return {
        'risk_limits': [
            {
                'account_id': r.account_id,
                'trading_mode': r.trading_mode,
                'max_loss_limit': r.max_loss_limit,
                'current_loss': r.current_loss,
                'is_breached': r.is_breached
            }
            for r in risk_limits
        ],
        'strategy_limits': [
            {
                'trading_mode': s.trading_mode,
                'max_concurrent_strategies': s.max_concurrent_strategies,
                'current_active_count': s.current_active_count
            }
            for s in strategy_limits
        ]
    }


def export_scenario(output_file: str):
    """Export complete test scenario"""
    logger.info(f"Exporting test scenario to {output_file}...")
    
    try:
        session = get_db_session()
        
        scenario = {
            'exported_at': datetime.now().isoformat(),
            'version': '1.0',
            'users': export_users(session),
            'trading': export_orders_and_positions(session),
            'risk_config': export_risk_config(session)
        }
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(scenario, f, indent=2)
        
        logger.info(f"Scenario exported successfully to {output_file}")
        
    except Exception as e:
        logger.error(f"Error exporting scenario: {e}", exc_info=True)
        sys.exit(1)
    finally:
        session.close()


def main():
    """Main export function"""
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'test_scenario.json'
    export_scenario(output_file)


if __name__ == "__main__":
    main()
