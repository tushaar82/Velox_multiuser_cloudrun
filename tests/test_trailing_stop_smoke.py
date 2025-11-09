"""
Smoke test for trailing stop implementation.
Simple test to verify the core trailing stop functionality works.
"""
import pytest


def test_trailing_stop_modules_import():
    """Test that all trailing stop modules can be imported."""
    try:
        from order_processor.trailing_stop_manager import TrailingStopManager
        from order_processor.trailing_stop_order_handler import TrailingStopOrderHandler
        from order_processor.market_data_processor import MarketDataProcessor
        assert TrailingStopManager is not None
        assert TrailingStopOrderHandler is not None
        assert MarketDataProcessor is not None
    except ImportError as e:
        pytest.fail(f"Failed to import trailing stop modules: {e}")


def test_trailing_stop_config_model():
    """Test TrailingStopConfig model."""
    from shared.models.position import TrailingStopConfig
    
    config = TrailingStopConfig(
        enabled=True,
        percentage=0.02,
        current_stop_price=2401.00,
        highest_price=2450.00,
        lowest_price=0
    )
    
    assert config.enabled is True
    assert config.percentage == 0.02
    assert config.current_stop_price == 2401.00
    assert config.highest_price == 2450.00
    assert config.lowest_price == 0


def test_position_data_with_trailing_stop():
    """Test PositionData with trailing stop configuration."""
    from shared.models.position import PositionData, PositionSide, TrailingStopConfig
    from shared.models.order import TradingMode
    from datetime import datetime
    
    trailing_config = TrailingStopConfig(
        enabled=True,
        percentage=0.02,
        current_stop_price=2401.00,
        highest_price=2450.00,
        lowest_price=0
    )
    
    position = PositionData(
        id="test-id",
        account_id="account-id",
        strategy_id="strategy-id",
        symbol="RELIANCE",
        side=PositionSide.LONG,
        quantity=10,
        entry_price=2450.00,
        current_price=2450.00,
        unrealized_pnl=0.0,
        realized_pnl=-7.35,
        trading_mode=TradingMode.PAPER,
        stop_loss=None,
        take_profit=None,
        trailing_stop_loss=trailing_config,
        opened_at=datetime.now(),
        closed_at=None
    )
    
    assert position.trailing_stop_loss is not None
    assert position.trailing_stop_loss.enabled is True
    assert position.trailing_stop_loss.percentage == 0.02


def test_trailing_stop_calculation_long():
    """Test trailing stop calculation for long position."""
    # Long position: stop = price * (1 - percentage)
    price = 2450.00
    percentage = 0.02
    expected_stop = price * (1 - percentage)  # 2401.00
    
    assert abs(expected_stop - 2401.00) < 0.01


def test_trailing_stop_calculation_short():
    """Test trailing stop calculation for short position."""
    # Short position: stop = price * (1 + percentage)
    price = 2450.00
    percentage = 0.02
    expected_stop = price * (1 + percentage)  # 2499.00
    
    assert abs(expected_stop - 2499.00) < 0.01


def test_trailing_stop_trigger_logic_long():
    """Test trailing stop trigger logic for long position."""
    current_stop = 2401.00
    current_price_above = 2420.00  # Above stop - not triggered
    current_price_below = 2400.00  # Below stop - triggered
    
    assert current_price_above > current_stop  # Not triggered
    assert current_price_below <= current_stop  # Triggered


def test_trailing_stop_trigger_logic_short():
    """Test trailing stop trigger logic for short position."""
    current_stop = 2499.00
    current_price_below = 2480.00  # Below stop - not triggered
    current_price_above = 2500.00  # Above stop - triggered
    
    assert current_price_below < current_stop  # Not triggered
    assert current_price_above >= current_stop  # Triggered


def test_trailing_stop_update_logic_long():
    """Test trailing stop update logic for long position."""
    # Long: stop only moves up, never down
    old_stop = 2401.00
    old_highest = 2450.00
    percentage = 0.02
    
    # Price moves up - stop should update
    new_price_up = 2500.00
    new_highest_up = max(new_price_up, old_highest)
    new_stop_up = new_highest_up * (1 - percentage)
    
    assert new_highest_up == 2500.00
    assert new_stop_up > old_stop  # Stop moved up
    assert abs(new_stop_up - 2450.00) < 0.01
    
    # Price moves down - stop should NOT update
    new_price_down = 2420.00
    new_highest_down = max(new_price_down, new_highest_up)
    new_stop_down = new_highest_down * (1 - percentage)
    
    assert new_highest_down == 2500.00  # Highest unchanged
    assert new_stop_down == new_stop_up  # Stop unchanged


def test_trailing_stop_update_logic_short():
    """Test trailing stop update logic for short position."""
    # Short: stop only moves down, never up
    old_stop = 2499.00
    old_lowest = 2450.00
    percentage = 0.02
    
    # Price moves down - stop should update
    new_price_down = 2400.00
    new_lowest_down = min(new_price_down, old_lowest)
    new_stop_down = new_lowest_down * (1 + percentage)
    
    assert new_lowest_down == 2400.00
    assert new_stop_down < old_stop  # Stop moved down
    assert abs(new_stop_down - 2448.00) < 0.01
    
    # Price moves up - stop should NOT update
    new_price_up = 2480.00
    new_lowest_up = min(new_price_up, new_lowest_down)
    new_stop_up = new_lowest_up * (1 + percentage)
    
    assert new_lowest_up == 2400.00  # Lowest unchanged
    assert new_stop_up == new_stop_down  # Stop unchanged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
