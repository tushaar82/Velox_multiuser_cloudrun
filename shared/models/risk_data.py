"""
Risk Management Data Classes

Data classes for risk management operations including loss calculations and strategy counts.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class RiskLimitsData:
    """Data class for risk limits information"""
    account_id: str
    trading_mode: str  # 'paper' or 'live'
    max_loss_limit: Decimal
    current_loss: Decimal
    is_breached: bool
    breached_at: Optional[datetime]
    acknowledged: bool
    updated_at: datetime
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'account_id': str(self.account_id),
            'trading_mode': self.trading_mode,
            'max_loss_limit': float(self.max_loss_limit),
            'current_loss': float(self.current_loss),
            'is_breached': self.is_breached,
            'breached_at': self.breached_at.isoformat() if self.breached_at else None,
            'acknowledged': self.acknowledged,
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class LossCalculation:
    """Data class for loss calculation results"""
    realized_loss: Decimal
    unrealized_loss: Decimal
    total_loss: Decimal
    timestamp: datetime
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'realized_loss': float(self.realized_loss),
            'unrealized_loss': float(self.unrealized_loss),
            'total_loss': float(self.total_loss),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class StrategyLimitsData:
    """Data class for strategy limits information"""
    trading_mode: str  # 'paper' or 'live'
    max_concurrent_strategies: int
    last_updated: datetime
    updated_by: Optional[str]
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'trading_mode': self.trading_mode,
            'max_concurrent_strategies': self.max_concurrent_strategies,
            'last_updated': self.last_updated.isoformat(),
            'updated_by': str(self.updated_by) if self.updated_by else None
        }


@dataclass
class AccountStrategyCount:
    """Data class for tracking active strategy count per account"""
    account_id: str
    trading_mode: str  # 'paper' or 'live'
    active_strategies: int
    paused_strategies: int
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'account_id': str(self.account_id),
            'trading_mode': self.trading_mode,
            'active_strategies': self.active_strategies,
            'paused_strategies': self.paused_strategies
        }
