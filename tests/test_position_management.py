"""
Unit tests for position management and trailing stop-loss.
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.connection import Base
from shared.models.position import Position, PositionData, PositionSide
from shared.models.trade import TradeData
from shared.models.order import OrderSide, TradingMode
from order_processor.position_manager import PositionManager
from order_processor.trailing_stop_manager import TrailingStopManager
import uuid


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
def position_manager(db_session):
    """Create position manager."""
    return PositionManager(db_session)


@pytest.fixture
def trailing_stop_manager(db_session):
    """Create trailing stop manager."""
    return TrailingStopManager(db_session)


@pytest.fixture
def sample_trade():
    """Create sample trade data."""
    return TradeData(
        id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        account_id=str(uuid.uuid4()),
        symbol='RELIANCE',
        side=OrderSide.BUY,
        quantity=10,
        price=2450.00,
        commission=7.35,
        trading_mode=TradingMode.PAPER,
        executed_at=datetime.utcnow()
    )


class TestPositionManager:
    """Tests for position manager."""
    
    def test_open_long_position(self, position_manager, sample_trade):
        """Test opening a long position."""
        position = position_manager.open_position(sample_trade)
        
        assert position.symbol == 'RELIANCE'
        assert position.side == PositionSide.LONG
        assert position.quantity == 10
        assert position.entry_price == 2450.00
        assert position.current_price == 2450.00
        assert position.unrealized_pnl == 0.0
        assert position.realized_pnl == -7.35  # Commission is realized loss
        assert position.trading_mode == TradingMode.PAPER
        assert position.closed_at is None
    
    def test_open_short_position(self, position_manager):
        """Test opening a short position."""
        trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            price=2450.00,
            commission=7.35,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        position = position_manager.open_position(trade)
        
        assert position.side == PositionSide.SHORT
        assert position.quantity == 10
    
    def test_calculate_pnl_long_position_profit(self, position_manager, sample_trade):
        """Test P&L calculation for profitable long position."""
        position = position_manager.open_position(sample_trade)
        
        # Price increases
        unrealized_pnl, total_pnl = position_manager.calculate_pnl(position.id, 2500.00)
        
        # Unrealized P&L = (2500 - 2450) * 10 = 500
        assert unrealized_pnl == 500.0
        # Total P&L = 500 - 7.35 (commission) = 492.65
        assert total_pnl == 492.65
    
    def test_calculate_pnl_long_position_loss(self, position_manager, sample_trade):
        """Test P&L calculation for losing long position."""
        position = position_manager.open_position(sample_trade)
        
        # Price decreases
        unrealized_pnl, total_pnl = position_manager.calculate_pnl(position.id, 2400.00)
        
        # Unrealized P&L = (2400 - 2450) * 10 = -500
        assert unrealized_pnl == -500.0
        # Total P&L = -500 - 7.35 = -507.35
        assert total_pnl == -507.35
    
    def test_calculate_pnl_short_position_profit(self, position_manager):
        """Test P&L calculation for profitable short position."""
        trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            price=2450.00,
            commission=7.35,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        position = position_manager.open_position(trade)
        
        # Price decreases (profit for short)
        unrealized_pnl, total_pnl = position_manager.calculate_pnl(position.id, 2400.00)
        
        # Unrealized P&L = (2450 - 2400) * 10 = 500
        assert unrealized_pnl == 500.0
    
    def test_close_position(self, position_manager, sample_trade):
        """Test closing a position."""
        position = position_manager.open_position(sample_trade)
        
        # Close at profit
        closed_position = position_manager.close_position(position.id, 2500.00, commission=7.35)
        
        assert closed_position.closed_at is not None
        assert closed_position.unrealized_pnl == 0.0
        # Realized P&L = (2500 - 2450) * 10 - 7.35 (open) - 7.35 (close) = 485.30
        assert closed_position.realized_pnl == 485.30
    
    def test_add_to_position(self, position_manager, sample_trade):
        """Test adding to an existing position."""
        position = position_manager.open_position(sample_trade)
        
        # Add more shares at higher price
        add_trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=sample_trade.account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=5,
            price=2500.00,
            commission=3.75,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        updated_position = position_manager.update_position(position.id, add_trade)
        
        # New quantity = 10 + 5 = 15
        assert updated_position.quantity == 15
        # New average = (2450*10 + 2500*5) / 15 = 2466.67
        assert abs(updated_position.entry_price - 2466.67) < 0.01
        # Realized P&L includes both commissions
        assert updated_position.realized_pnl == -11.10  # -7.35 - 3.75
    
    def test_reduce_position(self, position_manager, sample_trade):
        """Test reducing a position."""
        position = position_manager.open_position(sample_trade)
        
        # Sell half at profit
        reduce_trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=sample_trade.account_id,
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=5,
            price=2500.00,
            commission=3.75,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        updated_position = position_manager.update_position(position.id, reduce_trade)
        
        # Remaining quantity = 10 - 5 = 5
        assert updated_position.quantity == 5
        # Realized P&L = (2500 - 2450) * 5 - 7.35 - 3.75 = 238.90
        assert updated_position.realized_pnl == 238.90
    
    def test_get_positions_by_trading_mode(self, position_manager, sample_trade):
        """Test filtering positions by trading mode."""
        account_id = sample_trade.account_id
        
        # Open paper position
        paper_position = position_manager.open_position(sample_trade)
        
        # Open live position
        live_trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='TCS',
            side=OrderSide.BUY,
            quantity=5,
            price=3500.00,
            commission=5.25,
            trading_mode=TradingMode.LIVE,
            executed_at=datetime.utcnow()
        )
        live_position = position_manager.open_position(live_trade)
        
        # Get paper positions
        paper_positions = position_manager.get_positions(account_id, TradingMode.PAPER)
        assert len(paper_positions) == 1
        assert paper_positions[0].trading_mode == TradingMode.PAPER
        
        # Get live positions
        live_positions = position_manager.get_positions(account_id, TradingMode.LIVE)
        assert len(live_positions) == 1
        assert live_positions[0].trading_mode == TradingMode.LIVE


class TestTrailingStopManager:
    """Tests for trailing stop-loss manager."""
    
    def test_configure_trailing_stop_long_position(self, position_manager, trailing_stop_manager, sample_trade):
        """Test configuring trailing stop for long position."""
        position = position_manager.open_position(sample_trade)
        
        # Configure 2% trailing stop
        updated_position = trailing_stop_manager.configure_trailing_stop(
            position.id,
            percentage=0.02,
            current_price=2450.00
        )
        
        assert updated_position.trailing_stop_loss is not None
        assert updated_position.trailing_stop_loss.enabled is True
        assert updated_position.trailing_stop_loss.percentage == 0.02
        # Stop price = 2450 * (1 - 0.02) = 2401
        assert updated_position.trailing_stop_loss.current_stop_price == 2401.00
        assert updated_position.trailing_stop_loss.highest_price == 2450.00
    
    def test_trailing_stop_updates_on_favorable_move_long(self, position_manager, trailing_stop_manager, sample_trade):
        """Test trailing stop updates when price moves favorably for long position."""
        position = position_manager.open_position(sample_trade)
        trailing_stop_manager.configure_trailing_stop(position.id, 0.02, 2450.00)
        
        # Price increases to 2500
        updated_position, triggered = trailing_stop_manager.update_trailing_stop(position.id, 2500.00)
        
        assert triggered is False
        # New stop = 2500 * (1 - 0.02) = 2450
        assert updated_position.trailing_stop_loss.current_stop_price == 2450.00
        assert updated_position.trailing_stop_loss.highest_price == 2500.00
    
    def test_trailing_stop_does_not_update_on_unfavorable_move_long(self, position_manager, trailing_stop_manager, sample_trade):
        """Test trailing stop doesn't update when price moves unfavorably for long position."""
        position = position_manager.open_position(sample_trade)
        trailing_stop_manager.configure_trailing_stop(position.id, 0.02, 2450.00)
        
        # Price decreases to 2420
        updated_position, triggered = trailing_stop_manager.update_trailing_stop(position.id, 2420.00)
        
        assert triggered is False
        # Stop should remain at 2401
        assert updated_position.trailing_stop_loss.current_stop_price == 2401.00
    
    def test_trailing_stop_triggers_long_position(self, position_manager, trailing_stop_manager, sample_trade):
        """Test trailing stop triggers for long position."""
        position = position_manager.open_position(sample_trade)
        trailing_stop_manager.configure_trailing_stop(position.id, 0.02, 2450.00)
        
        # Price drops below stop
        updated_position, triggered = trailing_stop_manager.update_trailing_stop(position.id, 2400.00)
        
        assert triggered is True
    
    def test_trailing_stop_short_position(self, position_manager, trailing_stop_manager):
        """Test trailing stop for short position."""
        trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            price=2450.00,
            commission=7.35,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        position = position_manager.open_position(trade)
        trailing_stop_manager.configure_trailing_stop(position.id, 0.02, 2450.00)
        
        # Price decreases (favorable for short)
        updated_position, triggered = trailing_stop_manager.update_trailing_stop(position.id, 2400.00)
        
        assert triggered is False
        # New stop = 2400 * (1 + 0.02) = 2448
        assert updated_position.trailing_stop_loss.current_stop_price == 2448.00
        assert updated_position.trailing_stop_loss.lowest_price == 2400.00
    
    def test_trailing_stop_triggers_short_position(self, position_manager, trailing_stop_manager):
        """Test trailing stop triggers for short position."""
        trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            price=2450.00,
            commission=7.35,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        
        position = position_manager.open_position(trade)
        trailing_stop_manager.configure_trailing_stop(position.id, 0.02, 2450.00)
        
        # Price increases above stop (unfavorable for short)
        # Stop is at 2450 * (1 + 0.02) = 2499
        updated_position, triggered = trailing_stop_manager.update_trailing_stop(position.id, 2500.00)
        
        assert triggered is True
    
    def test_disable_trailing_stop(self, position_manager, trailing_stop_manager, sample_trade):
        """Test disabling trailing stop."""
        position = position_manager.open_position(sample_trade)
        trailing_stop_manager.configure_trailing_stop(position.id, 0.02, 2450.00)
        
        # Disable trailing stop
        updated_position = trailing_stop_manager.disable_trailing_stop(position.id)
        
        assert updated_position.trailing_stop_loss.enabled is False
    
    def test_trailing_stop_callback_on_trigger(self, position_manager, trailing_stop_manager, sample_trade):
        """Test callback is called when trailing stop triggers."""
        position = position_manager.open_position(sample_trade)
        trailing_stop_manager.configure_trailing_stop(position.id, 0.02, 2450.00)
        
        # Register callback
        callback_called = []
        def callback(pos):
            callback_called.append(pos.id)
        
        trailing_stop_manager.register_stop_triggered_callback(callback)
        
        # Trigger stop
        trailing_stop_manager.update_trailing_stop(position.id, 2400.00)
        
        assert len(callback_called) == 1
        assert callback_called[0] == position.id


