"""
Candle Manager

Handles tick data ingestion, candle formation, and candle completion detection.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
import logging

from .models import Tick, Candle
from .storage import InfluxDBStorage, RedisStorage, CandleBufferManager

logger = logging.getLogger(__name__)


class CandleManager:
    """Manages candle formation from tick data across multiple timeframes"""
    
    # Supported timeframes in minutes
    TIMEFRAMES = {
        '1m': 1,
        '3m': 3,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '1d': 1440
    }
    
    def __init__(
        self,
        influxdb_storage: InfluxDBStorage,
        redis_storage: RedisStorage,
        buffer_manager: CandleBufferManager
    ):
        self.influxdb = influxdb_storage
        self.redis = redis_storage
        self.buffer_manager = buffer_manager
        self.candle_complete_callbacks: List[Callable[[Candle], None]] = []
        self.candle_update_callbacks: List[Callable[[Candle], None]] = []
    
    def register_candle_complete_callback(self, callback: Callable[[Candle], None]) -> None:
        """Register a callback to be called when a candle completes"""
        self.candle_complete_callbacks.append(callback)
    
    def register_candle_update_callback(self, callback: Callable[[Candle], None]) -> None:
        """Register a callback to be called when a forming candle updates"""
        self.candle_update_callbacks.append(callback)
    
    def on_tick(self, tick: Tick) -> None:
        """
        Process incoming tick data and update candles for all timeframes.
        
        This is the main entry point for market data processing.
        """
        logger.debug(f"Processing tick: {tick.symbol} @ {tick.price} at {tick.timestamp}")
        
        # Update candles for all timeframes
        for timeframe in self.TIMEFRAMES.keys():
            self._update_candle_for_timeframe(tick, timeframe)
    
    def _update_candle_for_timeframe(self, tick: Tick, timeframe: str) -> None:
        """Update or create candle for a specific timeframe"""
        # Get the candle timestamp for this timeframe
        candle_timestamp = self._get_candle_timestamp(tick.timestamp, timeframe)
        
        # Try to get existing forming candle from Redis
        forming_candle = self.redis.get_forming_candle(tick.symbol, timeframe)
        
        if forming_candle is None:
            # Create new candle
            forming_candle = Candle.from_tick(tick, timeframe, candle_timestamp)
            logger.debug(f"Created new {timeframe} candle for {tick.symbol} at {candle_timestamp}")
        elif forming_candle.timestamp != candle_timestamp:
            # Current candle has completed, start new one
            self._complete_candle(forming_candle)
            forming_candle = Candle.from_tick(tick, timeframe, candle_timestamp)
            logger.debug(f"Completed {timeframe} candle for {tick.symbol}, started new one")
        else:
            # Update existing forming candle
            forming_candle.update_with_tick(tick)
        
        # Store updated forming candle in Redis
        self.redis.store_forming_candle(forming_candle)
        
        # Publish update to Redis pub/sub
        self.redis.publish_candle_update(forming_candle)
        
        # Notify callbacks
        for callback in self.candle_update_callbacks:
            try:
                callback(forming_candle)
            except Exception as e:
                logger.error(f"Error in candle update callback: {e}", exc_info=True)
    
    def _complete_candle(self, candle: Candle) -> None:
        """Mark candle as complete and store it"""
        candle.is_forming = False
        
        logger.info(
            f"Candle completed: {candle.symbol} {candle.timeframe} "
            f"O:{candle.open} H:{candle.high} L:{candle.low} C:{candle.close} V:{candle.volume}"
        )
        
        # Store in InfluxDB
        try:
            self.influxdb.store_candle(candle)
        except Exception as e:
            logger.error(f"Failed to store candle in InfluxDB: {e}", exc_info=True)
        
        # Add to in-memory buffer
        self.buffer_manager.add_candle(candle)
        
        # Remove from Redis forming candles
        self.redis.delete_forming_candle(candle.symbol, candle.timeframe)
        
        # Publish completion event
        self.redis.publish_candle_complete(candle)
        
        # Notify callbacks
        for callback in self.candle_complete_callbacks:
            try:
                callback(candle)
            except Exception as e:
                logger.error(f"Error in candle complete callback: {e}", exc_info=True)
    
    def _get_candle_timestamp(self, tick_timestamp: datetime, timeframe: str) -> datetime:
        """
        Calculate the candle start timestamp for a given tick timestamp and timeframe.
        
        For example, if tick is at 09:37:45 and timeframe is 5m,
        the candle timestamp should be 09:35:00.
        """
        minutes = self.TIMEFRAMES[timeframe]
        
        if timeframe == '1d':
            # Daily candles start at midnight
            return tick_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate minutes since midnight
        minutes_since_midnight = tick_timestamp.hour * 60 + tick_timestamp.minute
        
        # Round down to nearest timeframe interval
        candle_minutes = (minutes_since_midnight // minutes) * minutes
        
        # Create candle timestamp
        candle_hour = candle_minutes // 60
        candle_minute = candle_minutes % 60
        
        return tick_timestamp.replace(
            hour=candle_hour,
            minute=candle_minute,
            second=0,
            microsecond=0
        )
    
    def get_forming_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Get the current forming candle for a symbol/timeframe"""
        return self.redis.get_forming_candle(symbol, timeframe)
    
    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int
    ) -> List[Candle]:
        """
        Get historical candles from buffer and InfluxDB.
        
        First tries to get from in-memory buffer, then falls back to InfluxDB if needed.
        """
        # Try to get from buffer first
        buffer_candles = self.buffer_manager.get_recent_candles(symbol, timeframe, count)
        
        if len(buffer_candles) >= count:
            return buffer_candles
        
        # Need more candles from InfluxDB
        try:
            influx_candles = self.influxdb.get_recent_candles(symbol, timeframe, count)
            return influx_candles
        except Exception as e:
            logger.error(f"Failed to get historical candles from InfluxDB: {e}", exc_info=True)
            return buffer_candles
    
    def get_candles_for_period(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Candle]:
        """Get candles for a specific time period from InfluxDB"""
        try:
            return self.influxdb.get_historical_candles(symbol, timeframe, start_time, end_time)
        except Exception as e:
            logger.error(f"Failed to get candles for period from InfluxDB: {e}", exc_info=True)
            return []
    
    def force_complete_candle(self, symbol: str, timeframe: str) -> None:
        """
        Force completion of a forming candle (useful for testing or end of day).
        """
        forming_candle = self.redis.get_forming_candle(symbol, timeframe)
        if forming_candle:
            self._complete_candle(forming_candle)
    
    def initialize_from_historical_data(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Candle]
    ) -> None:
        """
        Initialize candle buffer with historical data.
        
        Useful for loading data on startup or after reconnection.
        """
        logger.info(f"Initializing {symbol} {timeframe} with {len(candles)} historical candles")
        
        for candle in candles:
            if not candle.is_forming:
                self.buffer_manager.add_candle(candle)
