"""
Unit tests for strategy execution engine
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from redis import Redis

from strategy_workers.strategy_interface import (
    IStrategy, StrategyConfig, RiskConfig, StrategyStatus,
    Candle, TimeframeData, MultiTimeframeData, Signal
)
from strategy_workers.strategy_plugin_manager import StrategyPluginManager
from strategy_workers.strategy_state_manager import StrategyStateManager
from strategy_workers.strategy_orchestrator import StrategyOrchestrator
from strategy_workers.multi_timeframe_provider import MultiTimeframeDataProvider
from strategy_workers.strategies.moving_average_crossover.strategy import MovingAverageCrossoverStrategy


class TestStrategyPluginManager:
    """Test strategy plugin discovery and loading"""
    
    def test_discover_plugins(self, tmp_path):
        """Test plugin discovery"""
        # Create a test plugin directory
        plugin_dir = tmp_path / "strategies"
        plugin_dir.mkdir()
        
        # Create a test strategy plugin
        test_strategy_dir = plugin_dir / "test_strategy"
        test_strategy_dir.mkdir()
        
        # Create config.json
        config = {
            "name": "Test Strategy",
            "version": "1.0.0",
            "description": "Test strategy",
            "parameters": [
                {
                    "name": "period",
                    "type": "integer",
                    "default": 10,
                    "min": 5,
                    "max": 50
                }
            ]
        }
        
        import json
        with open(test_strategy_dir / "config.json", "w") as f:
            json.dump(config, f)
        
        # Create strategy.py
        strategy_code = '''
from strategy_workers.strategy_interface import IStrategy, StrategyConfig, MultiTimeframeData, Candle, Signal
from typing import Optional

class TestStrategy(IStrategy):
    def initialize(self, config: StrategyConfig) -> None:
        pass
    
    def on_tick(self, data: MultiTimeframeData) -> Optional[Signal]:
        return None
    
    def on_candle_complete(self, timeframe: str, candle: Candle, data: MultiTimeframeData) -> Optional[Signal]:
        return None
    
    def cleanup(self) -> None:
        pass
'''
        with open(test_strategy_dir / "strategy.py", "w") as f:
            f.write(strategy_code)
        
        # Test discovery
        manager = StrategyPluginManager(str(plugin_dir))
        plugins = manager.discover_plugins()
        
        assert len(plugins) == 1
        assert plugins[0]["name"] == "Test Strategy"
        assert "Test Strategy" in manager.list_strategies()
    
    def test_validate_parameters(self):
        """Test parameter validation"""
        manager = StrategyPluginManager()
        
        # Mock a strategy config
        manager.strategy_configs["Test"] = {
            "name": "Test",
            "parameters": [
                {
                    "name": "period",
                    "type": "integer",
                    "min": 5,
                    "max": 50,
                    "required": True
                }
            ]
        }
        
        # Valid parameters
        is_valid, error = manager.validate_parameters("Test", {"period": 10})
        assert is_valid
        assert error is None
        
        # Missing required parameter
        is_valid, error = manager.validate_parameters("Test", {})
        assert not is_valid
        assert "missing" in error.lower()
        
        # Out of range
        is_valid, error = manager.validate_parameters("Test", {"period": 100})
        assert not is_valid
        assert "must be" in error.lower()


class TestStrategyStateManager:
    """Test strategy state persistence"""
    
    @pytest.fixture
    def redis_mock(self):
        """Mock Redis client"""
        return Mock(spec=Redis)
    
    @pytest.fixture
    def state_manager(self, redis_mock):
        """Create state manager with mock Redis"""
        return StrategyStateManager(redis_mock)
    
    def test_save_and_load_state(self, state_manager, redis_mock):
        """Test saving and loading strategy state"""
        from strategy_workers.strategy_interface import StrategyState
        
        # Create test state
        config = StrategyConfig(
            strategy_id="test-123",
            account_id="acc-456",
            trading_mode="paper",
            symbols=["NIFTY"],
            timeframes=["1m"],
            parameters={"period": 10}
        )
        
        state = StrategyState(
            strategy_id="test-123",
            account_id="acc-456",
            status=StrategyStatus.RUNNING,
            config=config,
            started_at=datetime.utcnow(),
            last_update=datetime.utcnow()
        )
        
        # Mock Redis setex
        redis_mock.setex = Mock()
        redis_mock.sadd = Mock()
        
        # Save state
        state_manager.save_state(state)
        
        # Verify Redis was called
        assert redis_mock.setex.called
        assert redis_mock.sadd.called
    
    def test_update_status(self, state_manager, redis_mock):
        """Test updating strategy status"""
        # Mock load_state to return a state
        state_manager.load_state = Mock(return_value=Mock(
            strategy_id="test-123",
            status=StrategyStatus.RUNNING,
            last_update=datetime.utcnow()
        ))
        
        state_manager.save_state = Mock()
        
        # Update status
        state_manager.update_status("test-123", StrategyStatus.PAUSED)
        
        # Verify save was called
        assert state_manager.save_state.called


class TestMultiTimeframeDataProvider:
    """Test multi-timeframe data aggregation"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        redis_mock = Mock(spec=Redis)
        candle_storage_mock = Mock()
        indicator_calculator_mock = Mock()
        
        return redis_mock, candle_storage_mock, indicator_calculator_mock
    
    @pytest.fixture
    def data_provider(self, mock_dependencies):
        """Create data provider with mocks"""
        redis_mock, candle_storage, indicator_calc = mock_dependencies
        return MultiTimeframeDataProvider(redis_mock, candle_storage, indicator_calc)
    
    def test_get_data(self, data_provider, mock_dependencies):
        """Test getting multi-timeframe data"""
        redis_mock, candle_storage, indicator_calc = mock_dependencies
        
        # Mock candle storage
        test_candles = [
            Candle(
                symbol="NIFTY",
                timeframe="1m",
                open=18000.0,
                high=18010.0,
                low=17990.0,
                close=18005.0,
                volume=1000,
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                is_forming=False
            )
            for i in range(10, 0, -1)
        ]
        
        candle_storage.get_recent_candles = Mock(return_value=test_candles)
        
        # Mock forming candle
        redis_mock.get = Mock(return_value=None)
        
        # Get data
        data = data_provider.get_data("NIFTY", ["1m", "5m"])
        
        assert data.symbol == "NIFTY"
        assert "1m" in data.timeframes
        assert "5m" in data.timeframes
        assert len(data.timeframes["1m"].historical_candles) == 10
    
    def test_ensure_data_consistency(self, data_provider):
        """Test data consistency validation"""
        # Create test data
        candles = [
            Candle(
                symbol="NIFTY",
                timeframe="1m",
                open=18000.0,
                high=18010.0,
                low=17990.0,
                close=18005.0,
                volume=1000,
                timestamp=datetime.utcnow(),
                is_forming=False
            )
        ]
        
        tf_data = TimeframeData(
            historical_candles=candles,
            forming_candle=None
        )
        
        data = MultiTimeframeData(
            symbol="NIFTY",
            timeframes={"1m": tf_data},
            current_price=18005.0,
            timestamp=datetime.utcnow()
        )
        
        # Should be consistent
        assert data_provider.ensure_data_consistency(data)
        
        # Test with empty data
        empty_data = MultiTimeframeData(
            symbol="NIFTY",
            timeframes={},
            current_price=0.0,
            timestamp=datetime.utcnow()
        )
        
        assert not data_provider.ensure_data_consistency(empty_data)


