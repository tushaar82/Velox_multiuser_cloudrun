"""Mock broker connector for offline testing and development."""

import logging
import uuid
import random
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timezone

from shared.brokers.base import (
    IBrokerConnector,
    BrokerCredentials,
    BrokerOrder,
    BrokerOrderResponse,
    BrokerPosition,
    AccountInfo
)

logger = logging.getLogger(__name__)


class MockBrokerConnector(IBrokerConnector):
    """Mock broker connector that simulates order fills without real broker."""
    
    def __init__(self):
        """Initialize mock broker."""
        self._connected = False
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._positions: Dict[str, BrokerPosition] = {}
        self._account_funds = 1000000.0  # Start with 10 lakh
        self._order_update_callback: Optional[Callable] = None
        self._connection_lost_callback: Optional[Callable] = None
    
    def connect(self, credentials: BrokerCredentials) -> None:
        """
        Simulate broker connection.
        
        Args:
            credentials: Broker credentials (not validated in mock)
        """
        logger.info("Mock broker: Simulating connection")
        self._connected = True
        logger.info("Mock broker: Connected successfully")
    
    def disconnect(self) -> None:
        """Disconnect from mock broker."""
        logger.info("Mock broker: Disconnecting")
        self._connected = False
        self._orders.clear()
        self._positions.clear()
    
    def is_connected(self) -> bool:
        """Check if mock broker is connected."""
        return self._connected
    
    def place_order(self, order: BrokerOrder) -> BrokerOrderResponse:
        """
        Simulate order placement.
        
        Args:
            order: Order details
            
        Returns:
            BrokerOrderResponse with simulated order ID
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to mock broker")
        
        # Generate order ID
        order_id = str(uuid.uuid4())
        
        # Simulate order with random fill price (±0.1% slippage)
        base_price = order.price if order.price else 100.0
        slippage = random.uniform(-0.001, 0.001)
        fill_price = base_price * (1 + slippage)
        
        # Store order
        self._orders[order_id] = {
            'order_id': order_id,
            'symbol': order.symbol,
            'side': order.side,
            'quantity': order.quantity,
            'order_type': order.order_type,
            'price': order.price,
            'fill_price': fill_price,
            'status': 'filled',  # Instantly fill for mock
            'created_at': datetime.now(timezone.utc)
        }
        
        # Update positions
        self._update_position(order.symbol, order.side, order.quantity, fill_price, order.exchange)
        
        logger.info(f"Mock broker: Order placed and filled - {order_id} ({order.symbol} {order.side} {order.quantity})")
        
        # Trigger callback if registered
        if self._order_update_callback:
            self._order_update_callback(order_id, 'filled')
        
        return BrokerOrderResponse(
            broker_order_id=order_id,
            status='filled',
            message='Order filled successfully (mock)'
        )
    
    def cancel_order(self, broker_order_id: str) -> None:
        """
        Simulate order cancellation.
        
        Args:
            broker_order_id: Order ID to cancel
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to mock broker")
        
        if broker_order_id not in self._orders:
            raise ValueError(f"Order not found: {broker_order_id}")
        
        order = self._orders[broker_order_id]
        if order['status'] == 'filled':
            raise ValueError("Cannot cancel filled order")
        
        order['status'] = 'cancelled'
        logger.info(f"Mock broker: Order cancelled - {broker_order_id}")
    
    def modify_order(self, broker_order_id: str, updates: Dict[str, Any]) -> None:
        """
        Simulate order modification.
        
        Args:
            broker_order_id: Order ID to modify
            updates: Fields to update
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to mock broker")
        
        if broker_order_id not in self._orders:
            raise ValueError(f"Order not found: {broker_order_id}")
        
        order = self._orders[broker_order_id]
        if order['status'] == 'filled':
            raise ValueError("Cannot modify filled order")
        
        # Update order fields
        for key, value in updates.items():
            if key in order:
                order[key] = value
        
        logger.info(f"Mock broker: Order modified - {broker_order_id}")
    
    def get_order_status(self, broker_order_id: str) -> str:
        """
        Get order status.
        
        Args:
            broker_order_id: Order ID
            
        Returns:
            Order status string
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to mock broker")
        
        if broker_order_id not in self._orders:
            raise ValueError(f"Order not found: {broker_order_id}")
        
        return self._orders[broker_order_id]['status']
    
    def get_positions(self) -> List[BrokerPosition]:
        """
        Get all current positions.
        
        Returns:
            List of positions
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to mock broker")
        
        return list(self._positions.values())
    
    def get_holdings(self) -> List[BrokerPosition]:
        """
        Get holdings (delivery positions).
        
        Returns:
            List of delivery positions
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to mock broker")
        
        # Return only delivery positions
        return [pos for pos in self._positions.values() if pos.product_type == 'delivery']
    
    def get_account_info(self) -> AccountInfo:
        """
        Get account information.
        
        Returns:
            Account info with simulated funds
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to mock broker")
        
        # Calculate used margin from positions
        used_margin = sum(
            abs(pos.quantity * pos.average_price * 0.2)  # Assume 20% margin
            for pos in self._positions.values()
        )
        
        return AccountInfo(
            account_id='mock_account',
            available_funds=self._account_funds - used_margin,
            used_margin=used_margin,
            total_margin=self._account_funds
        )
    
    def on_order_update(self, callback: Callable) -> None:
        """Register callback for order updates."""
        self._order_update_callback = callback
        logger.info("Mock broker: Order update callback registered")
    
    def on_connection_lost(self, callback: Callable) -> None:
        """Register callback for connection loss."""
        self._connection_lost_callback = callback
        logger.info("Mock broker: Connection lost callback registered")
    
    def _update_position(self, symbol: str, side: str, quantity: int, price: float, exchange: str) -> None:
        """
        Update position after order fill.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Order quantity
            price: Fill price
            exchange: Exchange name
        """
        position_key = f"{symbol}_{exchange}"
        
        if position_key in self._positions:
            pos = self._positions[position_key]
            
            if side == 'buy':
                # Add to position
                total_cost = (pos.quantity * pos.average_price) + (quantity * price)
                new_quantity = pos.quantity + quantity
                pos.quantity = new_quantity
                pos.average_price = total_cost / new_quantity if new_quantity > 0 else 0
            else:
                # Reduce position
                pos.quantity -= quantity
                
                # Remove position if closed
                if pos.quantity <= 0:
                    del self._positions[position_key]
                    return
            
            # Update last price and P&L
            pos.last_price = price
            pos.pnl = (pos.last_price - pos.average_price) * pos.quantity
        else:
            # Create new position
            if side == 'buy':
                self._positions[position_key] = BrokerPosition(
                    symbol=symbol,
                    exchange=exchange,
                    quantity=quantity,
                    average_price=price,
                    last_price=price,
                    pnl=0.0,
                    product_type='intraday'
                )
    
    def simulate_price_update(self, symbol: str, new_price: float) -> None:
        """
        Simulate price update for testing.
        
        Args:
            symbol: Trading symbol
            new_price: New market price
        """
        for pos in self._positions.values():
            if pos.symbol == symbol:
                pos.last_price = new_price
                pos.pnl = (pos.last_price - pos.average_price) * pos.quantity
    
    def simulate_connection_loss(self) -> None:
        """Simulate connection loss for testing."""
        logger.warning("Mock broker: Simulating connection loss")
        self._connected = False
        if self._connection_lost_callback:
            self._connection_lost_callback()
