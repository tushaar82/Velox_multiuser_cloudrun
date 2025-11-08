"""Order router for routing orders to brokers or paper trading simulator."""

from typing import Optional, Dict, List
from datetime import datetime, timedelta
import uuid
from sqlalchemy.orm import Session
from shared.models.order import Order, OrderData, OrderStatus, OrderSide, TradingMode
from shared.models.trade import Trade, TradeData
from shared.models.broker_connection import BrokerConnection
from shared.brokers.base import IBrokerConnector, BrokerOrder, BrokerOrderResponse
from shared.services.symbol_mapping_service import SymbolMappingService
from shared.utils.logging_config import get_logger
from order_processor.paper_trading_simulator import PaperTradingSimulator

logger = get_logger(__name__)


class OrderValidationError(Exception):
    """Exception raised when order validation fails."""
    pass


class OrderRouter:
    """Routes orders to appropriate execution venue (broker or paper trading)."""
    
    def __init__(
        self,
        db_session: Session,
        symbol_mapping_service: SymbolMappingService,
        broker_connectors: Dict[str, IBrokerConnector],
        paper_trading_simulator: PaperTradingSimulator
    ):
        """
        Initialize order router.
        
        Args:
            db_session: Database session
            symbol_mapping_service: Symbol mapping service for translation
            broker_connectors: Dictionary of broker name to connector instances
            paper_trading_simulator: Paper trading simulator
        """
        self.db = db_session
        self.symbol_mapping = symbol_mapping_service
        self.broker_connectors = broker_connectors
        self.paper_simulator = paper_trading_simulator
        self.pending_orders: Dict[str, datetime] = {}  # order_id -> submission_time
        
        logger.info("Order router initialized")
    
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
            side: Order side (buy/sell)
            quantity: Order quantity
            order_type: Order type (market/limit/stop/stop_limit)
            trading_mode: Trading mode (paper/live)
            strategy_id: Optional strategy ID
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            current_market_price: Current market price (for paper trading)
            
        Returns:
            Created order data
            
        Raises:
            OrderValidationError: If order validation fails
        """
        # Validate order
        self._validate_order(symbol, side, quantity, order_type, price, stop_price)
        
        # Create order record
        order = Order(
            id=uuid.uuid4(),
            account_id=uuid.UUID(account_id),
            strategy_id=uuid.UUID(strategy_id) if strategy_id else None,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            trading_mode=trading_mode,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            created_at=datetime.utcnow()
        )
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        order_data = OrderData.from_orm(order)
        
        logger.info(
            f"Created order: {order_data.id} - {symbol} {side.value} {quantity} "
            f"@ {price or 'market'} (mode: {trading_mode.value})"
        )
        
        # Route order based on trading mode
        if trading_mode == TradingMode.PAPER:
            return self._execute_paper_order(order_data, current_market_price)
        else:  # LIVE
            return self._execute_live_order(order_data)
    
    def _validate_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: str,
        price: Optional[float],
        stop_price: Optional[float]
    ) -> None:
        """Validate order parameters."""
        if quantity <= 0:
            raise OrderValidationError("Quantity must be positive")
        
        if order_type in ['limit', 'stop_limit'] and price is None:
            raise OrderValidationError(f"{order_type} order requires price")
        
        if order_type in ['stop', 'stop_limit'] and stop_price is None:
            raise OrderValidationError(f"{order_type} order requires stop_price")
        
        if price is not None and price <= 0:
            raise OrderValidationError("Price must be positive")
        
        if stop_price is not None and stop_price <= 0:
            raise OrderValidationError("Stop price must be positive")
    
    def _execute_paper_order(
        self,
        order: OrderData,
        current_price: Optional[float]
    ) -> OrderData:
        """Execute order in paper trading mode."""
        if current_price is None:
            raise OrderValidationError("Current market price required for paper trading")
        
        # Simulate order execution
        if order.order_type == 'market':
            updated_order, trade = self.paper_simulator.simulate_market_order(order, current_price)
            self._save_paper_trade(updated_order, trade)
            return updated_order
        
        elif order.order_type == 'limit':
            result = self.paper_simulator.simulate_limit_order(order, current_price)
            if result:
                updated_order, trade = result
                self._save_paper_trade(updated_order, trade)
                return updated_order
            else:
                # Order pending
                self._update_order_status(order.id, OrderStatus.SUBMITTED)
                order.status = OrderStatus.SUBMITTED
                return order
        
        elif order.order_type in ['stop', 'stop_limit']:
            result = self.paper_simulator.simulate_stop_order(order, current_price)
            if result:
                updated_order, trade = result
                self._save_paper_trade(updated_order, trade)
                return updated_order
            else:
                # Order pending
                self._update_order_status(order.id, OrderStatus.SUBMITTED)
                order.status = OrderStatus.SUBMITTED
                return order
        
        else:
            raise OrderValidationError(f"Unsupported order type: {order.order_type}")
    
    def _execute_live_order(self, order: OrderData) -> OrderData:
        """Execute order in live trading mode with broker."""
        # Get broker connection for account
        broker_conn = self.db.query(BrokerConnection).filter(
            BrokerConnection.account_id == uuid.UUID(order.account_id),
            BrokerConnection.is_connected == True
        ).first()
        
        if not broker_conn:
            self._update_order_status(order.id, OrderStatus.REJECTED)
            order.status = OrderStatus.REJECTED
            logger.error(f"No active broker connection for account {order.account_id}")
            raise OrderValidationError("No active broker connection")
        
        # Get broker connector
        broker_name = broker_conn.broker_name
        connector = self.broker_connectors.get(broker_name)
        
        if not connector or not connector.is_connected():
            self._update_order_status(order.id, OrderStatus.REJECTED)
            order.status = OrderStatus.REJECTED
            logger.error(f"Broker connector {broker_name} not available or not connected")
            raise OrderValidationError(f"Broker {broker_name} not available")
        
        # Translate symbol to broker-specific token
        broker_token = self.symbol_mapping.get_broker_symbol(broker_name, order.symbol)
        if not broker_token:
            self._update_order_status(order.id, OrderStatus.REJECTED)
            order.status = OrderStatus.REJECTED
            logger.error(f"Symbol mapping not found: {order.symbol} for broker {broker_name}")
            raise OrderValidationError(f"Symbol {order.symbol} not supported by broker {broker_name}")
        
        # Get mapping details for exchange info
        mapping = self.symbol_mapping.get_mapping_details(broker_name, order.symbol)
        exchange = mapping.exchange if mapping else 'NSE'
        
        # Create broker order
        broker_order = BrokerOrder(
            symbol=broker_token,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type,
            price=order.price,
            stop_price=order.stop_price,
            product_type='intraday',
            exchange=exchange
        )
        
        try:
            # Submit order to broker
            response = connector.place_order(broker_order)
            
            # Update order with broker order ID
            self._update_order_broker_id(order.id, response.broker_order_id, OrderStatus.SUBMITTED)
            order.broker_order_id = response.broker_order_id
            order.status = OrderStatus.SUBMITTED
            
            # Track pending order for timeout monitoring
            self.pending_orders[order.id] = datetime.utcnow()
            
            logger.info(
                f"Submitted live order to {broker_name}: {order.id} -> {response.broker_order_id}"
            )
            
            return order
            
        except Exception as e:
            self._update_order_status(order.id, OrderStatus.REJECTED)
            order.status = OrderStatus.REJECTED
            logger.error(f"Failed to submit order to broker: {e}")
            raise OrderValidationError(f"Broker order submission failed: {str(e)}")
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        order = self.db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            logger.warning(f"Cannot cancel order {order_id} with status {order.status}")
            return False
        
        if order.trading_mode == TradingMode.PAPER:
            # Cancel paper order
            self.paper_simulator.cancel_order(order_id)
            self._update_order_status(order_id, OrderStatus.CANCELLED)
            logger.info(f"Cancelled paper order: {order_id}")
            return True
        
        else:  # LIVE
            if not order.broker_order_id:
                logger.error(f"Order {order_id} has no broker order ID")
                return False
            
            # Get broker connection
            broker_conn = self.db.query(BrokerConnection).filter(
                BrokerConnection.account_id == order.account_id,
                BrokerConnection.is_connected == True
            ).first()
            
            if not broker_conn:
                logger.error(f"No active broker connection for order {order_id}")
                return False
            
            connector = self.broker_connectors.get(broker_conn.broker_name)
            if not connector or not connector.is_connected():
                logger.error(f"Broker connector not available for order {order_id}")
                return False
            
            try:
                connector.cancel_order(order.broker_order_id)
                self._update_order_status(order_id, OrderStatus.CANCELLED)
                
                # Remove from pending orders
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]
                
                logger.info(f"Cancelled live order: {order_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to cancel order {order_id}: {e}")
                return False
    
    def check_pending_order_timeouts(self, timeout_seconds: int = 30) -> List[str]:
        """
        Check for pending orders that have exceeded timeout.
        
        Args:
            timeout_seconds: Timeout in seconds (default 30)
            
        Returns:
            List of timed out order IDs
        """
        timed_out = []
        current_time = datetime.utcnow()
        
        for order_id, submission_time in list(self.pending_orders.items()):
            if (current_time - submission_time).total_seconds() > timeout_seconds:
                logger.warning(f"Order {order_id} timed out after {timeout_seconds}s")
                timed_out.append(order_id)
                del self.pending_orders[order_id]
        
        return timed_out
    
    def update_order_from_broker(
        self,
        broker_order_id: str,
        status: str,
        filled_quantity: int = 0,
        average_price: Optional[float] = None
    ) -> Optional[OrderData]:
        """
        Update order status from broker callback.
        
        Args:
            broker_order_id: Broker's order ID
            status: New order status
            filled_quantity: Filled quantity
            average_price: Average fill price
            
        Returns:
            Updated order data or None if not found
        """
        order = self.db.query(Order).filter(
            Order.broker_order_id == broker_order_id
        ).first()
        
        if not order:
            logger.warning(f"Order with broker ID {broker_order_id} not found")
            return None
        
        # Map broker status to our status
        status_mapping = {
            'complete': OrderStatus.FILLED,
            'rejected': OrderStatus.REJECTED,
            'cancelled': OrderStatus.CANCELLED,
            'open': OrderStatus.SUBMITTED,
            'trigger pending': OrderStatus.SUBMITTED
        }
        
        new_status = status_mapping.get(status.lower(), OrderStatus.SUBMITTED)
        
        order.status = new_status
        order.filled_quantity = filled_quantity
        if average_price:
            order.average_price = average_price
        order.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(order)
        
        # Remove from pending if filled or rejected
        if new_status in [OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED]:
            if str(order.id) in self.pending_orders:
                del self.pending_orders[str(order.id)]
        
        logger.info(
            f"Updated order {order.id} from broker: status={new_status}, "
            f"filled={filled_quantity}, price={average_price}"
        )
        
        return OrderData.from_orm(order)
    
    def _save_paper_trade(self, order: OrderData, trade: TradeData) -> None:
        """Save paper trade to database."""
        # Update order in database
        db_order = self.db.query(Order).filter(Order.id == uuid.UUID(order.id)).first()
        if db_order:
            db_order.status = order.status
            db_order.filled_quantity = order.filled_quantity
            db_order.average_price = order.average_price
            db_order.updated_at = order.updated_at
        
        # Save trade
        db_trade = Trade(
            id=uuid.UUID(trade.id),
            order_id=uuid.UUID(trade.order_id),
            account_id=uuid.UUID(trade.account_id),
            symbol=trade.symbol,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            commission=trade.commission,
            trading_mode=trade.trading_mode,
            executed_at=trade.executed_at
        )
        
        self.db.add(db_trade)
        self.db.commit()
        
        logger.info(f"Saved paper trade: {trade.id}")
    
    def _update_order_status(self, order_id: str, status: OrderStatus) -> None:
        """Update order status in database."""
        order = self.db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if order:
            order.status = status
            order.updated_at = datetime.utcnow()
            self.db.commit()
    
    def _update_order_broker_id(
        self,
        order_id: str,
        broker_order_id: str,
        status: OrderStatus
    ) -> None:
        """Update order with broker order ID."""
        order = self.db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if order:
            order.broker_order_id = broker_order_id
            order.status = status
            order.updated_at = datetime.utcnow()
            self.db.commit()
    
    def get_order(self, order_id: str) -> Optional[OrderData]:
        """Get order by ID."""
        order = self.db.query(Order).filter(Order.id == uuid.UUID(order_id)).first()
        if not order:
            return None
        return OrderData.from_orm(order)
    
    def get_orders(
        self,
        account_id: str,
        trading_mode: Optional[TradingMode] = None,
        limit: int = 100
    ) -> List[OrderData]:
        """Get orders for account."""
        query = self.db.query(Order).filter(Order.account_id == uuid.UUID(account_id))
        
        if trading_mode:
            query = query.filter(Order.trading_mode == trading_mode)
        
        orders = query.order_by(Order.created_at.desc()).limit(limit).all()
        
        return [OrderData.from_orm(o) for o in orders]
