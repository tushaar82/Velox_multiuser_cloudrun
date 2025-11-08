"""Angel One SmartAPI broker connector implementation."""

import logging
import time
import pyotp
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
from SmartApi import SmartConnect

from shared.brokers.base import (
    IBrokerConnector,
    BrokerCredentials,
    BrokerOrder,
    BrokerOrderResponse,
    BrokerPosition,
    AccountInfo
)

logger = logging.getLogger(__name__)


class AngelOneConnector(IBrokerConnector):
    """Angel One SmartAPI broker connector."""
    
    # Exchange segment mapping
    EXCHANGE_MAP = {
        'NSE': 'NSE',
        'BSE': 'BSE',
        'NFO': 'NFO',
        'MCX': 'MCX'
    }
    
    # Order type mapping
    ORDER_TYPE_MAP = {
        'market': 'MARKET',
        'limit': 'LIMIT',
        'stop': 'STOPLOSS_LIMIT',
        'stop_limit': 'STOPLOSS_LIMIT'
    }
    
    # Product type mapping
    PRODUCT_TYPE_MAP = {
        'intraday': 'INTRADAY',
        'delivery': 'DELIVERY'
    }
    
    def __init__(self):
        """Initialize Angel One connector."""
        self.smart_api: Optional[SmartConnect] = None
        self._connected = False
        self._order_update_callback: Optional[Callable] = None
        self._connection_lost_callback: Optional[Callable] = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_interval = 30  # seconds
    
    def connect(self, credentials: BrokerCredentials) -> None:
        """
        Connect to Angel One SmartAPI.
        
        Args:
            credentials: Must contain api_key, client_code, password, and totp_token
            
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Extract credentials
            api_key = credentials.api_key
            client_code = credentials.user_id or credentials.additional_params.get('client_code')
            password = credentials.api_secret
            totp_token = credentials.additional_params.get('totp_token')
            
            if not all([api_key, client_code, password, totp_token]):
                raise ValueError("Missing required credentials: api_key, client_code, password, totp_token")
            
            # Generate TOTP
            totp = pyotp.TOTP(totp_token)
            totp_code = totp.now()
            
            # Initialize SmartAPI
            self.smart_api = SmartConnect(api_key=api_key)
            
            # Login
            data = self.smart_api.generateSession(client_code, password, totp_code)
            
            if not data or 'data' not in data:
                raise ConnectionError("Failed to generate session")
            
            auth_token = data['data']['jwtToken']
            refresh_token = data['data']['refreshToken']
            feed_token = self.smart_api.getfeedToken()
            
            self._connected = True
            self._reconnect_attempts = 0
            
            logger.info(f"Successfully connected to Angel One for client {client_code}")
            
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Angel One: {str(e)}")
            raise ConnectionError(f"Angel One connection failed: {str(e)}")
    
    def disconnect(self) -> None:
        """Disconnect from Angel One."""
        try:
            if self.smart_api:
                self.smart_api.terminateSession(self.smart_api.userId)
                logger.info("Disconnected from Angel One")
        except Exception as e:
            logger.warning(f"Error during disconnect: {str(e)}")
        finally:
            self._connected = False
            self.smart_api = None
    
    def is_connected(self) -> bool:
        """Check if connected to Angel One."""
        return self._connected and self.smart_api is not None
    
    def place_order(self, order: BrokerOrder) -> BrokerOrderResponse:
        """
        Place order with Angel One.
        
        Args:
            order: Order details
            
        Returns:
            BrokerOrderResponse with order ID
            
        Raises:
            ConnectionError: If not connected
            ValueError: If order parameters invalid
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Angel One")
        
        try:
            # Map order parameters
            order_params = {
                'variety': 'NORMAL',
                'tradingsymbol': order.symbol,
                'symboltoken': self._get_symbol_token(order.symbol, order.exchange),
                'transactiontype': 'BUY' if order.side == 'buy' else 'SELL',
                'exchange': self.EXCHANGE_MAP.get(order.exchange, 'NSE'),
                'ordertype': self.ORDER_TYPE_MAP.get(order.order_type, 'MARKET'),
                'producttype': self.PRODUCT_TYPE_MAP.get(order.product_type, 'INTRADAY'),
                'duration': 'DAY',
                'quantity': order.quantity
            }
            
            # Add price for limit orders
            if order.order_type in ['limit', 'stop', 'stop_limit']:
                if order.price is None:
                    raise ValueError(f"Price required for {order.order_type} orders")
                order_params['price'] = order.price
            
            # Add trigger price for stop orders
            if order.order_type in ['stop', 'stop_limit']:
                if order.stop_price is None:
                    raise ValueError(f"Stop price required for {order.order_type} orders")
                order_params['triggerprice'] = order.stop_price
            
            # Place order
            response = self.smart_api.placeOrder(order_params)
            
            if response and response.get('status'):
                order_id = response['data']['orderid']
                logger.info(f"Order placed successfully: {order_id}")
                return BrokerOrderResponse(
                    broker_order_id=order_id,
                    status='submitted',
                    message=response.get('message')
                )
            else:
                error_msg = response.get('message', 'Unknown error')
                logger.error(f"Order placement failed: {error_msg}")
                raise ValueError(f"Order placement failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise
    
    def cancel_order(self, broker_order_id: str) -> None:
        """Cancel order with Angel One."""
        if not self.is_connected():
            raise ConnectionError("Not connected to Angel One")
        
        try:
            response = self.smart_api.cancelOrder(broker_order_id, 'NORMAL')
            
            if not response or not response.get('status'):
                error_msg = response.get('message', 'Unknown error')
                raise ValueError(f"Order cancellation failed: {error_msg}")
            
            logger.info(f"Order cancelled successfully: {broker_order_id}")
            
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            raise
    
    def modify_order(self, broker_order_id: str, updates: Dict[str, Any]) -> None:
        """Modify order with Angel One."""
        if not self.is_connected():
            raise ConnectionError("Not connected to Angel One")
        
        try:
            # Build modification parameters
            modify_params = {
                'variety': 'NORMAL',
                'orderid': broker_order_id
            }
            
            if 'quantity' in updates:
                modify_params['quantity'] = updates['quantity']
            if 'price' in updates:
                modify_params['price'] = updates['price']
            if 'order_type' in updates:
                modify_params['ordertype'] = self.ORDER_TYPE_MAP.get(updates['order_type'])
            if 'stop_price' in updates:
                modify_params['triggerprice'] = updates['stop_price']
            
            response = self.smart_api.modifyOrder(modify_params)
            
            if not response or not response.get('status'):
                error_msg = response.get('message', 'Unknown error')
                raise ValueError(f"Order modification failed: {error_msg}")
            
            logger.info(f"Order modified successfully: {broker_order_id}")
            
        except Exception as e:
            logger.error(f"Error modifying order: {str(e)}")
            raise
    
    def get_order_status(self, broker_order_id: str) -> str:
        """Get order status from Angel One."""
        if not self.is_connected():
            raise ConnectionError("Not connected to Angel One")
        
        try:
            response = self.smart_api.orderBook()
            
            if response and response.get('status') and response.get('data'):
                orders = response['data']
                for order in orders:
                    if order.get('orderid') == broker_order_id:
                        return order.get('orderstatus', 'unknown').lower()
                
                raise ValueError(f"Order not found: {broker_order_id}")
            else:
                raise ValueError("Failed to fetch order book")
                
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            raise
    
    def get_positions(self) -> List[BrokerPosition]:
        """Get positions from Angel One."""
        if not self.is_connected():
            raise ConnectionError("Not connected to Angel One")
        
        try:
            response = self.smart_api.position()
            
            if not response or not response.get('status'):
                raise ValueError("Failed to fetch positions")
            
            positions = []
            data = response.get('data', [])
            
            for pos in data:
                if pos.get('netqty', 0) != 0:  # Only include open positions
                    positions.append(BrokerPosition(
                        symbol=pos.get('tradingsymbol'),
                        exchange=pos.get('exchange'),
                        quantity=int(pos.get('netqty', 0)),
                        average_price=float(pos.get('netprice', 0)),
                        last_price=float(pos.get('ltp', 0)),
                        pnl=float(pos.get('pnl', 0)),
                        product_type=pos.get('producttype', '').lower()
                    ))
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            raise
    
    def get_holdings(self) -> List[BrokerPosition]:
        """Get holdings from Angel One."""
        if not self.is_connected():
            raise ConnectionError("Not connected to Angel One")
        
        try:
            response = self.smart_api.holding()
            
            if not response or not response.get('status'):
                raise ValueError("Failed to fetch holdings")
            
            holdings = []
            data = response.get('data', [])
            
            for holding in data:
                holdings.append(BrokerPosition(
                    symbol=holding.get('tradingsymbol'),
                    exchange=holding.get('exchange'),
                    quantity=int(holding.get('quantity', 0)),
                    average_price=float(holding.get('averageprice', 0)),
                    last_price=float(holding.get('ltp', 0)),
                    pnl=float(holding.get('pnl', 0)),
                    product_type='delivery'
                ))
            
            return holdings
            
        except Exception as e:
            logger.error(f"Error getting holdings: {str(e)}")
            raise
    
    def get_account_info(self) -> AccountInfo:
        """Get account info from Angel One."""
        if not self.is_connected():
            raise ConnectionError("Not connected to Angel One")
        
        try:
            response = self.smart_api.rmsLimit()
            
            if not response or not response.get('status'):
                raise ValueError("Failed to fetch account info")
            
            data = response.get('data', {})
            
            return AccountInfo(
                account_id=self.smart_api.userId,
                available_funds=float(data.get('availablecash', 0)),
                used_margin=float(data.get('utiliseddebits', 0)),
                total_margin=float(data.get('net', 0))
            )
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            raise
    
    def on_order_update(self, callback: Callable) -> None:
        """Register callback for order updates."""
        self._order_update_callback = callback
        logger.info("Order update callback registered")
    
    def on_connection_lost(self, callback: Callable) -> None:
        """Register callback for connection loss."""
        self._connection_lost_callback = callback
        logger.info("Connection lost callback registered")
    
    def _get_symbol_token(self, symbol: str, exchange: str) -> str:
        """
        Get symbol token for Angel One.
        This is a placeholder - in production, this should query the symbol mapping service.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            Symbol token string
        """
        # TODO: Integrate with symbol mapping service
        # For now, return symbol as token (will need proper implementation)
        return symbol
    
    def _attempt_reconnection(self) -> None:
        """Attempt to reconnect to Angel One."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            if self._connection_lost_callback:
                self._connection_lost_callback()
            return
        
        self._reconnect_attempts += 1
        logger.info(f"Attempting reconnection {self._reconnect_attempts}/{self._max_reconnect_attempts}")
        
        time.sleep(self._reconnect_interval)
        
        # Reconnection logic would go here
        # This would need stored credentials to reconnect
