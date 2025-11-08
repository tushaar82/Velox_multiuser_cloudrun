"""
Multi-Timeframe Data Provider

Aggregates market data from multiple timeframes and provides synchronized data
to strategies for analysis.
"""

import logging
from typing import Dict, List, Optional, Protocol
from datetime import datetime
from redis import Redis

from strategy_workers.strategy_interface import (
    MultiTimeframeData, TimeframeData, Candle, IndicatorValue
)

logger = logging.getLogger(__name__)


class CandleStorage(Protocol):
    """Protocol for candle storage interface"""
    def get_recent_candles(self, symbol: str, timeframe: str, count: int) -> List[Candle]:
        """Get recent candles from storage"""
        ...


class IndicatorCalculator(Protocol):
    """Protocol for indicator calculator interface"""
    def calculate(self, indicator_type: str, candles: List[Candle], **params) -> any:
        """Calculate indicator value"""
        ...


class MultiTimeframeDataProvider:
    """Provides synchronized multi-timeframe market data to strategies"""
    
    def __init__(self, redis_client: Redis, candle_storage: CandleStorage,
                 indicator_calculator: IndicatorCalculator):
        """
        Initialize data provider.
        
        Args:
            redis_client: Redis connection for forming candles
            candle_storage: Storage for historical candles
            indicator_calculator: Calculator for indicators
        """
        self.redis = redis_client
        self.candle_storage = candle_storage
        self.indicator_calculator = indicator_calculator
    
    def get_data(self, symbol: str, timeframes: List[str], 
                 indicator_configs: Optional[Dict[str, List[Dict]]] = None) -> MultiTimeframeData:
        """
        Get synchronized multi-timeframe data for a symbol.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to fetch (e.g., ['1m', '5m', '15m'])
            indicator_configs: Optional dict of {timeframe: [indicator_configs]}
            
        Returns:
            MultiTimeframeData with all requested timeframes
        """
        timeframe_data_dict = {}
        current_price = 0.0
        
        for timeframe in timeframes:
            tf_data = self._get_timeframe_data(symbol, timeframe, indicator_configs)
            timeframe_data_dict[timeframe] = tf_data
            
            # Get current price from forming candle or latest historical candle
            if tf_data.forming_candle:
                current_price = tf_data.forming_candle.close
            elif tf_data.historical_candles:
                current_price = tf_data.historical_candles[-1].close
        
        return MultiTimeframeData(
            symbol=symbol,
            timeframes=timeframe_data_dict,
            current_price=current_price,
            timestamp=datetime.utcnow()
        )
    
    def _get_timeframe_data(self, symbol: str, timeframe: str,
                           indicator_configs: Optional[Dict[str, List[Dict]]]) -> TimeframeData:
        """
        Get data for a single timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1m', '5m')
            indicator_configs: Optional indicator configurations
            
        Returns:
            TimeframeData for the timeframe
        """
        # Get historical candles from storage
        historical_candles = self.candle_storage.get_recent_candles(
            symbol=symbol,
            timeframe=timeframe,
            count=500  # Keep last 500 candles in memory
        )
        
        # Get forming candle from Redis
        forming_candle = self._get_forming_candle(symbol, timeframe)
        
        # Calculate indicators if requested
        indicators = {}
        if indicator_configs and timeframe in indicator_configs:
            indicators = self._calculate_indicators(
                symbol, timeframe, historical_candles, 
                forming_candle, indicator_configs[timeframe]
            )
        
        return TimeframeData(
            historical_candles=historical_candles,
            forming_candle=forming_candle,
            indicators=indicators
        )
    
    def _get_forming_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """
        Get forming candle from Redis.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            Forming candle if exists, None otherwise
        """
        try:
            import json
            key = f"forming_candle:{symbol}:{timeframe}"
            data = self.redis.get(key)
            
            if not data:
                return None
            
            candle_dict = json.loads(data)
            
            return Candle(
                symbol=candle_dict['symbol'],
                timeframe=candle_dict['timeframe'],
                open=candle_dict['open'],
                high=candle_dict['high'],
                low=candle_dict['low'],
                close=candle_dict['close'],
                volume=candle_dict['volume'],
                timestamp=datetime.fromisoformat(candle_dict['timestamp']),
                is_forming=True
            )
            
        except Exception as e:
            logger.error(f"Failed to get forming candle for {symbol} {timeframe}: {e}")
            return None
    
    def _calculate_indicators(self, symbol: str, timeframe: str,
                            historical_candles: List[Candle],
                            forming_candle: Optional[Candle],
                            configs: List[Dict]) -> Dict[str, IndicatorValue]:
        """
        Calculate indicators for the timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            historical_candles: Historical candles
            forming_candle: Current forming candle
            configs: List of indicator configurations
            
        Returns:
            Dict of {indicator_name: IndicatorValue}
        """
        indicators = {}
        
        # Combine historical and forming candle for calculation
        all_candles = historical_candles.copy()
        if forming_candle:
            all_candles.append(forming_candle)
        
        if not all_candles:
            return indicators
        
        for config in configs:
            try:
                indicator_type = config['type']
                indicator_name = config.get('name', indicator_type)
                params = config.get('params', {})
                
                # Calculate indicator
                value = self.indicator_calculator.calculate(
                    indicator_type=indicator_type,
                    candles=all_candles,
                    **params
                )
                
                indicators[indicator_name] = IndicatorValue(
                    symbol=symbol,
                    timeframe=timeframe,
                    indicator_type=indicator_type,
                    value=value,
                    timestamp=datetime.utcnow()
                )
                
            except Exception as e:
                logger.error(f"Failed to calculate indicator {config}: {e}")
        
        return indicators
    
    def ensure_data_consistency(self, data: MultiTimeframeData) -> bool:
        """
        Verify that multi-timeframe data is synchronized and consistent.
        
        Args:
            data: Multi-timeframe data to validate
            
        Returns:
            True if data is consistent, False otherwise
        """
        if not data.timeframes:
            return False
        
        # Check that all timeframes have data
        for timeframe, tf_data in data.timeframes.items():
            if not tf_data.historical_candles and not tf_data.forming_candle:
                logger.warning(f"No data for timeframe {timeframe}")
                return False
        
        # Check timestamp alignment (all data should be recent)
        max_age_seconds = 60  # Data should be within last minute
        current_time = datetime.utcnow()
        
        for timeframe, tf_data in data.timeframes.items():
            latest_candle = tf_data.forming_candle or (
                tf_data.historical_candles[-1] if tf_data.historical_candles else None
            )
            
            if latest_candle:
                age = (current_time - latest_candle.timestamp).total_seconds()
                if age > max_age_seconds:
                    logger.warning(f"Stale data for {timeframe}: {age}s old")
                    return False
        
        return True
    
    def get_indicator_value(self, data: MultiTimeframeData, timeframe: str,
                           indicator_name: str) -> Optional[any]:
        """
        Helper to extract indicator value from multi-timeframe data.
        
        Args:
            data: Multi-timeframe data
            timeframe: Timeframe to get indicator from
            indicator_name: Name of the indicator
            
        Returns:
            Indicator value if found, None otherwise
        """
        if timeframe not in data.timeframes:
            return None
        
        tf_data = data.timeframes[timeframe]
        if indicator_name not in tf_data.indicators:
            return None
        
        return tf_data.indicators[indicator_name].value
    
    def get_latest_candle(self, data: MultiTimeframeData, timeframe: str) -> Optional[Candle]:
        """
        Get the latest candle (forming or most recent historical) for a timeframe.
        
        Args:
            data: Multi-timeframe data
            timeframe: Timeframe to get candle from
            
        Returns:
            Latest candle if found, None otherwise
        """
        if timeframe not in data.timeframes:
            return None
        
        tf_data = data.timeframes[timeframe]
        
        # Return forming candle if available, otherwise latest historical
        if tf_data.forming_candle:
            return tf_data.forming_candle
        elif tf_data.historical_candles:
            return tf_data.historical_candles[-1]
        
        return None
