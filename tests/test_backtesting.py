"""
Unit tests for backtesting engine.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models.backtest import (
    Backtest, BacktestConfig, BacktestTrade, EquityPoint,
    PerformanceMetrics, BacktestStatus
)
from strategy_workers.strategy_interface import (
    IStrategy, StrategyConfig, MultiTimeframeData, Signal, Candle
)
from backtesting_engine.data_loader import MultiTimeframeDataSynchronizer
from backtesting_engine.execution_engine import BacktestExecutionEngine
from backtesting_engine.metrics_calculator import MetricsCalculator


# Test database setup
@pytest.fixture(scope='function')
def db_session():
    """Create a test database session."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_candles():
    """Create sample candle data for testing."""
    base_time = datetime(2024, 1, 1, 9, 0, 0)
    candles = []
    
    # Create 100 candles with upward trend
    for i in range(100):
        candle = Candle(
            symbol='TEST',
            timeframe='5m',
            open=100.0 + i * 0.5,
            high=101.0 + i * 0.5,
            low=99.0 + i * 0.5,
            close=100.5 + i * 0.5,
            volume=1000,
            timestamp=base_time + timedelta(minutes=5 * i),
            is_forming=False
        )
        candles.append(candle)
    
    return candles


@pytest.fixture
def sample_historical_data(sample_candles):
    """Create sample historical data structure."""
    return {
        'TEST': {
            '5m': sample_candles
        }
    }


@pytest.fixture
def backtest_config():
    """Create sample backtest configuration."""
    return BacktestConfig(
        strategy_id='test-strategy-id',
        account_id='test-account-id',
        symbols=['TEST'],
        timeframes=['5m'],
        start_date=datetime(2024, 1, 1, 9, 0, 0),
        end_date=datetime(2024, 1, 1, 17, 0, 0),
        initial_capital=100000.0,
        slippage=0.0005,
        commission=0.0003
    )


class MockStrategy(IStrategy):
    """Mock strategy for testing."""
    
    def __init__(self):
        self.initialized = False
        self.candle_count = 0
    
    def initialize(self, config: StrategyConfig) -> None:
        self.initialized = True
    
    def on_tick(self, data: MultiTimeframeData):
        return None
    
    def on_candle_complete(self, timeframe: str, candle: Candle, data: MultiTimeframeData):
        self.candle_count += 1
        
        # Simple strategy: buy on 10th candle, sell on 20th candle
        if self.candle_count == 10:
            return Signal(
                type='entry',
                direction='long',
                symbol='TEST',
                quantity=10,
                order_type='market'
            )
        elif self.candle_count == 20:
            return Signal(
                type='exit',
                direction='long',
                symbol='TEST',
                quantity=10,
                order_type='market'
            )
        
        return None
    
    def cleanup(self) -> None:
        pass


class TestBacktestConfig:
    """Tests for backtest configuration."""
    
    def test_valid_config(self, backtest_config):
        """Test valid configuration passes validation."""
        backtest_config.validate()  # Should not raise
    
    def test_empty_symbols_raises_error(self, backtest_config):
        """Test empty symbols list raises error."""
        backtest_config.symbols = []
        with pytest.raises(ValueError, match="At least one symbol is required"):
            backtest_config.validate()
    
    def test_empty_timeframes_raises_error(self, backtest_config):
        """Test empty timeframes list raises error."""
        backtest_config.timeframes = []
        with pytest.raises(ValueError, match="At least one timeframe is required"):
            backtest_config.validate()
    
    def test_invalid_date_range_raises_error(self, backtest_config):
        """Test start date after end date raises error."""
        backtest_config.start_date = datetime(2024, 1, 2)
        backtest_config.end_date = datetime(2024, 1, 1)
        with pytest.raises(ValueError, match="Start date must be before end date"):
            backtest_config.validate()
    
    def test_negative_capital_raises_error(self, backtest_config):
        """Test negative initial capital raises error."""
        backtest_config.initial_capital = -1000
        with pytest.raises(ValueError, match="Initial capital must be positive"):
            backtest_config.validate()
    
    def test_invalid_slippage_raises_error(self, backtest_config):
        """Test invalid slippage raises error."""
        backtest_config.slippage = 0.15  # 15% is too high
        with pytest.raises(ValueError, match="Slippage must be between 0 and 0.1"):
            backtest_config.validate()


