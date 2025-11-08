"""
Unit tests for risk management service.
Tests loss limit tracking, strategy limit enforcement, and breach handling.
"""
import pytest
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models import User, UserAccount, UserRole
from shared.models.risk_management import RiskLimits, StrategyLimits
from api_gateway.risk_management_service import RiskManagementService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import event, String
    from sqlalchemy.dialects.postgresql import UUID
    
    engine = create_engine('sqlite:///:memory:')
    
    # Register UUID type for SQLite (convert to String)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Override UUID columns to use String for SQLite
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, UUID):
                column.type = String(36)
    
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Insert default strategy limits
    session.add(StrategyLimits(trading_mode='paper', max_concurrent_strategies=5))
    session.add(StrategyLimits(trading_mode='live', max_concurrent_strategies=5))
    session.commit()
    
    yield session
    
    session.close()


@pytest.fixture
def risk_service(db_session):
    """Create a RiskManagementService instance with test database."""
    return RiskManagementService(db_session)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email="trader@example.com",
        password_hash="hashed_password",
        role=UserRole.TRADER
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_account(db_session, test_user):
    """Create a test user account."""
    account_id = str(uuid.uuid4())
    account = UserAccount(
        id=account_id,
        trader_id=test_user.id,
        name="Test Trading Account"
    )
    db_session.add(account)
    db_session.commit()
    return account


