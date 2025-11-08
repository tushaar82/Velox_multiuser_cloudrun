"""
Unit tests for Market Data Engine

Tests candle formation, indicator calculations, and market data processing.
"""
import pytest
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# Mock influxdb_client before importing market_data_engine modules
sys.modules['influxdb_client'] = MagicMock()
sys.modules['influxdb_client.client'] = MagicMock()
sys.modules['influxdb_client.client.write_api'] = MagicMock()

from market_data_engine.models import Tick, Candle, IndicatorValue
from market_data_engine.candle_manager import CandleManager
from market_data_engine.indicators import (
    SMAIndicator, EMAIndicator, RSIIndicator, MACDIndicator,
    BollingerBandsIndicator, IndicatorEngine
)
from market_data_engine.subscription_manager import SubscriptionManager
from market_data_engine.simulator import MarketDataSimulator


class TestCandleFormation:
    """Test candle formation from tick data"""
    
    def test_candle_creation_from_tick(self):
        """Test creating a new candle from first tick"""
        tick = Tick(
            symbol='RELIANCE',
            price=2450.50,
            volume=1000,
            timestamp=datetime(2024, 1, 1, 9, 15, 30)
        )
        
        candle_timestamp = datetime(2024, 1, 1, 9, 15, 0)
        candle = Candle.from_tick(tick, '1m', candle_timestamp)
        
        assert candle.symbol == 'RELIANCE'
        assert candle.timeframe == '1m'
        assert candle.open == 2450.50
        assert candle.high == 2450.50
        assert candle.low == 2450.50
        assert candle.close == 2450.50
        assert candle.volume == 1000
        assert candle.is_forming is True
    
    def test_candle_update_with_tick(self):
        """Test updating candle with new tick"""
        # Create initial candle
        tick1 = Tick('RELIANCE', 2450.50, 1000, datetime(2024, 1, 1, 9, 15, 30))
        candle = Candle.from_tick(tick1, '1m', datetime(2024, 1, 1, 9, 15, 0))
        
        # Update with higher price
        tick2 = Tick('RELIANCE', 2452.00, 500, datetime(2024, 1, 1, 9, 15, 45))
        candle.update_with_tick(tick2)
        
        assert candle.high == 2452.00
        assert candle.close == 2452.00
        assert candle.volume == 1500
        
        # Update with lower price
        tick3 = Tick('RELIANCE', 2449.00, 300, datetime(2024, 1, 1, 9, 15, 50))
        candle.update_with_tick(tick3)
        
        assert candle.low == 2449.00
        assert candle.close == 2449.00
        assert candle.volume == 1800
    
    def test_candle_formation_multiple_timeframes(self):
        """Test candle formation for multiple timeframes"""
        # Mock storage
        influxdb = Mock()
        redis = Mock()
        redis.get_forming_candle = Mock(return_value=None)
        redis.store_forming_candle = Mock()
        redis.publish_candle_update = Mock()
        redis.publish_candle_complete = Mock()
        redis.delete_forming_candle = Mock()
        
        buffer_manager = Mock()
        buffer_manager.add_candle = Mock()
        
        candle_manager = CandleManager(influxdb, redis, buffer_manager)
        
        # Create ticks over 5 minutes
        base_time = datetime(2024, 1, 1, 9, 15, 0)
        for i in range(5):
            tick = Tick(
                symbol='RELIANCE',
                price=2450.00 + i,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i, seconds=30)
            )
            candle_manager.on_tick(tick)
        
        # Should have stored forming candles for all timeframes
        assert redis.store_forming_candle.call_count > 0
    
    def test_candle_completion_detection(self):
        """Test detection of candle completion"""
        influxdb = Mock()
        redis = Mock()
        redis.get_forming_candle = Mock(return_value=None)
        redis.store_forming_candle = Mock()
        redis.publish_candle_update = Mock()
        redis.publish_candle_complete = Mock()
        redis.delete_forming_candle = Mock()
        
        buffer_manager = Mock()
        buffer_manager.add_candle = Mock()
        
        candle_manager = CandleManager(influxdb, redis, buffer_manager)
        
        # Track completed candles
        completed_candles = []
        candle_manager.register_candle_complete_callback(
            lambda c: completed_candles.append(c)
        )
        
        # Create ticks in first minute
        base_time = datetime(2024, 1, 1, 9, 15, 0)
        tick1 = Tick('RELIANCE', 2450.00, 1000, base_time + timedelta(seconds=30))
        candle_manager.on_tick(tick1)
        
        # Create tick in next minute (should complete previous candle)
        tick2 = Tick('RELIANCE', 2451.00, 1000, base_time + timedelta(minutes=1, seconds=30))
        
        # Mock the forming candle from first minute
        forming_candle = Candle.from_tick(tick1, '1m', base_time)
        redis.get_forming_candle = Mock(return_value=forming_candle)
        
        candle_manager.on_tick(tick2)
        
        # Should have completed the first candle
        assert len(completed_candles) > 0