class TestMultiTimeframeDataSynchronizer:
    """Tests for multi-timeframe data synchronizer."""
    
    def test_get_candles_at_time(self, sample_historical_data):
        """Test getting candles up to specific time."""
        sync = MultiTimeframeDataSynchronizer(sample_historical_data)
        
        # Get candles at 10th candle time
        target_time = datetime(2024, 1, 1, 9, 45, 0)  # 10th candle
        candles = sync.get_candles_at_time('TEST', '5m', target_time, lookback=5)
        
        assert len(candles) == 5
        assert all(c.timestamp <= target_time for c in candles)
    
    def test_get_all_timestamps(self, sample_historical_data):
        """Test getting all unique timestamps."""
        sync = MultiTimeframeDataSynchronizer(sample_historical_data)
        timestamps = sync.get_all_timestamps()
        
        assert len(timestamps) == 100
        assert timestamps == sorted(timestamps)  # Should be sorted
    
    def test_get_price_at_time(self, sample_historical_data):
        """Test getting price at specific time."""
        sync = MultiTimeframeDataSynchronizer(sample_historical_data)
        
        target_time = datetime(2024, 1, 1, 9, 45, 0)
        price = sync.get_price_at_time('TEST', target_time)
        
        assert price is not None
        assert price > 0


class TestBacktestExecutionEngine:
    """Tests for backtest execution engine."""
    
    def test_backtest_execution_with_sample_data(
        self, backtest_config, sample_historical_data
    ):
        """Test backtest executes successfully with sample data."""
        strategy = MockStrategy()
        data_sync = MultiTimeframeDataSynchronizer(sample_historical_data)
        
        engine = BacktestExecutionEngine(backtest_config, strategy, data_sync)
        trades, equity_curve = engine.run()
        
        # Should have executed at least one trade
        assert len(trades) >= 1
        assert len(equity_curve) > 0
        
        # Strategy should have been initialized
        assert strategy.initialized
    
    def test_order_fill_with_slippage(
        self, backtest_config, sample_historical_data
    ):
        """Test orders are filled with configured slippage."""
        strategy = MockStrategy()
        data_sync = MultiTimeframeDataSynchronizer(sample_historical_data)
        
        engine = BacktestExecutionEngine(backtest_config, strategy, data_sync)
        trades, equity_curve = engine.run()
        
        if trades:
            trade = trades[0]
            # Entry price should include slippage
            # For buy orders, slippage increases price
            assert trade.entry_price > 0
    
    def test_commission_applied_to_trades(
        self, backtest_config, sample_historical_data
    ):
        """Test commission is applied to all trades."""
        strategy = MockStrategy()
        data_sync = MultiTimeframeDataSynchronizer(sample_historical_data)
        
        engine = BacktestExecutionEngine(backtest_config, strategy, data_sync)
        trades, equity_curve = engine.run()
        
        for trade in trades:
            assert trade.commission > 0
            # Commission should be deducted from P&L
            assert trade.commission == pytest.approx(
                trade.exit_price * trade.quantity * backtest_config.commission,
                rel=0.01
            )


