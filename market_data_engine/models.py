"""
Market Data Models

Data classes for Tick, Candle, and IndicatorValue used throughout the market data engine.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Union, List, Optional, Dict, Any


@dataclass
class Tick:
    """Represents a single price update from the market feed"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tick':
        """Create from dictionary"""
        return cls(
            symbol=data['symbol'],
            price=data['price'],
            volume=data['volume'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )


@dataclass
class Candle:
    """Represents a candlestick for a specific timeframe"""
    symbol: str
    timeframe: str  # '1m', '3m', '5m', '15m', '30m', '1h', '1d'
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    is_forming: bool = True  # True if candle is still being formed
    
    def update_with_tick(self, tick: Tick) -> None:
        """Update candle with new tick data"""
        self.close = tick.price
        self.high = max(self.high, tick.price)
        self.low = min(self.low, tick.price)
        self.volume += tick.volume
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat(),
            'is_forming': self.is_forming
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Candle':
        """Create from dictionary"""
        return cls(
            symbol=data['symbol'],
            timeframe=data['timeframe'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            is_forming=data.get('is_forming', False)
        )
    
    @classmethod
    def from_tick(cls, tick: Tick, timeframe: str, candle_timestamp: datetime) -> 'Candle':
        """Create a new candle from the first tick"""
        return cls(
            symbol=tick.symbol,
            timeframe=timeframe,
            open=tick.price,
            high=tick.price,
            low=tick.price,
            close=tick.price,
            volume=tick.volume,
            timestamp=candle_timestamp,
            is_forming=True
        )


@dataclass
class IndicatorValue:
    """Represents a calculated indicator value"""
    symbol: str
    timeframe: str
    indicator_type: str  # 'SMA', 'EMA', 'RSI', 'MACD', 'BB'
    value: Union[float, List[float], Dict[str, float]]  # Single value or multiple (e.g., MACD has multiple lines)
    timestamp: datetime
    params: Dict[str, Any] = field(default_factory=dict)  # Indicator parameters (e.g., period=20)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'indicator_type': self.indicator_type,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'params': self.params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndicatorValue':
        """Create from dictionary"""
        return cls(
            symbol=data['symbol'],
            timeframe=data['timeframe'],
            indicator_type=data['indicator_type'],
            value=data['value'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            params=data.get('params', {})
        )


@dataclass
class CandleBuffer:
    """Manages a buffer of recent candles for a symbol/timeframe"""
    symbol: str
    timeframe: str
    max_size: int = 500
    candles: List[Candle] = field(default_factory=list)
    
    def add_candle(self, candle: Candle) -> None:
        """Add a completed candle to the buffer"""
        self.candles.append(candle)
        # Keep only the last max_size candles
        if len(self.candles) > self.max_size:
            self.candles = self.candles[-self.max_size:]
    
    def get_recent_candles(self, count: int) -> List[Candle]:
        """Get the most recent N candles"""
        return self.candles[-count:] if count <= len(self.candles) else self.candles
    
    def get_all_candles(self) -> List[Candle]:
        """Get all candles in the buffer"""
        return self.candles.copy()
    
    def clear(self) -> None:
        """Clear all candles from the buffer"""
        self.candles.clear()
