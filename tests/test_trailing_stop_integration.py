"""
Integration tests for trailing stop-loss with automatic exit order generation.

Tests the complete flow:
1. Position opened with trailing stop
2. Price updates trigger trailing stop
3. Exit order automatically generated
4. Position closed
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from shared.models.position import PositionData, PositionSide
from shared.models.order import OrderData, OrderSide, OrderStatus, TradingMode
from shared.models.trade import TradeData
from order_processor.position_manager import PositionManager
from order_processor.trailing_stop_manager import TrailingStopManager
from order_processor.trailing_stop_order_handler import TrailingStopOrderHandler
from order_processor.order_router import OrderRouter
from order_processor.market_data_processor import MarketDataProcessor


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_order_router():
    """Mock order router."""
    router = Mock(spec=OrderRouter)
    
    # Mock submit_order to return a mock order
    def mock_submit_order(**kwargs):
        return OrderData(
            id=str(uuid.uuid4()),
            account_id=kwargs['account_id'],
            strategy_id=kwargs.get('strategy_id'),
            symbol=kwargs['symbol'],
            side=kwargs['side'],
            quantity=kwargs['quantity'],
            order_type=kwargs['order_type'],
            price=kwargs.get('price'),
            stop_price=kwargs.get('stop_price'),
            trading_mode=kwargs['trading_mode'],
            status=OrderStatus.FILLED,
            filled_quantity=kwargs['quantity'],
            average_price=kwargs.get('current_market_price', 0),
            broker_order_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    router.submit_order = Mock(side_effect=mock_submit_order)
    return router


@pytest.fixture
def sample_long_position():
    """Sample long position for testing."""
    from shared.models.position import TrailingStopConfig
    
    return PositionData(
        id=str(uuid.uuid4()),
        account_id=str(uuid.uuid4()),
        strategy_id=str(uuid.uuid4()),
        symbol='RELIANCE',
        side=PositionSide.LONG,
        quantity=10,
        entry_price=2450.00,
        current_price=2450.00,
        unrealized_pnl=0.0,
        realized_pnl=-7.35,
        trading_mode=TradingMode.PAPER,
        stop_loss=None,
        take_profit=None,
        trailing_stop_loss=TrailingStopConfig(
            enabled=True,
            percentage=0.02,
            current_stop_price=2401.00,
            highest_price=2450.00,
            lowest_price=0
        ),
        opened_at=datetime.utcnow(),
        closed_at=None
    )


@pytest.fixture
def sample_short_position():
    """Sample short position for testing."""
    from shared.models.position import TrailingStopConfig
    
    return PositionData(
        id=str(uuid.uuid4()),
        account_id=str(uuid.uuid4()),
        strategy_id=str(uuid.uuid4()),
        symbol='TCS',
        side=PositionSide.SHORT,
        quantity=5,
        entry_price=3500.00,
        current_price=3500.00,
        unrealized_pnl=0.0,
        realized_pnl=-5.25,
        trading_mode=TradingMode.LIVE,
        stop_loss=None,
        take_profit=None,
        trailing_stop_loss=TrailingStopConfig(
            enabled=True,
            percentage=0.03,
            current_stop_price=3605.00,
            highest_price=0,
            lowest_price=3500.00
        ),
        opened_at=datetime.utcnow(),
        closed_at=None
    )


class TestTrailingStopOrderHandler:
    """Tests for trailing stop order handler."""
    
    def test_handler_initialization(self, mock_db_session, mock_order_router):
        """Test handler initializes correctly and registers callback."""
        mock_trailing_stop_manager = Mock(spec=TrailingStopManager)
        
        handler = TrailingStopOrderHandler(
            db_session=mock_db_session,
            trailing_stop_manager=mock_trailing_stop_manager,
            order_router=mock_order_router
        )
        
        # Verify callback was registered
        mock_trailing_stop_manager.register_stop_triggered_callback.assert_called_once()
    
    def test_exit_order_generated_on_long_position_trigger(
        self,
        mock_db_session,
        mock_order_router,
        sample_long_position
    ):
        """Test exit order is generated when long position trailing stop triggers."""
        mock_trailing_stop_manager = Mock(spec=TrailingStopManager)
        
        handler = TrailingStopOrderHandler(
            db_session=mock_db_session,
            trailing_stop_manager=mock_trailing_stop_manager,
            order_router=mock_order_router
        )
        
        # Get the registered callback
        callback = mock_trailing_stop_manager.register_stop_triggered_callback.call_args[0][0]
        
        # Trigger the callback with position
        callback(sample_long_position)
        
        # Verify exit order was submitted
        mock_order_router.submit_order.assert_called_once()
        call_kwargs = mock_order_router.submit_order.call_args[1]
        
        assert call_kwargs['account_id'] == sample_long_position.account_id
        assert call_kwargs['symbol'] == sample_long_position.symbol
        assert call_kwargs['side'] == OrderSide.SELL  # Exit long = sell
        assert call_kwargs['quantity'] == sample_long_position.quantity
        assert call_kwargs['order_type'] == 'market'
        assert call_kwargs['trading_mode'] == sample_long_position.trading_mode
    
    def test_exit_order_generated_on_short_position_trigger(
        self,
        mock_db_session,
        mock_order_router,
        sample_short_position
    ):
        """Test exit order is generated when short position trailing stop triggers."""
        mock_trailing_stop_manager = Mock(spec=TrailingStopManager)
        
        handler = TrailingStopOrderHandler(
            db_session=mock_db_session,
            trailing_stop_manager=mock_trailing_stop_manager,
            order_router=mock_order_router
        )
        
        # Get the registered callback
        callback = mock_trailing_stop_manager.register_stop_triggered_callback.call_args[0][0]
        
        # Trigger the callback with position
        callback(sample_short_position)
        
        # Verify exit order was submitted
        mock_order_router.submit_order.assert_called_once()
        call_kwargs = mock_order_router.submit_order.call_args[1]
        
        assert call_kwargs['account_id'] == sample_short_position.account_id
        assert call_kwargs['symbol'] == sample_short_position.symbol
        assert call_kwargs['side'] == OrderSide.BUY  # Exit short = buy
        assert call_kwargs['quantity'] == sample_short_position.quantity
        assert call_kwargs['order_type'] == 'market'
        assert call_kwargs['trading_mode'] == sample_short_position.trading_mode
    
    def test_process_price_update_checks_trailing_stops(
        self,
        mock_db_session,
        mock_order_router
    ):
        """Test price update triggers trailing stop checks."""
        mock_trailing_stop_manager = Mock(spec=TrailingStopManager)
        mock_trailing_stop_manager.check_all_trailing_stops.return_value = [
            (Mock(), False),  # Not triggered
            (Mock(), True),   # Triggered
        ]
        
        handler = TrailingStopOrderHandler(
            db_session=mock_db_session,
            trailing_stop_manager=mock_trailing_stop_manager,
            order_router=mock_order_router
        )
        
        # Process price update
        triggered_count = handler.process_price_update(
            symbol='RELIANCE',
            current_price=2400.00,
            trading_mode=TradingMode.PAPER
        )
        
        # Verify trailing stops were checked
        mock_trailing_stop_manager.check_all_trailing_stops.assert_called_once_with(
            'RELIANCE',
            2400.00,
            TradingMode.PAPER
        )
        
        assert triggered_count == 1
    
    def test_configure_trailing_stop_with_validation(
        self,
        mock_db_session,
        mock_order_router
    ):
        """Test trailing stop configuration with percentage validation."""
        mock_trailing_stop_manager = Mock(spec=TrailingStopManager)
        mock_position = Mock()
        mock_trailing_stop_manager.configure_trailing_stop.return_value = mock_position
        
        handler = TrailingStopOrderHandler(
            db_session=mock_db_session,
            trailing_stop_manager=mock_trailing_stop_manager,
            order_router=mock_order_router
        )
        
        # Valid percentage (2%)
        result = handler.configure_trailing_stop_with_validation(
            position_id='test-id',
            percentage=0.02,
            current_price=2450.00
        )
        
        assert result == mock_position
        mock_trailing_stop_manager.configure_trailing_stop.assert_called_once()
    
    def test_configure_trailing_stop_rejects_invalid_percentage(
        self,
        mock_db_session,
        mock_order_router
    ):
        """Test trailing stop configuration rejects invalid percentages."""
        mock_trailing_stop_manager = Mock(spec=TrailingStopManager)
        
        handler = TrailingStopOrderHandler(
            db_session=mock_db_session,
            trailing_stop_manager=mock_trailing_stop_manager,
            order_router=mock_order_router
        )
        
        # Too low (0.05%)
        with pytest.raises(ValueError, match="between 0.1% and 10%"):
            handler.configure_trailing_stop_with_validation(
                position_id='test-id',
                percentage=0.0005,
                current_price=2450.00
            )
        
        # Too high (15%)
        with pytest.raises(ValueError, match="between 0.1% and 10%"):
            handler.configure_trailing_stop_with_validation(
                position_id='test-id',
                percentage=0.15,
                current_price=2450.00
            )
        
        # Verify configure was never called
        mock_trailing_stop_manager.configure_trailing_stop.assert_not_called()


class TestMarketDataProcessor:
    """Tests for market data processor integration."""
    
    def test_price_update_triggers_position_and_trailing_stop_updates(self):
        """Test that price updates trigger both position and trailing stop updates."""
        mock_db_session = Mock(spec=Session)
        mock_redis = Mock()
        mock_position_manager = Mock(spec=PositionManager)
        mock_trailing_stop_handler = Mock(spec=TrailingStopOrderHandler)
        
        # Mock position updates
        mock_position_manager.update_all_positions_price.return_value = [
            Mock(id='pos1', symbol='RELIANCE'),
            Mock(id='pos2', symbol='RELIANCE')
        ]
        
        # Mock trailing stop checks
        mock_trailing_stop_handler.process_price_update.return_value = 1
        
        processor = MarketDataProcessor(
            db_session=mock_db_session,
            redis_client=mock_redis,
            position_manager=mock_position_manager,
            trailing_stop_handler=mock_trailing_stop_handler
        )
        
        # Process single tick
        result = processor.process_single_tick(
            symbol='RELIANCE',
            price=2400.00,
            trading_mode=TradingMode.PAPER
        )
        
        # Verify position manager was called
        mock_position_manager.update_all_positions_price.assert_called_once_with(
            'RELIANCE',
            2400.00,
            TradingMode.PAPER
        )
        
        # Verify trailing stop handler was called
        mock_trailing_stop_handler.process_price_update.assert_called_once_with(
            'RELIANCE',
            2400.00,
            TradingMode.PAPER
        )
        
        # Verify result
        assert result['symbol'] == 'RELIANCE'
        assert result['price'] == 2400.00
        assert result['positions_updated'] == 2
        assert result['trailing_stops_triggered'] == 1


class TestEndToEndTrailingStopFlow:
    """End-to-end integration tests for trailing stop flow."""
    
    @patch('order_processor.trailing_stop_order_handler.logger')
    def test_complete_trailing_stop_flow(self, mock_logger):
        """
        Test complete flow:
        1. Position with trailing stop configured
        2. Price moves favorably (stop trails)
        3. Price reverses and hits stop
        4. Exit order generated automatically
        """
        # Setup mocks
        mock_db_session = Mock(spec=Session)
        mock_order_router = Mock(spec=OrderRouter)
        
        # Create position
        from shared.models.position import TrailingStopConfig
        
        position = PositionData(
            id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            strategy_id=str(uuid.uuid4()),
            symbol='INFY',
            side=PositionSide.LONG,
            quantity=20,
            entry_price=1500.00,
            current_price=1500.00,
            unrealized_pnl=0.0,
            realized_pnl=-4.50,
            trading_mode=TradingMode.PAPER,
            stop_loss=None,
            take_profit=None,
            trailing_stop_loss=TrailingStopConfig(
                enabled=True,
                percentage=0.02,
                current_stop_price=1470.00,  # 1500 * 0.98
                highest_price=1500.00,
                lowest_price=0
            ),
            opened_at=datetime.utcnow(),
            closed_at=None
        )
        
        # Mock trailing stop manager
        mock_trailing_stop_manager = Mock(spec=TrailingStopManager)
        
        # Simulate price movements
        price_updates = [
            (1520.00, False),  # Price up, stop trails to 1489.60
            (1550.00, False),  # Price up, stop trails to 1519.00
            (1530.00, False),  # Price down but above stop
            (1510.00, True),   # Price hits stop at 1519.00 - TRIGGERED!
        ]
        
        def mock_check_trailing_stops(symbol, price, mode):
            # Find matching price update
            for update_price, triggered in price_updates:
                if price == update_price:
                    if triggered:
                        return [(position, True)]
                    else:
                        return [(position, False)]
            return []
        
        mock_trailing_stop_manager.check_all_trailing_stops.side_effect = mock_check_trailing_stops
        
        # Mock order submission
        exit_order = OrderData(
            id=str(uuid.uuid4()),
            account_id=position.account_id,
            strategy_id=position.strategy_id,
            symbol=position.symbol,
            side=OrderSide.SELL,
            quantity=position.quantity,
            order_type='market',
            price=None,
            stop_price=None,
            trading_mode=position.trading_mode,
            status=OrderStatus.FILLED,
            filled_quantity=position.quantity,
            average_price=1510.00,
            broker_order_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_order_router.submit_order.return_value = exit_order
        
        # Create handler
        handler = TrailingStopOrderHandler(
            db_session=mock_db_session,
            trailing_stop_manager=mock_trailing_stop_manager,
            order_router=mock_order_router
        )
        
        # Get the callback
        callback = mock_trailing_stop_manager.register_stop_triggered_callback.call_args[0][0]
        
        # Process price updates
        for price, should_trigger in price_updates:
            results = mock_check_trailing_stops(position.symbol, price, position.trading_mode)
            
            if should_trigger:
                # Trigger callback
                callback(position)
                
                # Verify exit order was generated
                mock_order_router.submit_order.assert_called_once()
                call_kwargs = mock_order_router.submit_order.call_args[1]
                
                assert call_kwargs['symbol'] == position.symbol
                assert call_kwargs['side'] == OrderSide.SELL
                assert call_kwargs['quantity'] == position.quantity
                assert call_kwargs['order_type'] == 'market'
                
                # Verify logging
                assert mock_logger.info.called
                
                break
