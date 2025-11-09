"""
Backtest Execution Engine

Executes trading strategies against historical data and tracks performance.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid

from shared.models.backtest import (
    BacktestConfig, BacktestTrade, EquityPoint, BacktestStatus
)
from strategy_workers.strategy_interface import (
    IStrategy, StrategyConfig, MultiTimeframeData, TimeframeData,
    Candle, Signal, IndicatorValue
)
from backtesting_engine.data_loader import MultiTimeframeDataSynchronizer
from market_data_engine.indicators import IndicatorEngine

logger = logging.getLogger(__name__)


@dataclass
class BacktestPosition:
    """Position during backtest"""
    symbol: str
    side: str  # 'long' or 'short'
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop_loss: Optional[float] = None
    highest_price: Optional[float] = None  # For trailing stop
    lowest_price: Optional[float] = None  # For trailing stop


@dataclass
class BacktestOrder:
    """Order during backtest"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    order_type: str  # 'market' or 'limit'
    price: Optional[float]
    timestamp: datetime
    filled: bool = False
    fill_price: Optional[float] = None
    fill_time: Optional[datetime] = None


class BacktestExecutionEngine:
    """Executes backtests with historical data"""
    
    def __init__(self, config: BacktestConfig, strategy: IStrategy,
                 data_sync: MultiTimeframeDataSynchronizer):
        """
        Initialize backtest execution engine.
        
        Args:
            config: Backtest configuration
            strategy: Strategy instance to test
            data_sync: Data synchronizer with loaded historical data
        """
        self.config = config
        self.strategy = strategy
        self.data_sync = data_sync
        self.indicator_calculator = IndicatorCalculator()
        
        # Backtest state
        self.current_time: Optional[datetime] = None
        self.equity: float = config.initial_capital
        self.cash: float = config.initial_capital
        self.positions: Dict[str, BacktestPosition] = {}
        self.pending_orders: List[BacktestOrder] = []
        self.completed_trades: List[BacktestTrade] = []
        self.equity_curve: List[EquityPoint] = []
        
        # Performance tracking
        self.peak_equity: float = config.initial_capital
        self.max_drawdown: float = 0.0
        
        # Initialize strategy
        strategy_config = StrategyConfig(
            strategy_id=config.strategy_id,
            account_id=config.account_id,
            trading_mode='backtest',
            symbols=config.symbols,
            timeframes=config.timeframes,
            parameters=config.strategy_params
        )
        self.strategy.initialize(strategy_config)
    
    def run(self) -> Tuple[List[BacktestTrade], List[EquityPoint]]:
        """
        Execute the backtest.
        
        Returns:
            Tuple of (trades, equity_curve)
        """
        logger.info(f"Starting backtest from {self.config.start_date} to {self.config.end_date}")
        
        # Get all timestamps chronologically
        timestamps = self.data_sync.get_all_timestamps()
        
        if not timestamps:
            raise ValueError("No data available for backtest")
        
        # Filter timestamps to backtest date range
        timestamps = [
            ts for ts in timestamps
            if self.config.start_date <= ts <= self.config.end_date
        ]
        
        logger.info(f"Processing {len(timestamps)} timestamps")
        
        # Iterate through time chronologically
        for i, timestamp in enumerate(timestamps):
            self.current_time = timestamp
            
            # Process pending orders
            self._process_pending_orders()
            
            # Update positions with current prices
            self._update_positions()
            
            # Update equity curve
            self._record_equity_point()
            
            # Get multi-timeframe data at current time
            mtf_data = self._get_multi_timeframe_data(timestamp)
            
            # Check for candle completions and execute strategy
            self._execute_strategy(mtf_data, timestamp)
            
            # Log progress periodically
            if i % 1000 == 0:
                progress = (i / len(timestamps)) * 100
                logger.info(f"Progress: {progress:.1f}% - Equity: ${self.equity:.2f}")
        
        # Close any remaining positions
        self._close_all_positions()
        
        logger.info(f"Backtest complete. Final equity: ${self.equity:.2f}")
        logger.info(f"Total trades: {len(self.completed_trades)}")
        
        return self.completed_trades, self.equity_curve
    
    def _get_multi_timeframe_data(self, timestamp: datetime) -> MultiTimeframeData:
        """Build multi-timeframe data at current timestamp"""
        timeframe_data_dict = {}
        current_price = 0.0
        
        for symbol in self.config.symbols:
            for timeframe in self.config.timeframes:
                # Get historical candles up to current time
                historical_candles = self.data_sync.get_candles_at_time(
                    symbol, timeframe, timestamp, lookback=500
                )
                
                # Calculate indicators
                indicators = self._calculate_indicators(
                    symbol, timeframe, historical_candles
                )
                
                # Create timeframe data
                tf_data = TimeframeData(
                    historical_candles=historical_candles,
                    forming_candle=None,  # No forming candle in backtest
                    indicators=indicators
                )
                
                timeframe_data_dict[timeframe] = tf_data
                
                # Get current price from latest candle
                if historical_candles:
                    current_price = historical_candles[-1].close
        
        # For simplicity, return data for first symbol
        # Multi-symbol backtesting would need more complex handling
        symbol = self.config.symbols[0]
        
        return MultiTimeframeData(
            symbol=symbol,
            timeframes=timeframe_data_dict,
            current_price=current_price,
            timestamp=timestamp
        )
    
    def _calculate_indicators(self, symbol: str, timeframe: str,
                            candles: List[Candle]) -> Dict[str, IndicatorValue]:
        """Calculate indicators for candles"""
        indicators = {}
        
        if not candles:
            return indicators
        
        # Calculate common indicators
        # SMA 20
        try:
            sma_20 = self.indicator_calculator.calculate('SMA', candles, period=20)
            indicators['SMA_20'] = IndicatorValue(
                symbol=symbol,
                timeframe=timeframe,
                indicator_type='SMA',
                value=sma_20,
                timestamp=candles[-1].timestamp
            )
        except Exception as e:
            logger.debug(f"Could not calculate SMA_20: {e}")
        
        # SMA 50
        try:
            sma_50 = self.indicator_calculator.calculate('SMA', candles, period=50)
            indicators['SMA_50'] = IndicatorValue(
                symbol=symbol,
                timeframe=timeframe,
                indicator_type='SMA',
                value=sma_50,
                timestamp=candles[-1].timestamp
            )
        except Exception as e:
            logger.debug(f"Could not calculate SMA_50: {e}")
        
        # RSI
        try:
            rsi = self.indicator_calculator.calculate('RSI', candles, period=14)
            indicators['RSI'] = IndicatorValue(
                symbol=symbol,
                timeframe=timeframe,
                indicator_type='RSI',
                value=rsi,
                timestamp=candles[-1].timestamp
            )
        except Exception as e:
            logger.debug(f"Could not calculate RSI: {e}")
        
        return indicators
    
    def _execute_strategy(self, mtf_data: MultiTimeframeData, timestamp: datetime) -> None:
        """Execute strategy logic at current timestamp"""
        try:
            # Check for candle completions
            for timeframe in self.config.timeframes:
                if timeframe in mtf_data.timeframes:
                    tf_data = mtf_data.timeframes[timeframe]
                    if tf_data.historical_candles:
                        latest_candle = tf_data.historical_candles[-1]
                        
                        # Call on_candle_complete
                        signal = self.strategy.on_candle_complete(
                            timeframe, latest_candle, mtf_data
                        )
                        
                        if signal:
                            self._process_signal(signal, mtf_data.current_price)
        
        except Exception as e:
            logger.error(f"Strategy execution error at {timestamp}: {e}")
    
    def _process_signal(self, signal: Signal, current_price: float) -> None:
        """Process trading signal from strategy"""
        if signal.type == 'entry':
            self._open_position(signal, current_price)
        elif signal.type == 'exit':
            self._close_position(signal.symbol, current_price)
    
    def _open_position(self, signal: Signal, current_price: float) -> None:
        """Open a new position from signal"""
        # Check if we already have a position in this symbol
        if signal.symbol in self.positions:
            logger.debug(f"Already have position in {signal.symbol}, ignoring entry signal")
            return
        
        # Calculate position size based on available cash
        if signal.order_type == 'market':
            entry_price = current_price * (1 + self.config.slippage if signal.direction == 'long' else 1 - self.config.slippage)
        else:
            entry_price = signal.price or current_price
        
        # Check if we have enough cash
        position_cost = entry_price * signal.quantity
        commission = position_cost * self.config.commission
        total_cost = position_cost + commission
        
        if total_cost > self.cash:
            logger.debug(f"Insufficient cash for position: need ${total_cost:.2f}, have ${self.cash:.2f}")
            return
        
        # Create position
        position = BacktestPosition(
            symbol=signal.symbol,
            side=signal.direction,
            quantity=signal.quantity,
            entry_price=entry_price,
            entry_time=self.current_time,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            trailing_stop_loss=signal.trailing_stop_loss,
            highest_price=entry_price if signal.direction == 'long' else None,
            lowest_price=entry_price if signal.direction == 'short' else None
        )
        
        self.positions[signal.symbol] = position
        self.cash -= total_cost
        
        logger.debug(f"Opened {signal.direction} position in {signal.symbol}: {signal.quantity} @ ${entry_price:.2f}")
    
    def _close_position(self, symbol: str, current_price: float) -> None:
        """Close an existing position"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Calculate exit price with slippage
        exit_price = current_price * (1 - self.config.slippage if position.side == 'long' else 1 + self.config.slippage)
        
        # Calculate P&L
        if position.side == 'long':
            pnl = (exit_price - position.entry_price) * position.quantity
        else:  # short
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Subtract commission
        position_value = exit_price * position.quantity
        commission = position_value * self.config.commission
        pnl -= commission
        
        # Calculate holding time
        holding_time = (self.current_time - position.entry_time).total_seconds()
        
        # Create trade record
        trade = BacktestTrade(
            entry_date=position.entry_time,
            exit_date=self.current_time,
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            pnl=pnl,
            pnl_percent=(pnl / (position.entry_price * position.quantity)) * 100,
            commission=commission,
            holding_time_seconds=holding_time
        )
        
        self.completed_trades.append(trade)
        
        # Update cash
        self.cash += position_value - commission
        
        # Remove position
        del self.positions[symbol]
        
        logger.debug(f"Closed {position.side} position in {symbol}: P&L ${pnl:.2f}")
    
    def _update_positions(self) -> None:
        """Update positions with current prices and check stop losses"""
        for symbol, position in list(self.positions.items()):
            current_price = self.data_sync.get_price_at_time(symbol, self.current_time)
            
            if not current_price:
                continue
            
            # Update trailing stop
            if position.trailing_stop_loss:
                if position.side == 'long':
                    if current_price > position.highest_price:
                        position.highest_price = current_price
                        position.stop_loss = current_price * (1 - position.trailing_stop_loss / 100)
                else:  # short
                    if current_price < position.lowest_price:
                        position.lowest_price = current_price
                        position.stop_loss = current_price * (1 + position.trailing_stop_loss / 100)
            
            # Check stop loss
            if position.stop_loss:
                if position.side == 'long' and current_price <= position.stop_loss:
                    logger.debug(f"Stop loss hit for {symbol}")
                    self._close_position(symbol, current_price)
                    continue
                elif position.side == 'short' and current_price >= position.stop_loss:
                    logger.debug(f"Stop loss hit for {symbol}")
                    self._close_position(symbol, current_price)
                    continue
            
            # Check take profit
            if position.take_profit:
                if position.side == 'long' and current_price >= position.take_profit:
                    logger.debug(f"Take profit hit for {symbol}")
                    self._close_position(symbol, current_price)
                    continue
                elif position.side == 'short' and current_price <= position.take_profit:
                    logger.debug(f"Take profit hit for {symbol}")
                    self._close_position(symbol, current_price)
                    continue
    
    def _process_pending_orders(self) -> None:
        """Process any pending limit orders"""
        # For simplicity, we're using market orders in backtest
        # This method is a placeholder for future limit order support
        pass
    
    def _close_all_positions(self) -> None:
        """Close all remaining positions at end of backtest"""
        for symbol in list(self.positions.keys()):
            current_price = self.data_sync.get_price_at_time(symbol, self.current_time)
            if current_price:
                self._close_position(symbol, current_price)
    
    def _record_equity_point(self) -> None:
        """Record current equity for equity curve"""
        # Calculate total equity (cash + position values)
        position_value = 0.0
        for symbol, position in self.positions.items():
            current_price = self.data_sync.get_price_at_time(symbol, self.current_time)
            if current_price:
                if position.side == 'long':
                    position_value += current_price * position.quantity
                else:  # short
                    # For short positions, value is entry_value - (current_value - entry_value)
                    entry_value = position.entry_price * position.quantity
                    current_value = current_price * position.quantity
                    position_value += 2 * entry_value - current_value
        
        self.equity = self.cash + position_value
        
        # Update peak and drawdown
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        drawdown = ((self.peak_equity - self.equity) / self.peak_equity) * 100 if self.peak_equity > 0 else 0
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        # Record equity point (sample every 100 points to reduce memory)
        if len(self.equity_curve) == 0 or len(self.equity_curve) % 100 == 0:
            point = EquityPoint(
                timestamp=self.current_time,
                equity=self.equity,
                drawdown=drawdown
            )
            self.equity_curve.append(point)
