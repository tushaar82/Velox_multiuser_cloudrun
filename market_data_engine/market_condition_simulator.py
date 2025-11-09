"""
Market Condition Simulator

Simulates different market conditions for strategy testing.
"""
import random
import math
from datetime import datetime, timedelta
from typing import List, Optional
from enum import Enum
import logging

from .models import Tick, Candle

logger = logging.getLogger(__name__)


class MarketCondition(Enum):
    """Market condition types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    QUIET = "quiet"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


class MarketConditionSimulator:
    """
    Simulates different market conditions.
    
    Generates realistic price data matching specific market behaviors.
    """
    
    def __init__(self):
        self.current_condition = MarketCondition.RANGING
        self.base_volatility = 0.01
    
    def set_condition(self, condition: MarketCondition) -> None:
        """Set market condition"""
        self.current_condition = condition
        logger.info(f"Market condition set to: {condition.value}")
    
    def generate_ticks(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: Optional[datetime] = None
    ) -> List[Tick]:
        """
        Generate ticks matching current market condition.
        
        Args:
            symbol: Symbol
            start_price: Starting price
            num_ticks: Number of ticks to generate
            start_time: Starting timestamp
        
        Returns:
            List of ticks
        """
        if start_time is None:
            start_time = datetime.now()
        
        if self.current_condition == MarketCondition.TRENDING_UP:
            return self._generate_trending_up(symbol, start_price, num_ticks, start_time)
        elif self.current_condition == MarketCondition.TRENDING_DOWN:
            return self._generate_trending_down(symbol, start_price, num_ticks, start_time)
        elif self.current_condition == MarketCondition.RANGING:
            return self._generate_ranging(symbol, start_price, num_ticks, start_time)
        elif self.current_condition == MarketCondition.VOLATILE:
            return self._generate_volatile(symbol, start_price, num_ticks, start_time)
        elif self.current_condition == MarketCondition.QUIET:
            return self._generate_quiet(symbol, start_price, num_ticks, start_time)
        elif self.current_condition == MarketCondition.BREAKOUT:
            return self._generate_breakout(symbol, start_price, num_ticks, start_time)
        elif self.current_condition == MarketCondition.REVERSAL:
            return self._generate_reversal(symbol, start_price, num_ticks, start_time)
        else:
            return self._generate_ranging(symbol, start_price, num_ticks, start_time)
    
    def _generate_trending_up(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: datetime
    ) -> List[Tick]:
        """Generate upward trending market"""
        ticks = []
        current_price = start_price
        current_time = start_time
        
        # Strong upward trend with occasional pullbacks
        trend = 0.0005  # 0.05% per tick
        volatility = self.base_volatility * 0.8
        
        for i in range(num_ticks):
            # Occasional pullback
            if random.random() < 0.1:
                change = random.gauss(-trend * 2, volatility)
            else:
                change = random.gauss(trend, volatility)
            
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)
            
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=random.randint(1000, 10000),
                timestamp=current_time
            )
            ticks.append(tick)
            
            current_time += timedelta(seconds=1)
        
        return ticks
    
    def _generate_trending_down(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: datetime
    ) -> List[Tick]:
        """Generate downward trending market"""
        ticks = []
        current_price = start_price
        current_time = start_time
        
        # Strong downward trend with occasional bounces
        trend = -0.0005  # -0.05% per tick
        volatility = self.base_volatility * 0.8
        
        for i in range(num_ticks):
            # Occasional bounce
            if random.random() < 0.1:
                change = random.gauss(-trend * 2, volatility)
            else:
                change = random.gauss(trend, volatility)
            
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)
            
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=random.randint(1000, 10000),
                timestamp=current_time
            )
            ticks.append(tick)
            
            current_time += timedelta(seconds=1)
        
        return ticks
    
    def _generate_ranging(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: datetime
    ) -> List[Tick]:
        """Generate ranging (sideways) market"""
        ticks = []
        current_price = start_price
        current_time = start_time
        
        # Oscillate around starting price
        range_size = start_price * 0.02  # 2% range
        volatility = self.base_volatility
        
        for i in range(num_ticks):
            # Mean reversion
            distance_from_center = current_price - start_price
            mean_reversion = -distance_from_center / range_size * 0.001
            
            change = random.gauss(mean_reversion, volatility)
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)
            
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=random.randint(1000, 10000),
                timestamp=current_time
            )
            ticks.append(tick)
            
            current_time += timedelta(seconds=1)
        
        return ticks
    
    def _generate_volatile(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: datetime
    ) -> List[Tick]:
        """Generate volatile market with large swings"""
        ticks = []
        current_price = start_price
        current_time = start_time
        
        # High volatility with no clear direction
        volatility = self.base_volatility * 3.0
        
        for i in range(num_ticks):
            change = random.gauss(0, volatility)
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)
            
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=random.randint(5000, 50000),  # Higher volume
                timestamp=current_time
            )
            ticks.append(tick)
            
            current_time += timedelta(seconds=1)
        
        return ticks
    
    def _generate_quiet(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: datetime
    ) -> List[Tick]:
        """Generate quiet market with minimal movement"""
        ticks = []
        current_price = start_price
        current_time = start_time
        
        # Very low volatility
        volatility = self.base_volatility * 0.2
        
        for i in range(num_ticks):
            change = random.gauss(0, volatility)
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)
            
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=random.randint(100, 1000),  # Lower volume
                timestamp=current_time
            )
            ticks.append(tick)
            
            current_time += timedelta(seconds=1)
        
        return ticks
    
    def _generate_breakout(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: datetime
    ) -> List[Tick]:
        """Generate breakout pattern"""
        ticks = []
        current_price = start_price
        current_time = start_time
        
        # Consolidation followed by strong move
        breakout_point = num_ticks // 2
        
        for i in range(num_ticks):
            if i < breakout_point:
                # Consolidation phase
                volatility = self.base_volatility * 0.5
                change = random.gauss(0, volatility)
            else:
                # Breakout phase
                volatility = self.base_volatility * 1.5
                trend = 0.001  # Strong upward move
                change = random.gauss(trend, volatility)
            
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)
            
            # Higher volume during breakout
            volume = random.randint(1000, 10000) if i < breakout_point else random.randint(10000, 50000)
            
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=volume,
                timestamp=current_time
            )
            ticks.append(tick)
            
            current_time += timedelta(seconds=1)
        
        return ticks
    
    def _generate_reversal(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        start_time: datetime
    ) -> List[Tick]:
        """Generate trend reversal pattern"""
        ticks = []
        current_price = start_price
        current_time = start_time
        
        # Downtrend followed by uptrend
        reversal_point = num_ticks // 2
        
        for i in range(num_ticks):
            if i < reversal_point:
                # Downtrend
                trend = -0.0003
                volatility = self.base_volatility * 0.8
            else:
                # Uptrend after reversal
                trend = 0.0005
                volatility = self.base_volatility * 1.2
            
            change = random.gauss(trend, volatility)
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)
            
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=random.randint(1000, 10000),
                timestamp=current_time
            )
            ticks.append(tick)
            
            current_time += timedelta(seconds=1)
        
        return ticks
    
    def get_condition_description(self, condition: MarketCondition) -> str:
        """Get description of market condition"""
        descriptions = {
            MarketCondition.TRENDING_UP: "Strong upward trend with occasional pullbacks",
            MarketCondition.TRENDING_DOWN: "Strong downward trend with occasional bounces",
            MarketCondition.RANGING: "Sideways movement within a range",
            MarketCondition.VOLATILE: "High volatility with large price swings",
            MarketCondition.QUIET: "Low volatility with minimal movement",
            MarketCondition.BREAKOUT: "Consolidation followed by strong directional move",
            MarketCondition.REVERSAL: "Trend reversal from down to up"
        }
        return descriptions.get(condition, "Unknown condition")