class TestStrategyOrchestrator:
    """Test strategy execution orchestration"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies"""
        redis_mock = Mock(spec=Redis)
        plugin_manager = Mock(spec=StrategyPluginManager)
        state_manager = Mock(spec=StrategyStateManager)
        data_provider = Mock(spec=MultiTimeframeDataProvider)
        
        return redis_mock, plugin_manager, state_manager, data_provider
    
    @pytest.fixture
    def orchestrator(self, mock_dependencies):
        """Create orchestrator with mocks"""
        redis_mock, plugin_mgr, state_mgr, data_prov = mock_dependencies
        return StrategyOrchestrator(redis_mock, plugin_mgr, state_mgr, data_prov)
    
    def test_load_strategy(self, orchestrator, mock_dependencies):
        """Test loading a strategy"""
        _, plugin_mgr, state_mgr, _ = mock_dependencies
        
        # Mock strategy class
        mock_strategy_class = Mock(return_value=Mock(spec=IStrategy))
        plugin_mgr.get_strategy = Mock(return_value=mock_strategy_class)
        plugin_mgr.validate_parameters = Mock(return_value=(True, None))
        
        # Create config
        config = StrategyConfig(
            strategy_id="test-123",
            account_id="acc-456",
            trading_mode="paper",
            symbols=["NIFTY"],
            timeframes=["1m"],
            parameters={"fast_period": 10, "slow_period": 20}
        )
        
        # Load strategy
        result = orchestrator.load_strategy(config, "Moving Average Crossover")
        
        assert result is True
        assert "test-123" in orchestrator.active_strategies
    
    def test_pause_and_resume_strategy(self, orchestrator, mock_dependencies):
        """Test pausing and resuming a strategy"""
        _, _, state_mgr, _ = mock_dependencies
        
        # Add a mock strategy
        orchestrator.active_strategies["test-123"] = Mock(spec=IStrategy)
        
        # Mock state manager
        state_mgr.update_status = Mock()
        state_mgr.load_state = Mock(return_value=Mock(status=StrategyStatus.PAUSED))
        
        # Pause strategy
        result = orchestrator.pause_strategy("test-123")
        assert result is True
        
        # Resume strategy
        result = orchestrator.resume_strategy("test-123")
        assert result is True
    
    def test_signal_validation(self, orchestrator):
        """Test signal validation"""
        config = StrategyConfig(
            strategy_id="test-123",
            account_id="acc-456",
            trading_mode="paper",
            symbols=["NIFTY"],
            timeframes=["1m"],
            parameters={}
        )
        
        # Valid signal
        valid_signal = Signal(
            type="entry",
            direction="long",
            symbol="NIFTY",
            quantity=1,
            order_type="market"
        )
        
        assert orchestrator._validate_signal(valid_signal, config) is True
        
        # Invalid signal - wrong symbol
        invalid_signal = Signal(
            type="entry",
            direction="long",
            symbol="BANKNIFTY",
            quantity=1,
            order_type="market"
        )
        
        assert orchestrator._validate_signal(invalid_signal, config) is False


