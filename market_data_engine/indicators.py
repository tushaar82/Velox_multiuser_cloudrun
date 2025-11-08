"""
Technical Indicators

Implements various technical indicators for trading strategies.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
import pandas as pd

from .models import Candle, IndicatorValue


class IIndicator(ABC):
    """Interface for indicator plugins"""
    
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.validate_params()
    
    @abstractmethod
    def validate_params(self) -> None:
        """Validate indicator parameters"""
        pass
    
    @abstractmethod
    def calculate(self, candles: List[Candle]) -> Optional[IndicatorValue]:
        """
        Calculate indicator value from candles.
        
        Returns None if not enough data to calculate.
        """
        pass
    
    @abstractmethod
    def get_required_candles(self) -> int:
        """Return minimum number of candles required for calculation"""
        pass


class SMAIndicator(IIndicator):
    """Simple Moving Average indicator"""
    
    def validate_params(self) -> None:
        if 'period' not in self.params:
            raise ValueError("SMA requires 'period' parameter")
        if self.params['period'] < 1:
            raise ValueError("SMA period must be >= 1")
    
    def get_required_candles(self) -> int:
        return self.params['period']
    
    def calculate(self, candles: List[Candle]) -> Optional[IndicatorValue]:
        period = self.params['period']
        
        if len(candles) < period:
            return None
        
        # Get closing prices
        closes = [c.close for c in candles[-period:]]
        sma_value = sum(closes) / period
        
        return IndicatorValue(
            symbol=candles[-1].symbol,
            timeframe=candles[-1].timeframe,
            indicator_type='SMA',
            value=sma_value,
            timestamp=candles[-1].timestamp,
            params=self.params
        )


class EMAIndicator(IIndicator):
    """Exponential Moving Average indicator"""
    
    def validate_params(self) -> None:
        if 'period' not in self.params:
            raise ValueError("EMA requires 'period' parameter")
        if self.params['period'] < 1:
            raise ValueError("EMA period must be >= 1")
    
    def get_required_candles(self) -> int:
        # Need more candles for EMA to stabilize
        return self.params['period'] * 2
    
    def calculate(self, candles: List[Candle]) -> Optional[IndicatorValue]:
        period = self.params['period']
        
        if len(candles) < period:
            return None
        
        # Get closing prices
        closes = [c.close for c in candles]
        
        # Calculate EMA using pandas for efficiency
        df = pd.DataFrame({'close': closes})
        ema_series = df['close'].ewm(span=period, adjust=False).mean()
        ema_value = ema_series.iloc[-1]
        
        return IndicatorValue(
            symbol=candles[-1].symbol,
            timeframe=candles[-1].timeframe,
            indicator_type='EMA',
            value=float(ema_value),
            timestamp=candles[-1].timestamp,
            params=self.params
        )


class RSIIndicator(IIndicator):
    """Relative Strength Index indicator"""
    
    def validate_params(self) -> None:
        if 'period' not in self.params:
            raise ValueError("RSI requires 'period' parameter")
        if self.params['period'] < 2:
            raise ValueError("RSI period must be >= 2")
    
    def get_required_candles(self) -> int:
        return self.params['period'] + 1
    
    def calculate(self, candles: List[Candle]) -> Optional[IndicatorValue]:
        period = self.params['period']
        
        if len(candles) < period + 1:
            return None
        
        # Get closing prices
        closes = [c.close for c in candles]
        
        # Calculate price changes
        deltas = np.diff(closes)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gains and losses
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        # Calculate RSI
        if avg_loss == 0:
            rsi_value = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100 - (100 / (1 + rs))
        
        return IndicatorValue(
            symbol=candles[-1].symbol,
            timeframe=candles[-1].timeframe,
            indicator_type='RSI',
            value=float(rsi_value),
            timestamp=candles[-1].timestamp,
            params=self.params
        )


class MACDIndicator(IIndicator):
    """Moving Average Convergence Divergence indicator"""
    
    def validate_params(self) -> None:
        required = ['fast_period', 'slow_period', 'signal_period']
        for param in required:
            if param not in self.params:
                raise ValueError(f"MACD requires '{param}' parameter")
        
        if self.params['fast_period'] >= self.params['slow_period']:
            raise ValueError("MACD fast_period must be < slow_period")
    
    def get_required_candles(self) -> int:
        return self.params['slow_period'] + self.params['signal_period']
    
    def calculate(self, candles: List[Candle]) -> Optional[IndicatorValue]:
        fast_period = self.params['fast_period']
        slow_period = self.params['slow_period']
        signal_period = self.params['signal_period']
        
        required = slow_period + signal_period
        if len(candles) < required:
            return None
        
        # Get closing prices
        closes = [c.close for c in candles]
        df = pd.DataFrame({'close': closes})
        
        # Calculate EMAs
        fast_ema = df['close'].ewm(span=fast_period, adjust=False).mean()
        slow_ema = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return IndicatorValue(
            symbol=candles[-1].symbol,
            timeframe=candles[-1].timeframe,
            indicator_type='MACD',
            value={
                'macd': float(macd_line.iloc[-1]),
                'signal': float(signal_line.iloc[-1]),
                'histogram': float(histogram.iloc[-1])
            },
            timestamp=candles[-1].timestamp,
            params=self.params
        )


class BollingerBandsIndicator(IIndicator):
    """Bollinger Bands indicator"""
    
    def validate_params(self) -> None:
        if 'period' not in self.params:
            raise ValueError("Bollinger Bands requires 'period' parameter")
        if 'std_dev' not in self.params:
            raise ValueError("Bollinger Bands requires 'std_dev' parameter")
        if self.params['period'] < 2:
            raise ValueError("Bollinger Bands period must be >= 2")
    
    def get_required_candles(self) -> int:
        return self.params['period']
    
    def calculate(self, candles: List[Candle]) -> Optional[IndicatorValue]:
        period = self.params['period']
        std_dev = self.params['std_dev']
        
        if len(candles) < period:
            return None
        
        # Get closing prices
        closes = [c.close for c in candles[-period:]]
        
        # Calculate middle band (SMA)
        middle_band = sum(closes) / period
        
        # Calculate standard deviation
        variance = sum((x - middle_band) ** 2 for x in closes) / period
        std = variance ** 0.5
        
        # Calculate upper and lower bands
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        
        return IndicatorValue(
            symbol=candles[-1].symbol,
            timeframe=candles[-1].timeframe,
            indicator_type='BB',
            value={
                'upper': float(upper_band),
                'middle': float(middle_band),
                'lower': float(lower_band)
            },
            timestamp=candles[-1].timestamp,
            params=self.params
        )


class IndicatorEngine:
    """Manages indicator instances and calculations"""
    
    # Registry of available indicators
    INDICATORS = {
        'SMA': SMAIndicator,
        'EMA': EMAIndicator,
        'RSI': RSIIndicator,
        'MACD': MACDIndicator,
        'BB': BollingerBandsIndicator
    }
    
    def __init__(self, redis_storage):
        self.redis = redis_storage
        self.indicator_instances: Dict[str, IIndicator] = {}
    
    def _get_indicator_key(
        self,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        params: Dict[str, Any]
    ) -> str:
        """Generate unique key for indicator instance"""
        params_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{symbol}:{timeframe}:{indicator_type}:{params_str}"
    
    def get_indicator(
        self,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        params: Dict[str, Any]
    ) -> IIndicator:
        """Get or create indicator instance"""
        key = self._get_indicator_key(symbol, timeframe, indicator_type, params)
        
        if key not in self.indicator_instances:
            if indicator_type not in self.INDICATORS:
                raise ValueError(f"Unknown indicator type: {indicator_type}")
            
            indicator_class = self.INDICATORS[indicator_type]
            self.indicator_instances[key] = indicator_class(params)
        
        return self.indicator_instances[key]
    
    def calculate_indicator(
        self,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        params: Dict[str, Any],
        candles: List[Candle],
        use_cache: bool = True
    ) -> Optional[IndicatorValue]:
        """
        Calculate indicator value with optional caching.
        
        Args:
            symbol: Symbol to calculate for
            timeframe: Timeframe to calculate for
            indicator_type: Type of indicator (SMA, EMA, RSI, MACD, BB)
            params: Indicator parameters
            candles: Historical candles for calculation
            use_cache: Whether to use cached values
        
        Returns:
            IndicatorValue or None if not enough data
        """
        # Check cache first
        if use_cache:
            cached = self.redis.get_cached_indicator(symbol, timeframe, indicator_type, params)
            if cached:
                return cached
        
        # Get indicator instance
        indicator = self.get_indicator(symbol, timeframe, indicator_type, params)
        
        # Calculate
        result = indicator.calculate(candles)
        
        # Cache result
        if result and use_cache:
            self.redis.cache_indicator(result, ttl=300)  # 5 minute cache
        
        return result
    
    def calculate_multiple_indicators(
        self,
        symbol: str,
        timeframe: str,
        indicator_configs: List[Dict[str, Any]],
        candles: List[Candle]
    ) -> Dict[str, Optional[IndicatorValue]]:
        """
        Calculate multiple indicators at once.
        
        Args:
            symbol: Symbol to calculate for
            timeframe: Timeframe to calculate for
            indicator_configs: List of dicts with 'type' and 'params' keys
            candles: Historical candles for calculation
        
        Returns:
            Dictionary mapping indicator keys to values
        """
        results = {}
        
        for config in indicator_configs:
            indicator_type = config['type']
            params = config.get('params', {})
            
            key = self._get_indicator_key(symbol, timeframe, indicator_type, params)
            results[key] = self.calculate_indicator(
                symbol, timeframe, indicator_type, params, candles
            )
        
        return results
    
    @staticmethod
    def get_available_indicators() -> List[str]:
        """Get list of available indicator types"""
        return list(IndicatorEngine.INDICATORS.keys())