class TestIndicators:
    """Test technical indicator calculations"""
    
    def test_sma_calculation(self):
        """Test Simple Moving Average calculation"""
        # Create test candles
        candles = []
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        
        for i, price in enumerate(prices):
            candle = Candle(
                symbol='TEST',
                timeframe='1m',
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i),
                is_forming=False
            )
            candles.append(candle)
        
        # Calculate 5-period SMA
        sma = SMAIndicator({'period': 5})
        result = sma.calculate(candles)
        
        assert result is not None
        # SMA of last 5 prices: (105 + 104 + 106 + 108 + 107 + 109) / 6 = 106.5
        # Actually last 5: (104, 106, 108, 107, 109) = 106.8
        expected_sma = sum(prices[-5:]) / 5
        assert abs(result.value - expected_sma) < 0.01
    
    def test_ema_calculation(self):
        """Test Exponential Moving Average calculation"""
        candles = []
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        
        for i, price in enumerate(prices):
            candle = Candle(
                symbol='TEST',
                timeframe='1m',
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i),
                is_forming=False
            )
            candles.append(candle)
        
        # Calculate 5-period EMA
        ema = EMAIndicator({'period': 5})
        result = ema.calculate(candles)
        
        assert result is not None
        assert result.indicator_type == 'EMA'
        assert isinstance(result.value, float)
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        candles = []
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        # Prices with clear uptrend
        prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
        
        for i, price in enumerate(prices):
            candle = Candle(
                symbol='TEST',
                timeframe='1m',
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i),
                is_forming=False
            )
            candles.append(candle)
        
        # Calculate 14-period RSI
        rsi = RSIIndicator({'period': 10})
        result = rsi.calculate(candles)
        
        assert result is not None
        assert result.indicator_type == 'RSI'
        # RSI should be high (>70) for strong uptrend
        assert result.value > 70
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        candles = []
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        prices = list(range(100, 150))  # 50 prices
        
        for i, price in enumerate(prices):
            candle = Candle(
                symbol='TEST',
                timeframe='1m',
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i),
                is_forming=False
            )
            candles.append(candle)
        
        # Calculate MACD
        macd = MACDIndicator({
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9
        })
        result = macd.calculate(candles)
        
        assert result is not None
        assert result.indicator_type == 'MACD'
        assert isinstance(result.value, dict)
        assert 'macd' in result.value
        assert 'signal' in result.value
        assert 'histogram' in result.value
    
    def test_bollinger_bands_calculation(self):
        """Test Bollinger Bands calculation"""
        candles = []
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113]
        
        for i, price in enumerate(prices):
            candle = Candle(
                symbol='TEST',
                timeframe='1m',
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i),
                is_forming=False
            )
            candles.append(candle)
        
        # Calculate Bollinger Bands
        bb = BollingerBandsIndicator({'period': 10, 'std_dev': 2})
        result = bb.calculate(candles)
        
        assert result is not None
        assert result.indicator_type == 'BB'
        assert isinstance(result.value, dict)
        assert 'upper' in result.value
        assert 'middle' in result.value
        assert 'lower' in result.value
        assert result.value['upper'] > result.value['middle']
        assert result.value['middle'] > result.value['lower']
    
    def test_indicator_engine(self):
        """Test indicator engine with caching"""
        redis = Mock()
        redis.get_cached_indicator = Mock(return_value=None)
        redis.cache_indicator = Mock()
        
        engine = IndicatorEngine(redis)
        
        # Create test candles
        candles = []
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        for i in range(20):
            candle = Candle(
                symbol='TEST',
                timeframe='1m',
                open=100 + i,
                high=101 + i,
                low=99 + i,
                close=100 + i,
                volume=1000,
                timestamp=base_time + timedelta(minutes=i),
                is_forming=False
            )
            candles.append(candle)
        
        # Calculate indicator
        result = engine.calculate_indicator(
            'TEST', '1m', 'SMA', {'period': 10}, candles
        )
        
        assert result is not None
        assert redis.cache_indicator.called


