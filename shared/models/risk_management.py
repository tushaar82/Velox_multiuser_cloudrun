"""
Risk management data models.
Implements RiskLimits and StrategyLimits tables for loss tracking and concurrent strategy limits.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, 
    CheckConstraint, ForeignKey, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.database.connection import Base


class RiskLimits(Base):
    """Risk limits model for tracking maximum loss limits per account and trading mode."""
    
    __tablename__ = "risk_limits"
    
    account_id = Column(UUID(as_uuid=True), ForeignKey("user_accounts.id"), primary_key=True)
    trading_mode = Column(String(10), primary_key=True)
    max_loss_limit = Column(DECIMAL(15, 2), nullable=False)
    current_loss = Column(DECIMAL(15, 2), default=Decimal('0.00'), nullable=False)
    is_breached = Column(Boolean, default=False, nullable=False)
    breached_at = Column(DateTime, nullable=True)
    acknowledged = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # account = relationship("UserAccount", back_populates="risk_limits")
    
    __table_args__ = (
        CheckConstraint(
            "trading_mode IN ('paper', 'live')",
            name="check_risk_limits_trading_mode"
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<RiskLimits(account_id={self.account_id}, trading_mode={self.trading_mode}, "
            f"max_loss_limit={self.max_loss_limit}, current_loss={self.current_loss}, "
            f"is_breached={self.is_breached})>"
        )


class StrategyLimits(Base):
    """Strategy limits model for managing concurrent strategy execution limits."""
    
    __tablename__ = "strategy_limits"
    
    trading_mode = Column(String(10), primary_key=True)
    max_concurrent_strategies = Column(Integer, nullable=False, default=5)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    # updated_by_user = relationship("User")
    
    __table_args__ = (
        CheckConstraint(
            "trading_mode IN ('paper', 'live')",
            name="check_strategy_limits_trading_mode"
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<StrategyLimits(trading_mode={self.trading_mode}, "
            f"max_concurrent_strategies={self.max_concurrent_strategies})>"
        )
