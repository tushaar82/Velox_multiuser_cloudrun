"""
Historical Data Loader

Loads historical market data from InfluxDB for backtesting.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import logging

from market_data_engine.storage import InfluxDBStorage
from market_data_engine.models import Candle
from shared.models.backtest import BacktestConfig

logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """Loads and validates historical market data for backtesting"""
    
    def __init__(self):
        self.storage = InfluxDBStorage()
        self.storage.connect()
    
    def close(self) -> None:
        """Close storage connections"""
        self.storage.disconnect()
    
    def load_data(self, config: BacktestConfig) -> Dict[str, Dict[str, List[Candle]]]:
        """
        Load historical candles for all symbols and timeframes.
        
        Returns:
            Dict[symbol][timeframe] -> List[Candle]
        """
        logger.info(
            f"Loading historical data for {len(config.symbols)} symbols, "
            f"{len(config.timeframes)} timeframes from {config.start_date} to {config.end_date}"
        )
        
        data = defaultdict(dict)
        
        for symbol in config.symbols:
            for timeframe in config.timeframes:
                candles = self._load_symbol_timeframe(
                    symbol,
                    timeframe,
                    config.start_date,
                    config.end_date
                )
                data[symbol][timeframe] = candles
                logger.info(f"Loaded {len(candles)} candles for {symbol} {timeframe}")
        
        # Validate data completeness
        self._validate_data(data, config)
        
        return dict(data)
    
    def _load_symbol_timeframe(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Candle]:
        """Load candles for a single symbol and timeframe"""
        try:
            candles = self.storage.get_historical_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_date,
                end_time=end_date
            )
            
            # Sort by timestamp to ensure chronological order
            candles.sort(key=lambda c: c.timestamp)
            
            return candles
        except Exception as e:
            logger.error(f"Error loading data for {symbol} {timeframe}: {e}")
            raise
    
    def _validate_data(self, data: Dict[str, Dict[str, List[Candle]]], config: BacktestConfig) -> None:
        """Validate that loaded data is complete and consistent"""
        errors = []
        warnings = []
        
        # Check that all symbols have data
        for symbol in config.symbols:
            if symbol not in data or not data[symbol]:
                errors.append(f"No data found for symbol: {symbol}")
                continue
            
            # Check that all timeframes have data
            for timeframe in config.timeframes:
                if timeframe not in data[symbol]:
                    errors.append(f"No data found for {symbol} {timeframe}")
                    continue
                
                candles = data[symbol][timeframe]
                if not candles:
                    errors.append(f"Empty candle list for {symbol} {timeframe}")
                    continue
                
                # Check for gaps in data
                gaps = self._detect_gaps(candles, timeframe)
                if gaps:
                    warnings.append(
                        f"Found {len(gaps)} gaps in {symbol} {timeframe} data"
                    )
                
                # Check date range coverage
                first_candle = candles[0]
                last_candle = candles[-1]
                
                if first_candle.timestamp > config.start_date + timedelta(days=1):
                    warnings.append(
                        f"{symbol} {timeframe} data starts at {first_candle.timestamp}, "
                        f"requested start was {config.start_date}"
                    )
                
                if last_candle.timestamp < config.end_date - timedelta(days=1):
                    warnings.append(
                        f"{symbol} {timeframe} data ends at {last_candle.timestamp}, "
                        f"requested end was {config.end_date}"
                    )
        
        # Log warnings
        for warning in warnings:
            logger.warning(warning)
        
        # Raise errors if any
        if errors:
            error_msg = "Data validation failed:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _detect_gaps(self, candles: List[Candle], timeframe: str) -> List[tuple]:
        """
        Detect gaps in candle data.
        
        Returns:
            List of (start_time, end_time) tuples representing gaps
        """
        if len(candles) < 2:
            return []
        
        # Get expected interval in seconds
        interval_seconds = self._get_timeframe_seconds(timeframe)
        
        gaps = []
        for i in range(len(candles) - 1):
            current = candles[i]
            next_candle = candles[i + 1]
            
            expected_next = current.timestamp + timedelta(seconds=interval_seconds)
            actual_next = next_candle.timestamp
            
            # Allow some tolerance (e.g., 10% of interval)
            tolerance = timedelta(seconds=interval_seconds * 0.1)
            
            if actual_next > expected_next + tolerance:
                gaps.append((current.timestamp, next_candle.timestamp))
        
        return gaps
    
    def _get_timeframe_seconds(self, timeframe: str) -> int:
        """Convert timeframe string to seconds"""
        timeframe_map = {
            '1m': 60,
            '3m': 180,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '2h': 7200,
            '4h': 14400,
            '1d': 86400
        }
        
        if timeframe not in timeframe_map:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        
        return timeframe_map[timeframe]
    
    def get_data_summary(self, data: Dict[str, Dict[str, List[Candle]]]) -> Dict:
        """Get summary statistics about loaded data"""
        summary = {
            'symbols': {},
            'total_candles': 0
        }
        
        for symbol, timeframes in data.items():
            symbol_summary = {
                'timeframes': {},
                'total_candles': 0
            }
            
            for timeframe, candles in timeframes.items():
                if candles:
                    symbol_summary['timeframes'][timeframe] = {
                        'count': len(candles),
                        'start': candles[0].timestamp.isoformat(),
                        'end': candles[-1].timestamp.isoformat()
                    }
                    symbol_summary['total_candles'] += len(candles)
                    summary['total_candles'] += len(candles)
            
            summary['symbols'][symbol] = symbol_summary
        
        return summary


class MultiTimeframeDataSynchronizer:
    """Synchronizes data across multiple timeframes for backtesting"""
    
    def __init__(self, data: Dict[str, Dict[str, List[Candle]]]):
        self.data = data
        self.indices = defaultdict(lambda: defaultdict(int))
    
    def get_candles_at_time(
        self,
        symbol: str,
        timeframe: str,
        current_time: datetime,
        lookback: int = 100
    ) -> List[Candle]:
        """
        Get historical candles up to current_time for a symbol/timeframe.
        
        Args:
            symbol: Symbol to get candles for
            timeframe: Timeframe to get candles for
            current_time: Current simulation time
            lookback: Number of historical candles to return
        
        Returns:
            List of candles up to current_time (most recent first)
        """
        if symbol not in self.data or timeframe not in self.data[symbol]:
            return []
        
        candles = self.data[symbol][timeframe]
        
        # Find all candles up to current_time
        valid_candles = [c for c in candles if c.timestamp <= current_time]
        
        # Return most recent 'lookback' candles
        return valid_candles[-lookback:] if valid_candles else []
    
    def get_next_candle_time(self, symbol: str, timeframe: str, current_time: datetime) -> Optional[datetime]:
        """Get the timestamp of the next candle after current_time"""
        if symbol not in self.data or timeframe not in self.data[symbol]:
            return None
        
        candles = self.data[symbol][timeframe]
        
        for candle in candles:
            if candle.timestamp > current_time:
                return candle.timestamp
        
        return None
    
    def get_all_timestamps(self) -> List[datetime]:
        """Get all unique timestamps across all symbols and timeframes, sorted"""
        timestamps = set()
        
        for symbol_data in self.data.values():
            for candles in symbol_data.values():
                for candle in candles:
                    timestamps.add(candle.timestamp)
        
        return sorted(timestamps)
    
    def get_price_at_time(self, symbol: str, current_time: datetime) -> Optional[float]:
        """Get the most recent price for a symbol at current_time"""
        # Try to get from smallest timeframe first for most accurate price
        timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '1d']
        
        for timeframe in timeframes:
            if symbol in self.data and timeframe in self.data[symbol]:
                candles = self.get_candles_at_time(symbol, timeframe, current_time, lookback=1)
                if candles:
                    return candles[-1].close
        
        return None