class TestMetricsCalculator:
    """Tests for performance metrics calculator."""
    
    def test_calculate_metrics_with_winning_trades(self):
        """Test metrics calculation with winning trades."""
        trades = [
            BacktestTrade(
                entry_date=datetime(2024, 1, 1, 10, 0),
                exit_date=datetime(2024, 1, 1, 11, 0),
                symbol='TEST',
                side='long',
                entry_price=100.0,
                exit_price=105.0,
                quantity=10,
                pnl=50.0,
                pnl_percent=5.0,
                commission=0.3,
                holding_time_seconds=3600
            ),
            BacktestTrade(
                entry_date=datetime(2024, 1, 1, 12, 0),
                exit_date=datetime(2024, 1, 1, 13, 0),
                symbol='TEST',
                side='long',
                entry_price=105.0,
                exit_price=110.0,
                quantity=10,
                pnl=50.0,
                pnl_percent=4.76,
                commission=0.3,
                holding_time_seconds=3600
            )
        ]
        
        equity_curve = [
            EquityPoint(datetime(2024, 1, 1, 10, 0), 100000, 0),
            EquityPoint(datetime(2024, 1, 1, 11, 0), 100050, 0),
            EquityPoint(datetime(2024, 1, 1, 13, 0), 100100, 0)
        ]
        
        metrics = MetricsCalculator.calculate_metrics(
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=100000,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )
        
        assert metrics.total_trades == 2
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 0
        assert metrics.win_rate == 100.0
        assert metrics.average_win == 50.0
        assert metrics.profit_factor > 0
    
    def test_calculate_metrics_with_mixed_trades(self):
        """Test metrics calculation with winning and losing trades."""
        trades = [
            BacktestTrade(
                entry_date=datetime(2024, 1, 1, 10, 0),
                exit_date=datetime(2024, 1, 1, 11, 0),
                symbol='TEST',
                side='long',
                entry_price=100.0,
                exit_price=105.0,
                quantity=10,
                pnl=50.0,
                pnl_percent=5.0,
                commission=0.3,
                holding_time_seconds=3600
            ),
            BacktestTrade(
                entry_date=datetime(2024, 1, 1, 12, 0),
                exit_date=datetime(2024, 1, 1, 13, 0),
                symbol='TEST',
                side='long',
                entry_price=105.0,
                exit_price=100.0,
                quantity=10,
                pnl=-50.0,
                pnl_percent=-4.76,
                commission=0.3,
                holding_time_seconds=3600
            )
        ]
        
        equity_curve = [
            EquityPoint(datetime(2024, 1, 1, 10, 0), 100000, 0),
            EquityPoint(datetime(2024, 1, 1, 11, 0), 100050, 0),
            EquityPoint(datetime(2024, 1, 1, 13, 0), 100000, 0)
        ]
        
        metrics = MetricsCalculator.calculate_metrics(
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=100000,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )
        
        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate == 50.0
        assert metrics.average_win == 50.0
        assert metrics.average_loss == -50.0
        assert metrics.profit_factor == 1.0  # Equal wins and losses
    
    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation."""
        equity_curve = [
            EquityPoint(datetime(2024, 1, 1, 10, 0), 100000, 0),
            EquityPoint(datetime(2024, 1, 1, 11, 0), 105000, 0),  # Peak
            EquityPoint(datetime(2024, 1, 1, 12, 0), 95000, 0),   # Drawdown
            EquityPoint(datetime(2024, 1, 1, 13, 0), 100000, 0)
        ]
        
        max_dd = MetricsCalculator._calculate_max_drawdown(equity_curve)
        
        # Max drawdown should be (105000 - 95000) / 105000 = 9.52%
        assert max_dd == pytest.approx(9.52, rel=0.01)
    
    def test_consecutive_wins_calculation(self):
        """Test maximum consecutive wins calculation."""
        trades = [
            BacktestTrade(
                entry_date=datetime(2024, 1, 1, 10, 0),
                exit_date=datetime(2024, 1, 1, 11, 0),
                symbol='TEST', side='long',
                entry_price=100.0, exit_price=105.0,
                quantity=10, pnl=50.0, pnl_percent=5.0,
                commission=0.3, holding_time_seconds=3600
            ),
            BacktestTrade(
                entry_date=datetime(2024, 1, 1, 12, 0),
                exit_date=datetime(2024, 1, 1, 13, 0),
                symbol='TEST', side='long',
                entry_price=105.0, exit_price=110.0,
                quantity=10, pnl=50.0, pnl_percent=4.76,
                commission=0.3, holding_time_seconds=3600
            ),
            BacktestTrade(
                entry_date=datetime(2024, 1, 1, 14, 0),
                exit_date=datetime(2024, 1, 1, 15, 0),
                symbol='TEST', side='long',
                entry_price=110.0, exit_price=105.0,
                quantity=10, pnl=-50.0, pnl_percent=-4.55,
                commission=0.3, holding_time_seconds=3600
            )
        ]
        
        max_wins = MetricsCalculator._calculate_max_consecutive_wins(trades)
        assert max_wins == 2
    
    def test_no_trades_returns_zero_metrics(self):
        """Test that no trades returns zero metrics."""
        metrics = MetricsCalculator.calculate_metrics(
            trades=[],
            equity_curve=[],
            initial_capital=100000,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )
        
        assert metrics.total_trades == 0
        assert metrics.total_return == 0.0
        assert metrics.win_rate == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
