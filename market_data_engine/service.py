"""
Market Data Engine Service

Main service that coordinates market data processing, candle formation, and distribution.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from market_data_engine.models import Tick, Candle, IndicatorValue
from market_data_engine.storage import InfluxDBStorage, RedisStorage, CandleBufferManager
from market_data_engine.candle_manager import CandleManager
from market_data_engine.indicators import IndicatorEngine
from market_data_engine.subscription_manager import SubscriptionManager
from market_data_engine.feed_connector import IMarketDataFeed, AngelOneMarketDataFeed, SimulatedMarketDataFeed, MarketDataDistributor

logger = logging.getLogger(__name__)


class MarketDataEngine:
    """
    Main market data engine service.
    
    Coordinates:
    - Market data feed connection
    - Subscription management
    - Tick processing and candle formation
    - Indicator calculations
    - Data distribution via Redis pub/sub
    """
    
    def __init__(
        self,
        feed_type: str = 'simulated',
        feed_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize market data engine.
        
        Args:
            feed_type: Type of feed ('angel_one', 'simulated')
            feed_config: Configuration for the feed (API keys, etc.)
        """
        # Initialize storage
        self.influxdb = InfluxDBStorage()
        self.redis = RedisStorage()
        self.buffer_manager = CandleBufferManager(max_candles_per_buffer=500)
        
        # Initialize managers
        self.candle_manager = CandleManager(self.influxdb, self.redis, self.buffer_manager)
        self.indicator_engine = IndicatorEngine(self.redis)
        self.subscription_manager = SubscriptionManager()
        self.distributor = MarketDataDistributor(self.redis, self.subscription_manager)
        
        # Initialize market data feed
        self.feed = self._create_feed(feed_type, feed_config or {})
        
        # Register callbacks
        self.feed.on_tick(self._on_tick_received)
        self.feed.on_connection_lost(self._on_connection_lost)
        
        self.candle_manager.register_candle_complete_callback(self._on_candle_complete)
        self.candle_manager.register_candle_update_callback(self._on_candle_update)
        
        self.running = False
    
    def _create_feed(self, feed_type: str, config: Dict[str, Any]) -> IMarketDataFeed:
        """Create market data feed based on type"""
        if feed_type == 'angel_one':
            return AngelOneMarketDataFeed(
                api_key=config.get('api_key', ''),
                client_code=config.get('client_code', ''),
                feed_token=config.get('feed_token', '')
            )
        elif feed_type == 'simulated':
            return SimulatedMarketDataFeed()
        else:
            raise ValueError(f"Unknown feed type: {feed_type}")
    
    def start(self) -> bool:
        """Start the market data engine"""
        logger.info("Starting Market Data Engine")
        
        try:
            # Connect to storage
            self.influxdb.connect()
            self.redis.connect()
            
            # Connect to market data feed
            if not self.feed.connect():
                logger.error("Failed to connect to market data feed")
                return False
            
            self.running = True
            logger.info("Market Data Engine started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Market Data Engine: {e}", exc_info=True)
            return False
    
    def stop(self) -> None:
        """Stop the market data engine"""
        logger.info("Stopping Market Data Engine")
        
        self.running = False
        
        # Disconnect from feed
        self.feed.disconnect()
        
        # Disconnect from storage
        self.influxdb.disconnect()
        self.redis.disconnect()
        
        logger.info("Market Data Engine stopped")
    
    def subscribe(
        self,
        subscriber_id: str,
        symbol: str,
        timeframes: List[str],
        exchange: str = 'NSE'
    ) -> None:
        """
        Subscribe to market data for a symbol.
        
        Args:
            subscriber_id: Unique ID of subscriber (strategy or client)
            symbol: Symbol to subscribe to
            timeframes: List of timeframes needed
            exchange: Exchange segment
        """
        # Add to subscription manager
        self.subscription_manager.subscribe(subscriber_id, symbol, timeframes, exchange)
        
        # Subscribe to feed if this is the first subscriber for this symbol
        subscribed_symbols = self.subscription_manager.get_subscribed_symbols()
        if symbol in subscribed_symbols:
            # Check if we need to subscribe to the feed
            # (only subscribe once per symbol regardless of number of subscribers)
            self.feed.subscribe_symbols([symbol], exchange)
    
    def unsubscribe(
        self,
        subscriber_id: str,
        symbol: Optional[str] = None,
        timeframes: Optional[List[str]] = None
    ) -> None:
        """
        Unsubscribe from market data.
        
        Args:
            subscriber_id: Unique ID of subscriber
            symbol: Symbol to unsubscribe from (None = all)
            timeframes: Timeframes to unsubscribe from (None = all)
        """
        # Get symbols before unsubscribing
        symbols_before = set(self.subscription_manager.get_subscribed_symbols())
        
        # Remove from subscription manager
        self.subscription_manager.unsubscribe(subscriber_id, symbol, timeframes)
        
        # Get symbols after unsubscribing
        symbols_after = set(self.subscription_manager.get_subscribed_symbols())
        
        # Unsubscribe from feed if no more subscribers for symbols
        symbols_to_unsubscribe = symbols_before - symbols_after
        if symbols_to_unsubscribe:
            self.feed.unsubscribe_symbols(list(symbols_to_unsubscribe))
    
    def get_forming_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Get current forming candle"""
        return self.candle_manager.get_forming_candle(symbol, timeframe)
    
    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int
    ) -> List[Candle]:
        """Get historical candles"""
        return self.candle_manager.get_historical_candles(symbol, timeframe, count)
    
    def calculate_indicator(
        self,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        params: Dict[str, Any]
    ) -> Optional[IndicatorValue]:
        """Calculate indicator value"""
        # Get candles
        indicator = self.indicator_engine.get_indicator(symbol, timeframe, indicator_type, params)
        required_candles = indicator.get_required_candles()
        candles = self.candle_manager.get_historical_candles(symbol, timeframe, required_candles)
        
        # Calculate
        return self.indicator_engine.calculate_indicator(
            symbol, timeframe, indicator_type, params, candles
        )
    
    def get_subscription_stats(self) -> Dict:
        """Get subscription statistics"""
        return self.subscription_manager.get_stats()
    
    def _on_tick_received(self, tick: Tick) -> None:
        """Handle incoming tick data"""
        if not self.running:
            return
        
        try:
            # Process tick through candle manager
            self.candle_manager.on_tick(tick)
            
            # Distribute tick to subscribers
            self.distributor.distribute_tick(tick)
            
        except Exception as e:
            logger.error(f"Error processing tick: {e}", exc_info=True)
    
    def _on_candle_complete(self, candle: Candle) -> None:
        """Handle candle completion"""
        logger.info(f"Candle completed: {candle.symbol} {candle.timeframe}")
        
        # Recalculate indicators for this symbol/timeframe
        # This would trigger strategy evaluations in production
        pass
    
    def _on_candle_update(self, candle: Candle) -> None:
        """Handle forming candle update"""
        # This is called frequently, so we only log at debug level
        logger.debug(f"Candle updated: {candle.symbol} {candle.timeframe} @ {candle.close}")
    
    def _on_connection_lost(self) -> None:
        """Handle market data feed connection loss"""
        logger.error("Market data feed connection lost")
        
        # The feed connector will handle reconnection automatically
        # Here we could pause strategies or notify users
    
    def inject_tick(self, tick: Tick) -> None:
        """
        Inject a tick for testing (only works with simulated feed).
        
        Args:
            tick: Tick to inject
        """
        if isinstance(self.feed, SimulatedMarketDataFeed):
            self.feed.inject_tick(tick)
        else:
            logger.warning("inject_tick only works with simulated feed")
