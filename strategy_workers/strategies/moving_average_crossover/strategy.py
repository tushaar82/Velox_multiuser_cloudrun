"""
Moving Average Crossover Strategy Implementation
"""

import logging
from typing import Optional, List
from datetime import datetime

from strategy_workers.strategy_interface import (
    IStrategy, StrategyConfig, MultiTimeframeData, Candle, Signal
)

logger = logging.getLogger(__name__)


class MovingAverageCrossoverStrategy(IStrategy):
    """
    Moving Average Crossover Strategy
    
    Entry Logic:
    - Long: Fast MA crosses above Slow MA
    - Optional: Confirm with higher timeframe trend
    
    Exit Logic:
    - Fast MA crosses below Slow MA
    """
    
    def __init__(self):
        self.config: Optional[StrategyConfig] = None
        self.fast_period: int = 10
        self.slow_period: int = 20
        self.ma_type: str = "SMA"
        self.confirmation_timeframe: Optional[str] = None
        self.quantity: int = 1
        self.position_open: bool = False
        self.last_fast_ma: Optional[float] = None
        self.last_slow_ma: Optional[float] = None
    
    def initialize(self, config: StrategyConfig) -> None:
        """Initialize strategy with configuration"""
        self.config = config
        
        # Extract parameters
        params = config.parameters
        self.fast_period = params.get('fast_period', 10)
        self.slow_period = params.get('slow_period', 20)
        self.ma_type = params.get('ma_type', 'SMA')
        self.confirmation_timeframe = params.get('confirmation_timeframe')
        self.quantity = params.get('quantity', 1)
        
        # Validate parameters
        if self.fast_period >= self.slow_period:
            raise ValueError("Fast period must be less than slow period")
        
        logger.info(f"Initialized MA Crossover: fast={self.fast_period}, slow={self.slow_period}, type={self.ma_type}")
    
    def on_tick(self, data: MultiTimeframeData) -> Optional[Signal]:
        """
        Called on every tick.
        
        For MA crossover, we don't need tick-by-tick updates.
        Return None to skip processing.
        """
        return None
    
    def on_candle_complete(self, timeframe: str, candle: Candle, 
                          data: MultiTimeframeData) -> Optional[Signal]:
        """
        Called when a candle completes.
        
        Check for MA crossover and generate signals.
        """
        try:
            # Only process the primary timeframe (first in config)
            if timeframe != self.config.timeframes[0]:
                return None
            
            # Get timeframe data
            if timeframe not in data.timeframes:
                return None
            
            tf_data = data.timeframes[timeframe]
            
            # Need enough historical data
            if len(tf_data.historical_candles) < self.slow_period:
                logger.debug(f"Not enough candles: {len(tf_data.historical_candles)} < {self.slow_period}")
                return None
            
            # Calculate moving averages
            fast_ma = self._calculate_ma(tf_data.historical_candles, self.fast_period)
            slow_ma = self._calculate_ma(tf_data.historical_candles, self.slow_period)
            
            if fast_ma is None or slow_ma is None:
                return None
            
            # Check for crossover
            signal = None
            
            if self.last_fast_ma is not None and self.last_slow_ma is not None:
                # Bullish crossover: fast crosses above slow
                if self.last_fast_ma <= self.last_slow_ma and fast_ma > slow_ma:
                    if not self.position_open:
                        # Check confirmation if required
                        if self._check_confirmation(data):
                            signal = self._create_entry_signal(data.symbol, fast_ma, slow_ma)
                            if signal:
                                self.position_open = True
                                logger.info(f"Bullish crossover detected: fast={fast_ma:.2f}, slow={slow_ma:.2f}")
                
                # Bearish crossover: fast crosses below slow
                elif self.last_fast_ma >= self.last_slow_ma and fast_ma < slow_ma:
                    if self.position_open:
                        signal = self._create_exit_signal(data.symbol, fast_ma, slow_ma)
                        if signal:
                            self.position_open = False
                            logger.info(f"Bearish crossover detected: fast={fast_ma:.2f}, slow={slow_ma:.2f}")
            
            # Update last values
            self.last_fast_ma = fast_ma
            self.last_slow_ma = slow_ma
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in on_candle_complete: {e}")
            return None
    
    def cleanup(self) -> None:
        """Cleanup when strategy stops"""
        logger.info("Cleaning up MA Crossover strategy")
        self.position_open = False
        self.last_fast_ma = None
        self.last_slow_ma = None
    
    def get_state(self) -> dict:
        """Get strategy state for persistence"""
        return {
            'position_open': self.position_open,
            'last_fast_ma': self.last_fast_ma,
            'last_slow_ma': self.last_slow_ma
        }
    
    def set_state(self, state: dict) -> None:
        """Restore strategy state"""
        self.position_open = state.get('position_open', False)
        self.last_fast_ma = state.get('last_fast_ma')
        self.last_slow_ma = state.get('last_slow_ma')
    
    def _calculate_ma(self, candles: List[Candle], period: int) -> Optional[float]:
        """
        Calculate moving average.
        
        Args:
            candles: List of candles
            period: MA period
            
        Returns:
            MA value or None
        """
        if len(candles) < period:
            return None
        
        # Use last 'period' candles
        recent_candles = candles[-period:]
        
        if self.ma_type == "SMA":
            # Simple Moving Average
            total = sum(c.close for c in recent_candles)
            return total / period
        
        elif self.ma_type == "EMA":
            # Exponential Moving Average
            multiplier = 2 / (period + 1)
            ema = recent_candles[0].close
            
            for candle in recent_candles[1:]:
                ema = (candle.close - ema) * multiplier + ema
            
            return ema
        
        return None
    
    def _check_confirmation(self, data: MultiTimeframeData) -> bool:
        """
        Check higher timeframe confirmation if configured.
        
        Args:
            data: Multi-timeframe data
            
        Returns:
            True if confirmed or no confirmation required
        """
        if not self.confirmation_timeframe:
            return True
        
        if self.confirmation_timeframe not in data.timeframes:
            logger.warning(f"Confirmation timeframe {self.confirmation_timeframe} not available")
            return True  # Don't block if confirmation data unavailable
        
        tf_data = data.timeframes[self.confirmation_timeframe]
        
        if len(tf_data.historical_candles) < self.slow_period:
            return True  # Not enough data for confirmation
        
        # Calculate MAs on higher timeframe
        fast_ma = self._calculate_ma(tf_data.historical_candles, self.fast_period)
        slow_ma = self._calculate_ma(tf_data.historical_candles, self.slow_period)
        
        if fast_ma is None or slow_ma is None:
            return True
        
        # Confirm that higher timeframe is also bullish
        is_bullish = fast_ma > slow_ma
        
        logger.debug(f"Higher TF confirmation: fast={fast_ma:.2f}, slow={slow_ma:.2f}, bullish={is_bullish}")
        return is_bullish
    
    def _create_entry_signal(self, symbol: str, fast_ma: float, slow_ma: float) -> Signal:
        """
        Create entry signal.
        
        Args:
            symbol: Trading symbol
            fast_ma: Fast MA value
            slow_ma: Slow MA value
            
        Returns:
            Entry signal
        """
        # Calculate stop loss and take profit if configured
        stop_loss = None
        take_profit = None
        trailing_stop = None
        
        if self.config.risk_management:
            rm = self.config.risk_management
            
            if rm.stop_loss_percentage:
                stop_loss = fast_ma * (1 - rm.stop_loss_percentage / 100)
            
            if rm.take_profit_percentage:
                take_profit = fast_ma * (1 + rm.take_profit_percentage / 100)
            
            if rm.trailing_stop_percentage:
                trailing_stop = rm.trailing_stop_percentage
        
        return Signal(
            type='entry',
            direction='long',
            symbol=symbol,
            quantity=self.quantity,
            order_type='market',
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop_loss=trailing_stop,
            reason=f"MA Crossover: Fast({self.fast_period})={fast_ma:.2f} > Slow({self.slow_period})={slow_ma:.2f}"
        )
    
    def _create_exit_signal(self, symbol: str, fast_ma: float, slow_ma: float) -> Signal:
        """
        Create exit signal.
        
        Args:
            symbol: Trading symbol
            fast_ma: Fast MA value
            slow_ma: Slow MA value
            
        Returns:
            Exit signal
        """
        return Signal(
            type='exit',
            direction='long',
            symbol=symbol,
            quantity=self.quantity,
            order_type='market',
            reason=f"MA Crossover Exit: Fast({self.fast_period})={fast_ma:.2f} < Slow({self.slow_period})={slow_ma:.2f}"
        )
