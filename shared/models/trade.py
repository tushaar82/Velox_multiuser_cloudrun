"""Trade data models for trade execution tracking."""

from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from shared.database.connection import Base
from shared.models.order import OrderSide, TradingMode


class Trade(Base):
    """SQLAlchemy model for trades table."""
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    symbol = Column(String(50), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    commission = Column(Numeric(10, 2), nullable=False, default=0)
    trading_mode = Column(SQLEnum(TradingMode), nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_trades_account', 'account_id', 'executed_at'),
        Index('idx_trades_order', 'order_id'),
        Index('idx_trades_symbol', 'symbol', 'trading_mode'),
    )


@dataclass
class TradeData:
    """Data class for trade information."""
    id: str
    order_id: str
    account_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float
    trading_mode: TradingMode
    executed_at: datetime

    @classmethod
    def from_orm(cls, trade: Trade) -> 'TradeData':
        """Create TradeData from SQLAlchemy Trade model."""
        return cls(
            id=str(trade.id),
            order_id=str(trade.order_id),
            account_id=str(trade.account_id),
            symbol=trade.symbol,
            side=trade.side,
            quantity=trade.quantity,
            price=float(trade.price),
            commission=float(trade.commission),
            trading_mode=trade.trading_mode,
            executed_at=trade.executed_at
        )