class TestPositionPnLCalculations:
    """Tests for P&L calculation edge cases."""
    
    def test_pnl_with_multiple_trades(self, position_manager):
        """Test P&L calculation with multiple trades."""
        account_id = str(uuid.uuid4())
        
        # Open position
        trade1 = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            price=2450.00,
            commission=7.35,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        position = position_manager.open_position(trade1)
        
        # Add to position
        trade2 = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            price=2500.00,
            commission=7.50,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        position = position_manager.update_position(position.id, trade2)
        
        # Average price = (2450*10 + 2500*10) / 20 = 2475
        assert position.entry_price == 2475.00
        
        # Calculate P&L at 2550
        unrealized_pnl, total_pnl = position_manager.calculate_pnl(position.id, 2550.00)
        
        # Unrealized = (2550 - 2475) * 20 = 1500
        assert unrealized_pnl == 1500.0
        # Total = 1500 - 7.35 - 7.50 = 1485.15
        assert total_pnl == 1485.15
    
    def test_partial_position_closure(self, position_manager):
        """Test closing position in multiple steps."""
        account_id = str(uuid.uuid4())
        
        # Open position
        trade1 = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=20,
            price=2450.00,
            commission=14.70,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        position = position_manager.open_position(trade1)
        
        # Close half at 2500
        trade2 = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            price=2500.00,
            commission=7.50,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        position = position_manager.update_position(position.id, trade2)
        
        # Realized P&L = (2500 - 2450) * 10 - 14.70 - 7.50 = 477.80
        assert position.realized_pnl == 477.80
        assert position.quantity == 10
        
        # Close remaining at 2550
        trade3 = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            price=2550.00,
            commission=7.65,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        position = position_manager.update_position(position.id, trade3)
        
        # Additional realized = (2550 - 2450) * 10 - 7.65 = 992.35
        # Total realized = 477.80 + 992.35 = 1470.15
        assert position.realized_pnl == 1470.15
        assert position.quantity == 0
        assert position.closed_at is not None


