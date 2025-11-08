"""Paper trading simulator for simulating order execution without real broker."""

from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime
import uuid
from shared.models.order import OrderData, OrderStatus, OrderSide, OrderType, TradingMode
from shared.models.trade import TradeData
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class PaperTradingConfig:
    """Configuration for paper trading simulation."""
    DEFAULT_SLIPPAGE = 0.0005  # 0.05%
    DEFAULT_COMMISSION_RATE = 0.0003  # 0.03%
    MIN_COMMISSION = 0.0  # Minimum commission in rupees


class PaperTradingSimulator:
    """Simulates order execution for paper trading mode."""
    
    def __init__(
        self,
        slippage: float = PaperTradingConfig.DEFAULT_SLIPPAGE,
        commission_rate: float = PaperTradingConfig.DEFAULT_COMMISSION_RATE,
        min_commission: float = PaperTradingConfig.MIN_COMMISSION
    ):
        """
        Initialize paper trading simulator.
        
        Args:
            slippage: Slippage percentage (default 0.05%)
            commission_rate: Commission rate percentage (default 0.03%)
            min_commission: Minimum commission amount (default 0)
        """
        self.slippage = slippage
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.pending_limit_orders: Dict[str, OrderData] = {}
        
        logger.info(
            f"Paper trading simulator initialized with slippage={slippage}, "
            f"commission_rate={commission_rate}, min_commission={min_commission}"
        )
    
    def simulate_market_order(
        self,
        order: OrderData,
        current_price: float
    ) -> tuple[OrderData, TradeData]:
        """
        Simulate market order execution at current price with slippage.
        
        Args:
            order: Order to simulate
            current_price: Current market price
            
        Returns:
            Tuple of (updated order, trade)
        """
        # Apply slippage based on order side
        if order.side == OrderSide.BUY:
            execution_price = current_price * (1 + self.slippage)
        else:  # SELL
            execution_price = current_price * (1 - self.slippage)
        
        # Calculate commission
        trade_value = execution_price * order.quantity
        commission = max(trade_value * self.commission_rate, self.min_commission)
        
        # Create trade
        trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=order.id,
            account_id=order.account_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=round(execution_price, 2),
            commission=round(commission, 2),
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_price = round(execution_price, 2)
        order.updated_at = datetime.utcnow()
        
        logger.info(
            f"Simulated market order: {order.symbol} {order.side.value} "
            f"{order.quantity} @ {execution_price:.2f} (slippage applied)"
        )
        
        return order, trade
    
    def simulate_limit_order(
        self,
        order: OrderData,
        current_price: float
    ) -> Optional[tuple[OrderData, TradeData]]:
        """
        Simulate limit order execution when price reaches limit.
        
        Args:
            order: Order to simulate
            current_price: Current market price
            
        Returns:
            Tuple of (updated order, trade) if filled, None if not filled yet
        """
        if order.price is None:
            logger.error(f"Limit order {order.id} has no price specified")
            return None
        
        # Check if limit price is reached
        should_fill = False
        if order.side == OrderSide.BUY and current_price <= order.price:
            should_fill = True
        elif order.side == OrderSide.SELL and current_price >= order.price:
            should_fill = True
        
        if not should_fill:
            # Order not filled yet, add to pending
            self.pending_limit_orders[order.id] = order
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.utcnow()
            logger.debug(
                f"Limit order pending: {order.symbol} {order.side.value} "
                f"{order.quantity} @ {order.price} (current: {current_price:.2f})"
            )
            return None
        
        # Fill at limit price
        execution_price = order.price
        
        # Calculate commission
        trade_value = execution_price * order.quantity
        commission = max(trade_value * self.commission_rate, self.min_commission)
        
        # Create trade
        trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=order.id,
            account_id=order.account_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=round(execution_price, 2),
            commission=round(commission, 2),
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_price = round(execution_price, 2)
        order.updated_at = datetime.utcnow()
        
        # Remove from pending
        if order.id in self.pending_limit_orders:
            del self.pending_limit_orders[order.id]
        
        logger.info(
            f"Simulated limit order fill: {order.symbol} {order.side.value} "
            f"{order.quantity} @ {execution_price:.2f}"
        )
        
        return order, trade
    
    def simulate_stop_order(
        self,
        order: OrderData,
        current_price: float
    ) -> Optional[tuple[OrderData, TradeData]]:
        """
        Simulate stop order execution when price reaches stop price.
        
        Args:
            order: Order to simulate
            current_price: Current market price
            
        Returns:
            Tuple of (updated order, trade) if triggered, None if not triggered yet
        """
        if order.stop_price is None:
            logger.error(f"Stop order {order.id} has no stop price specified")
            return None
        
        # Check if stop price is reached
        should_trigger = False
        if order.side == OrderSide.BUY and current_price >= order.stop_price:
            should_trigger = True
        elif order.side == OrderSide.SELL and current_price <= order.stop_price:
            should_trigger = True
        
        if not should_trigger:
            # Order not triggered yet
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.utcnow()
            logger.debug(
                f"Stop order pending: {order.symbol} {order.side.value} "
                f"{order.quantity} @ stop {order.stop_price} (current: {current_price:.2f})"
            )
            return None
        
        # Trigger stop order - execute as market order with slippage
        if order.side == OrderSide.BUY:
            execution_price = current_price * (1 + self.slippage)
        else:  # SELL
            execution_price = current_price * (1 - self.slippage)
        
        # Calculate commission
        trade_value = execution_price * order.quantity
        commission = max(trade_value * self.commission_rate, self.min_commission)
        
        # Create trade
        trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=order.id,
            account_id=order.account_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=round(execution_price, 2),
            commission=round(commission, 2),
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.average_price = round(execution_price, 2)
        order.updated_at = datetime.utcnow()
        
        logger.info(
            f"Simulated stop order trigger: {order.symbol} {order.side.value} "
            f"{order.quantity} @ {execution_price:.2f} (stop: {order.stop_price})"
        )
        
        return order, trade
    
    def check_pending_orders(self, symbol: str, current_price: float) -> list[tuple[OrderData, TradeData]]:
        """
        Check all pending limit orders for a symbol and fill if price reached.
        
        Args:
            symbol: Symbol to check
            current_price: Current market price
            
        Returns:
            List of (order, trade) tuples for filled orders
        """
        filled_orders = []
        orders_to_remove = []
        
        for order_id, order in self.pending_limit_orders.items():
            if order.symbol != symbol:
                continue
            
            result = self.simulate_limit_order(order, current_price)
            if result:
                filled_orders.append(result)
                orders_to_remove.append(order_id)
        
        # Remove filled orders from pending
        for order_id in orders_to_remove:
            if order_id in self.pending_limit_orders:
                del self.pending_limit_orders[order_id]
        
        return filled_orders
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            True if order was cancelled, False if not found
        """
        if order_id in self.pending_limit_orders:
            order = self.pending_limit_orders[order_id]
            del self.pending_limit_orders[order_id]
            logger.info(f"Cancelled pending order: {order_id}")
            return True
        
        logger.warning(f"Order {order_id} not found in pending orders")
        return False
