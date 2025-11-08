"""Order service for business logic."""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from shared.models.order import Order, OrderData, OrderSide, TradingMode, OrderStatus
from shared.models.user import AccountAccess
from shared.services.symbol_mapping_service import SymbolMappingService
from shared.brokers.base import IBrokerConnector
from order_processor.order_router import OrderRouter, OrderValidationError
from order_processor.paper_trading_simulator import PaperTradingSimulator
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class OrderService:
    """Service for order management operations."""
    
    def __init__(
        self,
        db_session: Session,
        order_router: Optional[OrderRouter] = None
    ):
        """
        Initialize order service.
        
        Args:
            db_session: Database session
            order_router: Optional order router (will be created if not provided)
        """
        self.db = db_session
        
        # Initialize order router if not provided
        if order_router is None:
            symbol_mapping = SymbolMappingService(db_session)
            paper_simulator = PaperTradingSimulator()
            broker_connectors = {}  # Will be populated by broker service
            self.order_router = OrderRouter(
                db_session,
                symbol_mapping,
                broker_connectors,
                paper_simulator
            )
        else:
            self.order_router = order_router
    
    def verify_account_access(self, user_id: str, account_id: str) -> bool:
        """
        Verify user has access to account.
        
        Args:
            user_id: User ID
            account_id: Account ID
            
        Returns:
            True if user has access
        """
        access = self.db.query(AccountAccess).filter(
            AccountAccess.user_id == uuid.UUID(user_id),
            AccountAccess.account_id == uuid.UUID(account_id)
        ).first()
        
        return access is not None
    
    def submit_order(
        self,
        account_id: str,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: str,
        trading_mode: TradingMode,
        strategy_id: Optional[str] = None,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        current_market_price: Optional[float] = None
    ) -> OrderData:
        """
        Submit order for execution.
        
        Args:
            account_id: Account ID
            symbol: Standard symbol
            side: Order side
            quantity: Order quantity
            order_type: Order type
            trading_mode: Trading mode
            strategy_id: Optional strategy ID
            price: Optional limit price
            stop_price: Optional stop price
            current_market_price: Current market price (for paper trading)
            
        Returns:
            Created order data
            
        Raises:
            OrderValidationError: If validation fails
        """
        try:
            order = self.order_router.submit_order(
                account_id=account_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                trading_mode=trading_mode,
                strategy_id=strategy_id,
                price=price,
                stop_price=stop_price,
                current_market_price=current_market_price
            )
            
            logger.info(f"Order submitted: {order.id}")
            return order
            
        except OrderValidationError as e:
            logger.error(f"Order validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: Order ID
            
        Returns:
            True if cancelled successfully
        """
        try:
            return self.order_router.cancel_order(order_id)
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[OrderData]:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order data or None if not found
        """
        return self.order_router.get_order(order_id)
    
    def get_orders(
        self,
        account_id: str,
        trading_mode: Optional[TradingMode] = None,
        limit: int = 100
    ) -> List[OrderData]:
        """
        Get orders for account.
        
        Args:
            account_id: Account ID
            trading_mode: Optional trading mode filter
            limit: Maximum number of orders
            
        Returns:
            List of order data
        """
        return self.order_router.get_orders(account_id, trading_mode, limit)
    
    def get_order_history(
        self,
        account_id: str,
        filters: Dict[str, Any]
    ) -> List[OrderData]:
        """
        Get order history with filters.
        
        Args:
            account_id: Account ID
            filters: Dictionary of filters
            
        Returns:
            List of order data
        """
        query = self.db.query(Order).filter(Order.account_id == uuid.UUID(account_id))
        
        # Apply filters
        if filters.get('trading_mode'):
            try:
                trading_mode = TradingMode(filters['trading_mode'])
                query = query.filter(Order.trading_mode == trading_mode)
            except ValueError:
                pass
        
        if filters.get('status'):
            try:
                status = OrderStatus(filters['status'])
                query = query.filter(Order.status == status)
            except ValueError:
                pass
        
        if filters.get('symbol'):
            query = query.filter(Order.symbol == filters['symbol'])
        
        if filters.get('start_date'):
            try:
                start_date = datetime.fromisoformat(filters['start_date'])
                query = query.filter(Order.created_at >= start_date)
            except ValueError:
                pass
        
        if filters.get('end_date'):
            try:
                end_date = datetime.fromisoformat(filters['end_date'])
                query = query.filter(Order.created_at <= end_date)
            except ValueError:
                pass
        
        # Apply limit
        limit = filters.get('limit', 100)
        orders = query.order_by(Order.created_at.desc()).limit(limit).all()
        
        return [OrderData.from_orm(o) for o in orders]
    
    def update_order_from_broker(
        self,
        broker_order_id: str,
        status: str,
        filled_quantity: int = 0,
        average_price: Optional[float] = None
    ) -> Optional[OrderData]:
        """
        Update order from broker callback.
        
        Args:
            broker_order_id: Broker order ID
            status: New status
            filled_quantity: Filled quantity
            average_price: Average fill price
            
        Returns:
            Updated order data or None
        """
        return self.order_router.update_order_from_broker(
            broker_order_id,
            status,
            filled_quantity,
            average_price
        )