class TestRiskManagementIntegration:
    """Tests for risk management integration with position tracking."""
    
    def test_loss_limit_check_triggered_on_pnl_update(self, db_session, sample_trade):
        """Test that loss limit check is triggered when P&L is updated."""
        from api_gateway.risk_management_service import RiskManagementService
        from decimal import Decimal
        
        # Create risk service and position manager with integration
        risk_service = RiskManagementService(db_session)
        position_manager = PositionManager(db_session, risk_service)
        
        # Set loss limit
        account_id = uuid.UUID(sample_trade.account_id)
        risk_service.set_max_loss_limit(account_id, 'paper', Decimal('1000.00'))
        
        # Open position
        position = position_manager.open_position(sample_trade)
        
        # Update price to create loss
        position_manager.calculate_pnl(position.id, 2350.00)  # Loss of 1000
        
        # Check that risk limits were updated
        risk_limits = risk_service.get_risk_limits(account_id, 'paper')
        assert risk_limits is not None
        # Loss should be calculated (1000 loss + 7.35 commission = 1007.35)
        assert risk_limits.current_loss >= Decimal('1000.00')
    
    def test_loss_limit_breach_detection(self, db_session, sample_trade):
        """Test that loss limit breach is detected."""
        from api_gateway.risk_management_service import RiskManagementService
        from decimal import Decimal
        
        risk_service = RiskManagementService(db_session)
        position_manager = PositionManager(db_session, risk_service)
        
        # Set low loss limit
        account_id = uuid.UUID(sample_trade.account_id)
        risk_service.set_max_loss_limit(account_id, 'paper', Decimal('500.00'))
        
        # Open position
        position = position_manager.open_position(sample_trade)
        
        # Update price to create large loss that breaches limit
        position_manager.calculate_pnl(position.id, 2350.00)  # Loss of 1000
        
        # Check that breach was detected
        risk_limits = risk_service.get_risk_limits(account_id, 'paper')
        assert risk_limits.is_breached is True
        assert risk_limits.breached_at is not None
    
    def test_separate_loss_tracking_for_paper_and_live(self, db_session):
        """Test that paper and live trading losses are tracked separately."""
        from api_gateway.risk_management_service import RiskManagementService
        from decimal import Decimal
        
        risk_service = RiskManagementService(db_session)
        position_manager = PositionManager(db_session, risk_service)
        
        account_id = str(uuid.uuid4())
        
        # Set limits for both modes
        risk_service.set_max_loss_limit(uuid.UUID(account_id), 'paper', Decimal('1000.00'))
        risk_service.set_max_loss_limit(uuid.UUID(account_id), 'live', Decimal('500.00'))
        
        # Open paper position with loss
        paper_trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            price=2450.00,
            commission=7.35,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        paper_position = position_manager.open_position(paper_trade)
        position_manager.calculate_pnl(paper_position.id, 2350.00)  # 1000 loss
        
        # Open live position with smaller loss
        live_trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=account_id,
            symbol='TCS',
            side=OrderSide.BUY,
            quantity=5,
            price=3500.00,
            commission=5.25,
            trading_mode=TradingMode.LIVE,
            executed_at=datetime.utcnow()
        )
        live_position = position_manager.open_position(live_trade)
        position_manager.calculate_pnl(live_position.id, 3450.00)  # 250 loss
        
        # Check paper limits (should be breached)
        paper_limits = risk_service.get_risk_limits(uuid.UUID(account_id), 'paper')
        assert paper_limits.is_breached is True
        
        # Check live limits (should not be breached)
        live_limits = risk_service.get_risk_limits(uuid.UUID(account_id), 'live')
        assert live_limits.is_breached is False
    
    def test_loss_limit_check_on_position_update(self, db_session, sample_trade):
        """Test that loss limit check is triggered when position is updated."""
        from api_gateway.risk_management_service import RiskManagementService
        from decimal import Decimal
        
        risk_service = RiskManagementService(db_session)
        position_manager = PositionManager(db_session, risk_service)
        
        account_id = uuid.UUID(sample_trade.account_id)
        risk_service.set_max_loss_limit(account_id, 'paper', Decimal('500.00'))
        
        # Open position
        position = position_manager.open_position(sample_trade)
        
        # Reduce position at a loss
        reduce_trade = TradeData(
            id=str(uuid.uuid4()),
            order_id=str(uuid.uuid4()),
            account_id=sample_trade.account_id,
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            price=2400.00,  # Loss of 50 per share
            commission=6.00,
            trading_mode=TradingMode.PAPER,
            executed_at=datetime.utcnow()
        )
        position_manager.update_position(position.id, reduce_trade)
        
        # Check that loss was tracked
        risk_limits = risk_service.get_risk_limits(account_id, 'paper')
        assert risk_limits.current_loss > Decimal('0.00')
    
    def test_loss_limit_check_on_position_close(self, db_session, sample_trade):
        """Test that loss limit check is triggered when position is closed."""
        from api_gateway.risk_management_service import RiskManagementService
        from decimal import Decimal
        
        risk_service = RiskManagementService(db_session)
        position_manager = PositionManager(db_session, risk_service)
        
        account_id = uuid.UUID(sample_trade.account_id)
        risk_service.set_max_loss_limit(account_id, 'paper', Decimal('500.00'))
        
        # Open position
        position = position_manager.open_position(sample_trade)
        
        # Close at a loss
        position_manager.close_position(position.id, 2400.00, commission=6.00)
        
        # Check that loss was tracked
        risk_limits = risk_service.get_risk_limits(account_id, 'paper')
        assert risk_limits.current_loss > Decimal('0.00')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
