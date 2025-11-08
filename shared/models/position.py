"""Position data models for position tracking."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Index, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from shared.database.connection import Base
from shared.models.order import TradingMode
from enum import Enum


class PositionSide(str, Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"


class Position(Base):
    """SQLAlchemy model for positions table."""
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), nullable=True)
    symbol = Column(String(50), nullable=False)
    side = Column(SQLEnum(PositionSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Numeric(10, 2), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=False)
    unrealized_pnl = Column(Numeric(10, 2), nullable=False, default=0)
    realized_pnl = Column(Numeric(10, 2), default=0)
    trading_mode = Column(SQLEnum(TradingMode), nullable=False)
    stop_loss = Column(Numeric(10, 2), nullable=True)
    take_profit = Column(Numeric(10, 2), nullable=True)
    trailing_stop_config = Column(JSON, nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_positions_account', 'account_id', 'closed_at'),
        Index('idx_positions_symbol', 'symbol', 'trading_mode'),
        Index('idx_positions_strategy', 'strategy_id'),
    )


@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop-loss."""
    enabled: bool
    percentage: float
    current_stop_price: float
    highest_price: float  # for long positions
    lowest_price: float   # for short positions


@dataclass
class PositionData:
    """Data class for position information."""
    id: str
    account_id: str
    strategy_id: Optional[str]
    symbol: str
    side: PositionSide
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    trading_mode: TradingMode
    stop_loss: Optional[float]
    take_profit: Optional[float]
    trailing_stop_loss: Optional[TrailingStopConfig]
    opened_at: datetime
    closed_at: Optional[datetime]

    @classmethod
    def from_orm(cls, position: Position) -> 'PositionData':
        """Create PositionData from SQLAlchemy Position model."""
        trailing_stop = None
        if position.trailing_stop_config:
            trailing_stop = TrailingStopConfig(**position.trailing_stop_config)
        
        return cls(
            id=str(position.id),
            account_id=str(position.account_id),
            strategy_id=str(position.strategy_id) if position.strategy_id else None,
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=float(position.entry_price),
            current_price=float(position.current_price),
            unrealized_pnl=float(position.unrealized_pnl),
            realized_pnl=float(position.realized_pnl),
            trading_mode=position.trading_mode,
            stop_loss=float(position.stop_loss) if position.stop_loss else None,
            take_profit=float(position.take_profit) if position.take_profit else None,
            trailing_stop_loss=trailing_stop,
            opened_at=position.opened_at,
            closed_at=position.closed_at
        )