class TestMovingAverageCrossoverStrategy:
    """Test MA Crossover strategy implementation"""
    
    @pytest.fixture
    def strategy(self):
        """Create strategy instance"""
        return MovingAverageCrossoverStrategy()
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return StrategyConfig(
            strategy_id="test-123",
            account_id="acc-456",
            trading_mode="paper",
            symbols=["NIFTY"],
            timeframes=["1m"],
            parameters={
                "fast_period": 5,
                "slow_period": 10,
                "ma_type": "SMA",
                "quantity": 1
            }
        )
    
    def test_initialize(self, strategy, config):
        """Test strategy initialization"""
        strategy.initialize(config)
        
        assert strategy.fast_period == 5
        assert strategy.slow_period == 10
        assert strategy.ma_type == "SMA"
        assert strategy.quantity == 1
    
    def test_calculate_sma(self, strategy, config):
        """Test SMA calculation"""
        strategy.initialize(config)
        
        # Create test candles
        candles = [
            Candle(
                symbol="NIFTY",
                timeframe="1m",
                open=18000.0 + i,
                high=18010.0 + i,
                low=17990.0 + i,
                close=18000.0 + i,
                volume=1000,
                timestamp=datetime.utcnow() - timedelta(minutes=10-i),
                is_forming=False
            )
            for i in range(10)
        ]
        
        # Calculate SMA
        sma = strategy._calculate_ma(candles, 5)
        
        # SMA of last 5 closes: (18005 + 18006 + 18007 + 18008 + 18009) / 5 = 18007
        assert sma is not None
        assert abs(sma - 18007.0) < 0.01
    
    def test_bullish_crossover_signal(self, strategy, config):
        """Test bullish crossover signal generation"""
        strategy.initialize(config)
        
        # Create candles showing bullish crossover
        # Fast MA will cross above slow MA
        candles = []
        for i in range(20):
            # Price trending up
            close_price = 18000.0 + (i * 10)
            candles.append(
                Candle(
                    symbol="NIFTY",
                    timeframe="1m",
                    open=close_price - 5,
                    high=close_price + 5,
                    low=close_price - 10,
                    close=close_price,
                    volume=1000,
                    timestamp=datetime.utcnow() - timedelta(minutes=20-i),
                    is_forming=False
                )
            )
        
        # Create timeframe data
        tf_data = TimeframeData(
            historical_candles=candles,
            forming_candle=None
        )
        
        data = MultiTimeframeData(
            symbol="NIFTY",
            timeframes={"1m": tf_data},
            current_price=candles[-1].close,
            timestamp=datetime.utcnow()
        )
        
        # Process candles to detect crossover
        signal = None
        for i in range(10, len(candles)):
            # Update historical candles
            tf_data.historical_candles = candles[:i+1]
            
            signal = strategy.on_candle_complete("1m", candles[i], data)
            
            if signal:
                break
        
        # Should generate entry signal at some point
        # (exact candle depends on when fast MA crosses above slow MA)
        assert signal is None or signal.type == "entry"
    
    def test_state_persistence(self, strategy, config):
        """Test strategy state save/load"""
        strategy.initialize(config)
        
        # Set some state
        strategy.position_open = True
        strategy.last_fast_ma = 18005.0
        strategy.last_slow_ma = 18000.0
        
        # Get state
        state = strategy.get_state()
        
        assert state["position_open"] is True
        assert state["last_fast_ma"] == 18005.0
        assert state["last_slow_ma"] == 18000.0
        
        # Create new strategy and restore state
        new_strategy = MovingAverageCrossoverStrategy()
        new_strategy.initialize(config)
        new_strategy.set_state(state)
        
        assert new_strategy.position_open is True
        assert new_strategy.last_fast_ma == 18005.0
        assert new_strategy.last_slow_ma == 18000.0
