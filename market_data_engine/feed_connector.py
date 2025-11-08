"""
Market Data Feed Connector

Handles connection to market data feeds (live or simulated) and distributes data.
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, List
from datetime import datetime
import logging
import time
import threading

from .models import Tick
from .subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)


class IMarketDataFeed(ABC):
    """Interface for market data feed sources"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the market data feed"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the market data feed"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to the feed"""
        pass
    
    @abstractmethod
    def subscribe_symbols(self, symbols: List[str], exchange: str = 'NSE') -> None:
        """Subscribe to market data for symbols"""
        pass
    
    @abstractmethod
    def unsubscribe_symbols(self, symbols: List[str]) -> None:
        """Unsubscribe from market data for symbols"""
        pass
    
    @abstractmethod
    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        """Register callback for tick data"""
        pass
    
    @abstractmethod
    def on_connection_lost(self, callback: Callable[[], None]) -> None:
        """Register callback for connection loss"""
        pass


class AngelOneMarketDataFeed(IMarketDataFeed):
    """Angel One SmartAPI WebSocket feed for real-time market data"""
    
    def __init__(self, api_key: str, client_code: str, feed_token: str):
        self.api_key = api_key
        self.client_code = client_code
        self.feed_token = feed_token
        self.ws_client = None
        self.connected = False
        self.tick_callbacks: List[Callable[[Tick], None]] = []
        self.connection_lost_callbacks: List[Callable[[], None]] = []
        self.reconnect_thread: Optional[threading.Thread] = None
        self.should_reconnect = True
    
    def connect(self) -> bool:
        """Connect to Angel One SmartAPI WebSocket feed"""
        try:
            from smartapi import SmartWebSocket
            
            # Initialize WebSocket client
            self.ws_client = SmartWebSocket(
                auth_token=self.feed_token,
                api_key=self.api_key,
                client_code=self.client_code,
                feed_token=self.feed_token
            )
            
            # Set up callbacks
            self.ws_client.on_open = self._on_open
            self.ws_client.on_data = self._on_data
            self.ws_client.on_error = self._on_error
            self.ws_client.on_close = self._on_close
            
            # Connect
            self.ws_client.connect()
            self.connected = True
            logger.info("Connected to Angel One market data feed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Angel One feed: {e}", exc_info=True)
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Angel One feed"""
        self.should_reconnect = False
        if self.ws_client:
            try:
                self.ws_client.close()
            except Exception as e:
                logger.error(f"Error disconnecting from feed: {e}")
        self.connected = False
        logger.info("Disconnected from Angel One market data feed")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
    
    def subscribe_symbols(self, symbols: List[str], exchange: str = 'NSE') -> None:
        """Subscribe to symbols on Angel One feed"""
        if not self.connected or not self.ws_client:
            logger.warning("Cannot subscribe: not connected to feed")
            return
        
        try:
            # Convert symbols to Angel One token format
            # This would use the symbol mapping service in production
            tokens = self._get_tokens_for_symbols(symbols, exchange)
            
            # Subscribe to tokens
            self.ws_client.subscribe(tokens)
            logger.info(f"Subscribed to {len(symbols)} symbols on {exchange}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to symbols: {e}", exc_info=True)
    
    def unsubscribe_symbols(self, symbols: List[str]) -> None:
        """Unsubscribe from symbols"""
        if not self.connected or not self.ws_client:
            return
        
        try:
            tokens = self._get_tokens_for_symbols(symbols)
            self.ws_client.unsubscribe(tokens)
            logger.info(f"Unsubscribed from {len(symbols)} symbols")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from symbols: {e}", exc_info=True)
    
    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        """Register tick callback"""
        self.tick_callbacks.append(callback)
    
    def on_connection_lost(self, callback: Callable[[], None]) -> None:
        """Register connection lost callback"""
        self.connection_lost_callbacks.append(callback)
    
    def _on_open(self, ws):
        """WebSocket opened"""
        logger.info("Angel One WebSocket opened")
        self.connected = True
    
    def _on_data(self, ws, message):
        """Received tick data from WebSocket"""
        try:
            # Parse Angel One tick data format
            tick = self._parse_tick_data(message)
            if tick:
                # Notify all callbacks
                for callback in self.tick_callbacks:
                    try:
                        callback(tick)
                    except Exception as e:
                        logger.error(f"Error in tick callback: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error processing tick data: {e}", exc_info=True)
    
    def _on_error(self, ws, error):
        """WebSocket error"""
        logger.error(f"Angel One WebSocket error: {error}")
    
    def _on_close(self, ws):
        """WebSocket closed"""
        logger.warning("Angel One WebSocket closed")
        self.connected = False
        
        # Notify connection lost callbacks
        for callback in self.connection_lost_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in connection lost callback: {e}", exc_info=True)
        
        # Attempt reconnection
        if self.should_reconnect:
            self._start_reconnection()
    
    def _start_reconnection(self) -> None:
        """Start reconnection attempts"""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
        
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop)
        self.reconnect_thread.daemon = True
        self.reconnect_thread.start()
    
    def _reconnect_loop(self) -> None:
        """Reconnection loop with immediate retry"""
        attempt = 0
        max_attempts = 10
        
        while attempt < max_attempts and self.should_reconnect:
            attempt += 1
            logger.info(f"Reconnection attempt {attempt}/{max_attempts}")
            
            if self.connect():
                logger.info("Reconnection successful")
                return
            
            # Wait before next attempt (immediate first attempt, then 30s intervals)
            if attempt < max_attempts:
                time.sleep(30 if attempt > 1 else 0)
        
        logger.error("Failed to reconnect after maximum attempts")
    
    def _parse_tick_data(self, message: Dict) -> Optional[Tick]:
        """Parse Angel One tick data format to Tick object"""
        try:
            # Angel One tick data format (example)
            # Actual format depends on SmartAPI WebSocket response
            return Tick(
                symbol=message.get('symbol', ''),
                price=float(message.get('last_price', 0)),
                volume=int(message.get('volume', 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Failed to parse tick data: {e}")
            return None
    
    def _get_tokens_for_symbols(self, symbols: List[str], exchange: str = 'NSE') -> List[str]:
        """
        Convert symbols to broker tokens.
        
        In production, this would use the symbol mapping service.
        For now, returns symbols as-is.
        """
        # TODO: Integrate with symbol mapping service
        return symbols


class SimulatedMarketDataFeed(IMarketDataFeed):
    """Simulated market data feed for testing"""
    
    def __init__(self):
        self.connected = False
        self.tick_callbacks: List[Callable[[Tick], None]] = []
        self.connection_lost_callbacks: List[Callable[[], None]] = []
        self.subscribed_symbols: List[str] = []
    
    def connect(self) -> bool:
        """Connect to simulated feed"""
        self.connected = True
        logger.info("Connected to simulated market data feed")
        return True
    
    def disconnect(self) -> None:
        """Disconnect from simulated feed"""
        self.connected = False
        logger.info("Disconnected from simulated market data feed")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
    
    def subscribe_symbols(self, symbols: List[str], exchange: str = 'NSE') -> None:
        """Subscribe to symbols"""
        self.subscribed_symbols.extend(symbols)
        logger.info(f"Subscribed to {len(symbols)} symbols in simulated feed")
    
    def unsubscribe_symbols(self, symbols: List[str]) -> None:
        """Unsubscribe from symbols"""
        for symbol in symbols:
            if symbol in self.subscribed_symbols:
                self.subscribed_symbols.remove(symbol)
        logger.info(f"Unsubscribed from {len(symbols)} symbols in simulated feed")
    
    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        """Register tick callback"""
        self.tick_callbacks.append(callback)
    
    def on_connection_lost(self, callback: Callable[[], None]) -> None:
        """Register connection lost callback"""
        self.connection_lost_callbacks.append(callback)
    
    def inject_tick(self, tick: Tick) -> None:
        """Inject a tick for testing"""
        if not self.connected:
            logger.warning("Cannot inject tick: not connected")
            return
        
        for callback in self.tick_callbacks:
            try:
                callback(tick)
            except Exception as e:
                logger.error(f"Error in tick callback: {e}", exc_info=True)


class MarketDataDistributor:
    """Distributes market data to subscribers via Redis pub/sub"""
    
    def __init__(self, redis_storage, subscription_manager: SubscriptionManager):
        self.redis = redis_storage
        self.subscription_manager = subscription_manager
    
    def distribute_tick(self, tick: Tick) -> None:
        """Distribute tick to all subscribers"""
        # Get subscribers for this symbol
        subscribers = self.subscription_manager.get_subscribers_for_symbol(tick.symbol)
        
        if not subscribers:
            return
        
        # Publish to Redis pub/sub channel
        channel = f"tick:{tick.symbol}"
        self.redis.client.publish(channel, tick.to_dict())
        
        logger.debug(f"Distributed tick for {tick.symbol} to {len(subscribers)} subscribers")
    
    def subscribe_to_ticks(self, symbol: str):
        """Subscribe to tick updates for a symbol"""
        pubsub = self.redis.client.pubsub()
        channel = f"tick:{symbol}"
        pubsub.subscribe(channel)
        return pubsub