class TestSubscriptionManager:
    """Test subscription management"""
    
    def test_subscribe_to_symbol(self):
        """Test subscribing to a symbol"""
        manager = SubscriptionManager()
        
        manager.subscribe('strategy1', 'RELIANCE', ['1m', '5m'], 'NSE')
        
        assert 'RELIANCE' in manager.get_subscribed_symbols()
        assert 'strategy1' in manager.get_subscribers_for_symbol('RELIANCE')
        assert manager.is_subscribed('strategy1', 'RELIANCE', '1m')
        assert manager.is_subscribed('strategy1', 'RELIANCE', '5m')
    
    def test_unsubscribe_from_symbol(self):
        """Test unsubscribing from a symbol"""
        manager = SubscriptionManager()
        
        manager.subscribe('strategy1', 'RELIANCE', ['1m', '5m'], 'NSE')
        manager.unsubscribe('strategy1', 'RELIANCE')
        
        assert 'RELIANCE' not in manager.get_subscribed_symbols()
        assert not manager.is_subscribed('strategy1', 'RELIANCE')
    
    def test_multiple_subscribers(self):
        """Test multiple subscribers to same symbol"""
        manager = SubscriptionManager()
        
        manager.subscribe('strategy1', 'RELIANCE', ['1m'], 'NSE')
        manager.subscribe('strategy2', 'RELIANCE', ['5m'], 'NSE')
        
        subscribers = manager.get_subscribers_for_symbol('RELIANCE')
        assert len(subscribers) == 2
        assert 'strategy1' in subscribers
        assert 'strategy2' in subscribers
    
    def test_subscription_stats(self):
        """Test subscription statistics"""
        manager = SubscriptionManager()
        
        manager.subscribe('strategy1', 'RELIANCE', ['1m', '5m'], 'NSE')
        manager.subscribe('strategy2', 'TCS', ['1m'], 'NSE')
        
        stats = manager.get_stats()
        assert stats['total_subscriptions'] == 2
        assert stats['unique_symbols'] == 2
        assert stats['unique_subscribers'] == 2


class TestMarketDataSimulator:
    """Test market data simulator"""
    
    def test_generate_synthetic_data(self):
        """Test synthetic data generation"""
        simulator = MarketDataSimulator()
        
        count = simulator.generate_synthetic_data(
            symbol='TEST',
            start_price=100.0,
            num_ticks=100,
            volatility=0.02,
            trend=0.001
        )
        
        assert count == 100
        assert 'TEST' in simulator.historical_data
        assert len(simulator.historical_data['TEST']) == 100
    
    def test_simulator_playback_control(self):
        """Test simulator playback controls"""
        simulator = MarketDataSimulator()
        
        # Generate data
        simulator.generate_synthetic_data('TEST', 100.0, 50)
        
        # Track received ticks
        received_ticks = []
        simulator.on_tick(lambda tick: received_ticks.append(tick))
        
        # Start replay
        simulator.set_speed(10.0)  # 10x speed for faster test
        success = simulator.start_replay(['TEST'])
        assert success is True
        
        # Let it run briefly
        import time
        time.sleep(0.5)
        
        # Pause
        simulator.pause()
        tick_count_paused = len(received_ticks)
        
        time.sleep(0.2)
        
        # Should not have received more ticks while paused
        assert len(received_ticks) == tick_count_paused
        
        # Resume
        simulator.resume()
        time.sleep(0.3)
        
        # Should have received more ticks
        assert len(received_ticks) > tick_count_paused
        
        # Stop
        simulator.stop()
    
    def test_simulator_speed_control(self):
        """Test simulator speed adjustment"""
        simulator = MarketDataSimulator()
        
        simulator.set_speed(2.0)
        assert simulator.speed == 2.0
        
        simulator.set_speed(0.5)
        assert simulator.speed == 0.5
        
        with pytest.raises(ValueError):
            simulator.set_speed(0)
        
        with pytest.raises(ValueError):
            simulator.set_speed(-1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