class TestMaxLossLimit:
    """Test maximum loss limit tracking."""
    
    def test_set_max_loss_limit_new(self, risk_service, test_account):
        """Test setting max loss limit for the first time."""
        result = risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        assert result.account_id == str(test_account.id)
        assert result.trading_mode == 'paper'
        assert result.max_loss_limit == Decimal('50000.00')
        assert result.current_loss == Decimal('0.00')
        assert result.is_breached is False
        assert result.acknowledged is False
    
    def test_set_max_loss_limit_update(self, risk_service, test_account):
        """Test updating existing max loss limit."""
        # Set initial limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Update limit
        result = risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('75000.00')
        )
        
        assert result.max_loss_limit == Decimal('75000.00')
    
    def test_set_max_loss_limit_separate_modes(self, risk_service, test_account):
        """Test that paper and live trading have separate limits."""
        # Set paper limit
        paper_result = risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Set live limit
        live_result = risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='live',
            max_loss_limit=Decimal('100000.00')
        )
        
        assert paper_result.max_loss_limit == Decimal('50000.00')
        assert live_result.max_loss_limit == Decimal('100000.00')
    
    def test_calculate_current_loss(self, risk_service, test_account):
        """Test current loss calculation."""
        # Note: This is a placeholder test since actual loss calculation
        # depends on positions and trades tables which aren't implemented yet
        loss_calc = risk_service.calculate_current_loss(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert loss_calc.realized_loss == Decimal('0.00')
        assert loss_calc.unrealized_loss == Decimal('0.00')
        assert loss_calc.total_loss == Decimal('0.00')
        assert loss_calc.timestamp is not None
    
    def test_check_loss_limit_not_breached(self, risk_service, test_account):
        """Test checking loss limit when not breached."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Check limit (current loss is 0)
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert is_breached is False
    
    def test_check_loss_limit_breached(self, risk_service, test_account):
        """Test checking loss limit when breached."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Check limit with high current loss
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        assert is_breached is True
        
        # Verify breach was recorded
        risk_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        assert risk_limits.is_breached is True
        assert risk_limits.breached_at is not None
        assert risk_limits.acknowledged is False
    
    def test_acknowledge_limit_breach(self, risk_service, test_account):
        """Test acknowledging a limit breach."""
        # Set limit and trigger breach
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        # Acknowledge breach
        result = risk_service.acknowledge_limit_breach(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert result.acknowledged is True
        assert result.is_breached is True  # Still breached, just acknowledged
    
    def test_acknowledge_breach_with_new_limit(self, risk_service, test_account):
        """Test acknowledging breach and updating limit."""
        # Set limit and trigger breach
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        # Acknowledge with higher limit
        result = risk_service.acknowledge_limit_breach(
            account_id=test_account.id,
            trading_mode='paper',
            new_limit=Decimal('75000.00')
        )
        
        assert result.max_loss_limit == Decimal('75000.00')
        assert result.is_breached is False  # No longer breached with new limit
        assert result.acknowledged is False  # Reset when breach cleared
    
    def test_get_risk_limits(self, risk_service, test_account):
        """Test retrieving risk limits."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Get limits
        result = risk_service.get_risk_limits(test_account.id, 'paper')
        
        assert result is not None
        assert result.max_loss_limit == Decimal('50000.00')
    
    def test_get_risk_limits_not_found(self, risk_service, test_account):
        """Test retrieving non-existent risk limits."""
        result = risk_service.get_risk_limits(test_account.id, 'paper')
        assert result is None


class TestConcurrentStrategyLimits:
    """Test concurrent strategy limit enforcement."""
    
    def test_set_global_strategy_limit(self, risk_service, test_user):
        """Test setting global strategy limit."""
        result = risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=10,
            updated_by=test_user.id
        )
        
        assert result['trading_mode'] == 'paper'
        assert result['max_concurrent_strategies'] == 10
        assert result['updated_by'] == str(test_user.id)
    
    def test_get_strategy_limit(self, risk_service):
        """Test retrieving strategy limit."""
        result = risk_service.get_strategy_limit('paper')
        
        assert result is not None
        assert result['trading_mode'] == 'paper'
        assert result['max_concurrent_strategies'] == 5  # Default from fixture
    
    def test_get_active_strategy_count(self, risk_service, test_account):
        """Test getting active strategy count."""
        # Note: This is a placeholder test since active_strategies table
        # isn't implemented yet
        count = risk_service.get_active_strategy_count(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert count == 0  # Placeholder returns 0
    
    def test_can_activate_strategy_allowed(self, risk_service, test_account):
        """Test that strategy activation is allowed when under limit."""
        can_activate, error_msg = risk_service.can_activate_strategy(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert can_activate is True
        assert error_msg is None
    
    def test_enforce_limit_success(self, risk_service, test_account):
        """Test enforcing limit when activation is allowed."""
        result = risk_service.enforce_limit(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert result is True
    
    def test_separate_limits_for_modes(self, risk_service, test_user):
        """Test that paper and live trading have separate strategy limits."""
        # Set different limits
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=10,
            updated_by=test_user.id
        )
        risk_service.set_global_strategy_limit(
            trading_mode='live',
            max_concurrent_strategies=3,
            updated_by=test_user.id
        )
        
        # Verify separate limits
        paper_limit = risk_service.get_strategy_limit('paper')
        live_limit = risk_service.get_strategy_limit('live')
        
        assert paper_limit['max_concurrent_strategies'] == 10
        assert live_limit['max_concurrent_strategies'] == 3


class TestLossCalculationWithMultiplePositions:
    """Test loss limit calculation with multiple positions."""
    
    def test_calculate_loss_with_no_positions(self, risk_service, test_account):
        """Test loss calculation when there are no positions."""
        loss_calc = risk_service.calculate_current_loss(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert loss_calc.realized_loss == Decimal('0.00')
        assert loss_calc.unrealized_loss == Decimal('0.00')
        assert loss_calc.total_loss == Decimal('0.00')
    
    def test_check_limit_with_multiple_loss_updates(self, risk_service, test_account):
        """Test checking limit with multiple loss updates simulating multiple positions."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Simulate position 1 loss
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('15000.00')
        )
        assert is_breached is False
        
        # Simulate position 2 loss (cumulative)
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('30000.00')
        )
        assert is_breached is False
        
        # Simulate position 3 loss (cumulative - breaches limit)
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('55000.00')
        )
        assert is_breached is True
        
        # Verify current loss is tracked
        risk_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        assert risk_limits.current_loss == Decimal('55000.00')
    
    def test_loss_tracking_updates_on_each_check(self, risk_service, test_account):
        """Test that current loss is updated on each check."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # First check with loss
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('10000.00')
        )
        
        risk_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        assert risk_limits.current_loss == Decimal('10000.00')
        
        # Second check with higher loss
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('25000.00')
        )
        
        risk_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        assert risk_limits.current_loss == Decimal('25000.00')
        
        # Third check with even higher loss
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('45000.00')
        )
        
        risk_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        assert risk_limits.current_loss == Decimal('45000.00')


class TestAutomaticStrategyPause:
    """Test automatic strategy pause when limit breached."""
    
    def test_breach_triggers_pause_flag(self, risk_service, test_account):
        """Test that breaching limit sets the breach flag."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Trigger breach
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        assert is_breached is True
        
        # Verify breach was recorded with timestamp
        risk_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        assert risk_limits.is_breached is True
        assert risk_limits.breached_at is not None
        assert risk_limits.acknowledged is False
    
    def test_pause_all_strategies_called_on_breach(self, risk_service, test_account):
        """Test that pause_all_strategies is called when limit is breached."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # First breach
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        assert is_breached is True
        
        # Call pause_all_strategies directly (placeholder returns 0)
        paused_count = risk_service.pause_all_strategies(
            account_id=test_account.id,
            trading_mode='paper',
            reason="Loss limit breached"
        )
        
        # Currently returns 0 as placeholder
        assert paused_count == 0
    
    def test_breach_not_triggered_twice(self, risk_service, test_account):
        """Test that breach is only recorded once."""
        # Set limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # First breach
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        risk_limits_1 = risk_service.get_risk_limits(test_account.id, 'paper')
        first_breach_time = risk_limits_1.breached_at
        
        # Second check with even higher loss
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('70000.00')
        )
        
        risk_limits_2 = risk_service.get_risk_limits(test_account.id, 'paper')
        
        # Breach timestamp should not change
        assert risk_limits_2.breached_at == first_breach_time
        assert risk_limits_2.is_breached is True
    
    def test_separate_breach_tracking_for_modes(self, risk_service, test_account):
        """Test that paper and live trading have separate breach tracking."""
        # Set limits for both modes
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='live',
            max_loss_limit=Decimal('30000.00')
        )
        
        # Breach paper trading limit
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        # Check live trading (not breached)
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='live',
            current_loss=Decimal('20000.00')
        )
        
        # Verify separate breach status
        paper_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        live_limits = risk_service.get_risk_limits(test_account.id, 'live')
        
        assert paper_limits.is_breached is True
        assert live_limits.is_breached is False


class TestConcurrentStrategyLimitEnforcement:
    """Test concurrent strategy limit enforcement in detail."""
    
    def test_enforce_limit_raises_error_when_limit_reached(self, risk_service, test_account, test_user):
        """Test that enforce_limit raises ValueError when limit is reached."""
        # Set a low limit
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=0,
            updated_by=test_user.id
        )
        
        # Try to enforce limit
        with pytest.raises(ValueError) as exc_info:
            risk_service.enforce_limit(
                account_id=test_account.id,
                trading_mode='paper'
            )
        
        assert "concurrent strategy limit reached" in str(exc_info.value)
    
    def test_can_activate_returns_false_when_limit_reached(self, risk_service, test_account, test_user):
        """Test that can_activate_strategy returns False when limit is reached."""
        # Set limit to 0
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=0,
            updated_by=test_user.id
        )
        
        # Check if can activate
        can_activate, error_msg = risk_service.can_activate_strategy(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert can_activate is False
        assert error_msg is not None
        assert "concurrent strategy limit reached" in error_msg
        assert "(0/0)" in error_msg
    
    def test_can_activate_returns_true_when_under_limit(self, risk_service, test_account, test_user):
        """Test that can_activate_strategy returns True when under limit."""
        # Set limit to 10
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=10,
            updated_by=test_user.id
        )
        
        # Check if can activate (active count is 0)
        can_activate, error_msg = risk_service.can_activate_strategy(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        assert can_activate is True
        assert error_msg is None
    
    def test_strategy_limit_update_takes_effect_immediately(self, risk_service, test_account, test_user):
        """Test that updating strategy limit takes effect immediately."""
        # Set initial limit
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=5,
            updated_by=test_user.id
        )
        
        # Verify initial limit
        limit_1 = risk_service.get_strategy_limit('paper')
        assert limit_1['max_concurrent_strategies'] == 5
        
        # Update limit
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=10,
            updated_by=test_user.id
        )
        
        # Verify updated limit
        limit_2 = risk_service.get_strategy_limit('paper')
        assert limit_2['max_concurrent_strategies'] == 10
    
    def test_separate_limits_enforced_independently(self, risk_service, test_account, test_user):
        """Test that paper and live limits are enforced independently."""
        # Set different limits
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=10,
            updated_by=test_user.id
        )
        risk_service.set_global_strategy_limit(
            trading_mode='live',
            max_concurrent_strategies=0,
            updated_by=test_user.id
        )
        
        # Paper trading should allow activation
        can_activate_paper, _ = risk_service.can_activate_strategy(
            account_id=test_account.id,
            trading_mode='paper'
        )
        assert can_activate_paper is True
        
        # Live trading should block activation
        can_activate_live, error_msg = risk_service.can_activate_strategy(
            account_id=test_account.id,
            trading_mode='live'
        )
        assert can_activate_live is False
        assert error_msg is not None


class TestSeparateLimitsForPaperAndLive:
    """Test that paper and live trading have completely separate limits."""
    
    def test_loss_limits_independent_between_modes(self, risk_service, test_account):
        """Test that loss limits are completely independent between modes."""
        # Set different limits
        paper_result = risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        live_result = risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='live',
            max_loss_limit=Decimal('100000.00')
        )
        
        # Verify separate limits
        assert paper_result.max_loss_limit == Decimal('50000.00')
        assert live_result.max_loss_limit == Decimal('100000.00')
        
        # Breach paper limit
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        
        # Update live loss (not breached)
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='live',
            current_loss=Decimal('80000.00')
        )
        
        # Verify independent tracking
        paper_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        live_limits = risk_service.get_risk_limits(test_account.id, 'live')
        
        assert paper_limits.is_breached is True
        assert paper_limits.current_loss == Decimal('60000.00')
        assert live_limits.is_breached is False
        assert live_limits.current_loss == Decimal('80000.00')
    
    def test_strategy_limits_independent_between_modes(self, risk_service, test_user):
        """Test that strategy limits are completely independent between modes."""
        # Set different limits
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=10,
            updated_by=test_user.id
        )
        risk_service.set_global_strategy_limit(
            trading_mode='live',
            max_concurrent_strategies=3,
            updated_by=test_user.id
        )
        
        # Verify separate limits
        paper_limit = risk_service.get_strategy_limit('paper')
        live_limit = risk_service.get_strategy_limit('live')
        
        assert paper_limit['max_concurrent_strategies'] == 10
        assert live_limit['max_concurrent_strategies'] == 3
        
        # Update one limit
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=15,
            updated_by=test_user.id
        )
        
        # Verify only paper limit changed
        paper_limit_updated = risk_service.get_strategy_limit('paper')
        live_limit_unchanged = risk_service.get_strategy_limit('live')
        
        assert paper_limit_updated['max_concurrent_strategies'] == 15
        assert live_limit_unchanged['max_concurrent_strategies'] == 3
    
    def test_acknowledgement_independent_between_modes(self, risk_service, test_account):
        """Test that breach acknowledgement is independent between modes."""
        # Set limits for both modes
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='live',
            max_loss_limit=Decimal('50000.00')
        )
        
        # Breach both limits
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='live',
            current_loss=Decimal('60000.00')
        )
        
        # Acknowledge only paper breach
        risk_service.acknowledge_limit_breach(
            account_id=test_account.id,
            trading_mode='paper'
        )
        
        # Verify independent acknowledgement
        paper_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        live_limits = risk_service.get_risk_limits(test_account.id, 'live')
        
        assert paper_limits.acknowledged is True
        assert live_limits.acknowledged is False


class TestIntegration:
    """Integration tests for risk management."""
    
    def test_loss_limit_workflow(self, risk_service, test_account):
        """Test complete loss limit workflow."""
        # 1. Set initial limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # 2. Check limit (not breached)
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('30000.00')
        )
        assert is_breached is False
        
        # 3. Check limit (breached)
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        assert is_breached is True
        
        # 4. Acknowledge and increase limit
        result = risk_service.acknowledge_limit_breach(
            account_id=test_account.id,
            trading_mode='paper',
            new_limit=Decimal('75000.00')
        )
        assert result.is_breached is False
        assert result.max_loss_limit == Decimal('75000.00')
    
    def test_complete_risk_management_workflow(self, risk_service, test_account, test_user):
        """Test complete workflow with both loss and strategy limits."""
        # 1. Set loss limit
        risk_service.set_max_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            max_loss_limit=Decimal('50000.00')
        )
        
        # 2. Set strategy limit
        risk_service.set_global_strategy_limit(
            trading_mode='paper',
            max_concurrent_strategies=5,
            updated_by=test_user.id
        )
        
        # 3. Check if can activate strategy (should be allowed)
        can_activate, _ = risk_service.can_activate_strategy(
            account_id=test_account.id,
            trading_mode='paper'
        )
        assert can_activate is True
        
        # 4. Simulate trading loss
        is_breached = risk_service.check_loss_limit(
            account_id=test_account.id,
            trading_mode='paper',
            current_loss=Decimal('60000.00')
        )
        assert is_breached is True
        
        # 5. Verify breach was recorded
        risk_limits = risk_service.get_risk_limits(test_account.id, 'paper')
        assert risk_limits.is_breached is True
        assert risk_limits.acknowledged is False
        
        # 6. Acknowledge and update limit
        result = risk_service.acknowledge_limit_breach(
            account_id=test_account.id,
            trading_mode='paper',
            new_limit=Decimal('80000.00')
        )
        assert result.is_breached is False
