"""Order data models for order management."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from shared.database.connection import Base


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TradingMode(str, Enum):
    """Trading mode enumeration."""
    PAPER = "paper"
    LIVE = "live"


class Order(Base):
    """SQLAlchemy model for orders table."""
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), nullable=True)
    symbol = Column(String(50), nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    order_type = Column(String(20), nullable=False)
    price = Column(Numeric(10, 2), nullable=True)
    stop_price = Column(Numeric(10, 2), nullable=True)
    trading_mode = Column(SQLEnum(TradingMode), nullable=False)
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    filled_quantity = Column(Integer, default=0)
    average_price = Column(Numeric(10, 2), nullable=True)
    broker_order_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_orders_account', 'account_id', 'created_at'),
        Index('idx_orders_status', 'status', 'trading_mode'),
        Index('idx_orders_broker', 'broker_order_id'),
    )


@dataclass
class OrderData:
    """Data class for order information."""
    id: str
    account_id: str
    strategy_id: Optional[str]
    symbol: str
    side: OrderSide
    quantity: int
    order_type: str
    price: Optional[float]
    stop_price: Optional[float]
    trading_mode: TradingMode
    status: OrderStatus
    filled_quantity: int
    average_price: Optional[float]
    broker_order_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, order: Order) -> 'OrderData':
        """Create OrderData from SQLAlchemy Order model."""
        return cls(
            id=str(order.id),
            account_id=str(order.account_id),
            strategy_id=str(order.strategy_id) if order.strategy_id else None,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type,
            price=float(order.price) if order.price else None,
            stop_price=float(order.stop_price) if order.stop_price else None,
            trading_mode=order.trading_mode,
            status=order.status,
            filled_quantity=order.filled_quantity,
            average_price=float(order.average_price) if order.average_price else None,
            broker_order_id=order.broker_order_id,
            created_at=order.created_at,
            updated_at=order.updated_at
        )
