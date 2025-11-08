"""Base classes and interfaces for broker connectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


@dataclass
class BrokerCredentials:
    """Broker authentication credentials."""
    api_key: str
    api_secret: str
    user_id: Optional[str] = None
    additional_params: Optional[Dict[str, str]] = None


@dataclass
class BrokerOrder:
    """Order request to be sent to broker."""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    order_type: str  # 'market', 'limit', 'stop', 'stop_limit'
    price: Optional[float] = None
    stop_price: Optional[float] = None
    product_type: str = 'intraday'  # 'intraday' or 'delivery'
    exchange: str = 'NSE'  # 'NSE', 'BSE', 'NFO', 'MCX'


@dataclass
class BrokerOrderResponse:
    """Response from broker after order submission."""
    broker_order_id: str
    status: str
    message: Optional[str] = None


@dataclass
class BrokerPosition:
    """Position information from broker."""
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    product_type: str  # 'intraday' or 'delivery'


@dataclass
class AccountInfo:
    """Broker account information."""
    account_id: str
    available_funds: float
    used_margin: float
    total_margin: float


class IBrokerConnector(ABC):
    """Abstract base class for broker connector implementations."""
    
    @abstractmethod
    def connect(self, credentials: BrokerCredentials) -> None:
        """
        Establish connection to broker.
        
        Args:
            credentials: Broker authentication credentials
            
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from broker and cleanup resources."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if broker connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    def place_order(self, order: BrokerOrder) -> BrokerOrderResponse:
        """
        Place an order with the broker.
        
        Args:
            order: Order details
            
        Returns:
            BrokerOrderResponse with order ID and status
            
        Raises:
            ConnectionError: If not connected
            ValueError: If order parameters are invalid
        """
        pass
    
    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> None:
        """
        Cancel a pending order.
        
        Args:
            broker_order_id: Broker's order ID
            
        Raises:
            ConnectionError: If not connected
            ValueError: If order not found or cannot be cancelled
        """
        pass
    
    @abstractmethod
    def modify_order(self, broker_order_id: str, updates: Dict[str, Any]) -> None:
        """
        Modify an existing order.
        
        Args:
            broker_order_id: Broker's order ID
            updates: Dictionary of fields to update (price, quantity, etc.)
            
        Raises:
            ConnectionError: If not connected
            ValueError: If order not found or cannot be modified
        """
        pass
    
    @abstractmethod
    def get_order_status(self, broker_order_id: str) -> str:
        """
        Get current status of an order.
        
        Args:
            broker_order_id: Broker's order ID
            
        Returns:
            Order status string
            
        Raises:
            ConnectionError: If not connected
            ValueError: If order not found
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[BrokerPosition]:
        """
        Get all current positions.
        
        Returns:
            List of BrokerPosition objects
            
        Raises:
            ConnectionError: If not connected
        """
        pass
    
    @abstractmethod
    def get_holdings(self) -> List[BrokerPosition]:
        """
        Get all holdings (delivery positions).
        
        Returns:
            List of BrokerPosition objects for delivery holdings
            
        Raises:
            ConnectionError: If not connected
        """
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """
        Get account information including funds and margins.
        
        Returns:
            AccountInfo object
            
        Raises:
            ConnectionError: If not connected
        """
        pass
    
    @abstractmethod
    def on_order_update(self, callback: Callable) -> None:
        """
        Register callback for order status updates.
        
        Args:
            callback: Function to call when order status changes
        """
        pass
    
    @abstractmethod
    def on_connection_lost(self, callback: Callable) -> None:
        """
        Register callback for connection loss events.
        
        Args:
            callback: Function to call when connection is lost
        """
        pass
