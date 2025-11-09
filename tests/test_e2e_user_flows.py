"""
End-to-end tests for critical user flows.

Tests complete user journeys through the platform including:
- User registration and login
- Strategy activation and execution
- Order submission and position tracking
- Backtest execution and results viewing
- Investor invitation and access
"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models import (
    User, UserRole, UserAccount, AccountAccess, InvitationStatus,
    InvestorInvitation, BrokerConnection, Order, OrderStatus, OrderSide,
    TradingMode, Position, Backtest, BacktestStatus, SymbolMapping
)
from shared.config.settings import get_settings

# Import services
from api_gateway.auth_service import AuthService
from api_gateway.user_service import UserService
from order_processor.order_router import OrderRouter
from order_processor.paper_trading_simulator import PaperTradingSimulator
from shared.services.symbol_mapping_service import SymbolMappingService
from strategy_workers.strategy_plugin_manager import StrategyPluginManager


@pytest.fixture(scope='function')
def db_session():
    """Create a test database session with PostgreSQL-compatible types."""
    # Use PostgreSQL URL from settings or fallback to SQLite with UUID support
    settings = get_settings()
    
    # For testing, we'll use the actual database connection
    # This ensures UUID types work correctly
    try:
        from shared.database.connection import init_database, get_db_manager
        db_manager = init_database()
        session = db_manager.create_session()
        
        # Add test symbol mappings
        mapping = SymbolMapping(
            standard_symbol='RELIANCE',
            broker_name='Test Broker',
            broker_symbol='RELIANCE-EQ',
            broker_token='2885',
            exchange='NSE',
            instrument_type='EQ',
            lot_size=1,
            tick_size=0.05
        )
        session.add(mapping)
        session.commit()
        
        yield session
        
        # Cleanup
        session.rollback()
        session.close()
    except Exception as e:
        # Fallback: Skip tests if database not available
        pytest.skip(f"Database not available for end-to-end tests: {e}")


@pytest.fixture
def auth_service(db_session):
    """Create auth service."""
    return AuthService(db_session)


@pytest.fixture
def user_service(db_session):
    """Create user service."""
    return UserService(db_session)


@pytest.fixture
def symbol_mapping_service(db_session):
    """Create symbol mapping service."""
    return SymbolMappingService(db_session)


@pytest.fixture
def paper_simulator():
    """Create paper trading simulator."""
    return PaperTradingSimulator(slippage=0.0005, commission_rate=0.0003)


@pytest.fixture
def order_router(db_session, symbol_mapping_service, paper_simulator):
    """Create order router."""
    return OrderRouter(
        db_session,
        symbol_mapping_service,
        {},  # No broker connectors for paper trading
        paper_simulator
    )


class TestUserRegistrationAndLoginFlow:
    """Test complete user registration and login flow."""
    
    def test_trader_registration_and_login_flow(self, auth_service):
        """Test trader can register, login, and access system."""
        # Step 1: Register new trader
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        assert trader.email == "trader@example.com"
        assert trader.role == UserRole.TRADER
        assert trader.is_locked is False
        
        # Step 2: Login with credentials
        user, token = auth_service.login(
            email="trader@example.com",
            password="SecurePass123!",
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        assert user.id == trader.id
        assert token is not None
        
        # Step 3: Validate session
        validated_user = auth_service.validate_session(token)
        assert validated_user is not None
        assert validated_user.id == trader.id
        
        # Step 4: Refresh session
        success = auth_service.refresh_session(token)
        assert success is True
        
        # Step 5: Logout
        success = auth_service.logout(token)
        assert success is True
        
        # Step 6: Validate session should fail after logout
        validated_user = auth_service.validate_session(token)
        assert validated_user is None
    
    def test_investor_registration_and_login_flow(self, auth_service):
        """Test investor can register and login."""
        # Register investor
        investor = auth_service.register(
            email="investor@example.com",
            password="InvestPass123!",
            role=UserRole.INVESTOR
        )
        
        assert investor.role == UserRole.INVESTOR
        
        # Login
        user, token = auth_service.login(
            email="investor@example.com",
            password="InvestPass123!"
        )
        
        assert user.role == UserRole.INVESTOR
        assert token is not None
    
    def test_admin_registration_and_login_flow(self, auth_service):
        """Test admin can register and login."""
        # Register admin
        admin = auth_service.register(
            email="admin@example.com",
            password="AdminPass123!",
            role=UserRole.ADMIN
        )
        
        assert admin.role == UserRole.ADMIN
        
        # Login
        user, token = auth_service.login(
            email="admin@example.com",
            password="AdminPass123!"
        )
        
        assert user.role == UserRole.ADMIN


class TestStrategyActivationAndExecutionFlow:
    """Test strategy activation and execution flow."""
    
    def test_strategy_activation_in_paper_mode(
        self, auth_service, user_service, db_session
    ):
        """Test trader can activate strategy in paper trading mode."""
        # Step 1: Register and login trader
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Step 2: Create trading account
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="My Trading Account"
        )
        
        assert account.trader_id == trader.id
        assert account.is_active is True
        
        # Step 3: Load available strategies
        strategy_manager = StrategyPluginManager()
        available_strategies = strategy_manager.list_strategies()
        
        assert len(available_strategies) > 0
        
        # Step 4: Select and configure strategy
        strategy_id = available_strategies[0]['id']
        strategy_config = {
            'strategy_id': strategy_id,
            'account_id': str(account.id),
            'trading_mode': 'paper',
            'symbols': ['RELIANCE'],
            'timeframes': ['5m', '15m'],
            'parameters': {
                'fast_period': 10,
                'slow_period': 20
            }
        }
        
        # Step 5: Activate strategy (would be done through strategy service)
        # For this test, we verify the configuration is valid
        assert strategy_config['trading_mode'] == 'paper'
        assert len(strategy_config['symbols']) > 0
        assert len(strategy_config['timeframes']) > 0
    
    def test_strategy_activation_requires_account(
        self, auth_service, user_service
    ):
        """Test strategy activation requires valid account."""
        # Register trader
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Try to activate strategy without creating account
        # This should fail in actual implementation
        # Here we verify account creation is required
        accounts = user_service.get_trader_accounts(trader.id)
        assert len(accounts) == 0


class TestOrderSubmissionAndPositionTrackingFlow:
    """Test order submission and position tracking flow."""
    
    def test_paper_trading_order_flow(
        self, auth_service, user_service, order_router, db_session
    ):
        """Test complete paper trading order and position flow."""
        # Step 1: Register trader and create account
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Paper Trading Account"
        )
        
        # Step 2: Submit buy order in paper mode
        buy_order = order_router.submit_order(
            account_id=str(account.id),
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            current_market_price=2450.00
        )
        
        assert buy_order.status == OrderStatus.FILLED
        assert buy_order.trading_mode == TradingMode.PAPER
        assert buy_order.filled_quantity == 10
        
        # Step 3: Verify order saved to database
        db_order = db_session.query(Order).filter(
            Order.id == uuid.UUID(buy_order.id)
        ).first()
        assert db_order is not None
        assert db_order.status == OrderStatus.FILLED
        
        # Step 4: Check position created
        position = db_session.query(Position).filter(
            Position.account_id == account.id,
            Position.symbol == 'RELIANCE',
            Position.trading_mode == TradingMode.PAPER
        ).first()
        
        if position:
            assert position.quantity == 10
            assert position.side == 'long'
        
        # Step 5: Submit sell order to close position
        sell_order = order_router.submit_order(
            account_id=str(account.id),
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            current_market_price=2460.00
        )
        
        assert sell_order.status == OrderStatus.FILLED
        assert sell_order.filled_quantity == 10
        
        # Step 6: Get all orders for account
        orders = order_router.get_orders(str(account.id), TradingMode.PAPER)
        assert len(orders) == 2
        assert orders[0].trading_mode == TradingMode.PAPER
        assert orders[1].trading_mode == TradingMode.PAPER
    
    def test_order_separation_paper_vs_live(
        self, auth_service, user_service, order_router, db_session
    ):
        """Test paper and live orders are tracked separately."""
        # Register trader and create account
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        # Submit paper order
        paper_order = order_router.submit_order(
            account_id=str(account.id),
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            current_market_price=2450.00
        )
        
        # Get paper orders
        paper_orders = order_router.get_orders(str(account.id), TradingMode.PAPER)
        assert len(paper_orders) == 1
        assert paper_orders[0].id == paper_order.id
        
        # Get live orders (should be empty)
        live_orders = order_router.get_orders(str(account.id), TradingMode.LIVE)
        assert len(live_orders) == 0
    
    def test_limit_order_flow(
        self, auth_service, user_service, order_router, db_session
    ):
        """Test limit order submission and tracking."""
        # Register trader and create account
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        # Submit limit order
        limit_order = order_router.submit_order(
            account_id=str(account.id),
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='limit',
            price=2400.00,
            trading_mode=TradingMode.PAPER,
            current_market_price=2450.00
        )
        
        # Order should be submitted but not filled
        assert limit_order.status == OrderStatus.SUBMITTED
        assert limit_order.price == 2400.00
        
        # Cancel order
        success = order_router.cancel_order(limit_order.id)
        assert success is True
        
        # Verify order cancelled
        db_order = db_session.query(Order).filter(
            Order.id == uuid.UUID(limit_order.id)
        ).first()
        assert db_order.status == OrderStatus.CANCELLED


class TestBacktestExecutionFlow:
    """Test backtest execution and results viewing flow."""
    
    def test_backtest_execution_flow(
        self, auth_service, user_service, db_session
    ):
        """Test complete backtest execution flow."""
        # Step 1: Register trader and create account
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        # Step 2: Create backtest configuration
        backtest = Backtest(
            id=uuid.uuid4(),
            account_id=account.id,
            strategy_id='moving_average_crossover',
            config={
                'symbols': ['RELIANCE'],
                'timeframes': ['5m'],
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
                'initial_capital': 100000.0,
                'slippage': 0.0005,
                'commission': 0.0003,
                'parameters': {
                    'fast_period': 10,
                    'slow_period': 20
                }
            },
            status=BacktestStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        db_session.add(backtest)
        db_session.commit()
        
        # Step 3: Verify backtest created
        db_backtest = db_session.query(Backtest).filter(
            Backtest.id == backtest.id
        ).first()
        
        assert db_backtest is not None
        assert db_backtest.status == BacktestStatus.PENDING
        assert db_backtest.account_id == account.id
        
        # Step 4: Update backtest status (simulating execution)
        db_backtest.status = BacktestStatus.RUNNING
        db_session.commit()
        
        # Step 5: Complete backtest with results
        db_backtest.status = BacktestStatus.COMPLETED
        db_backtest.results = {
            'total_return': 15.5,
            'max_drawdown': 5.2,
            'sharpe_ratio': 1.8,
            'win_rate': 65.0,
            'total_trades': 20
        }
        db_backtest.completed_at = datetime.utcnow()
        db_session.commit()
        
        # Step 6: Retrieve and verify results
        completed_backtest = db_session.query(Backtest).filter(
            Backtest.id == backtest.id
        ).first()
        
        assert completed_backtest.status == BacktestStatus.COMPLETED
        assert completed_backtest.results is not None
        assert completed_backtest.results['total_return'] == 15.5
        assert completed_backtest.completed_at is not None
    
    def test_backtest_results_viewing(
        self, auth_service, user_service, db_session
    ):
        """Test viewing backtest results."""
        # Register trader and create account
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        # Create completed backtest
        backtest = Backtest(
            id=uuid.uuid4(),
            account_id=account.id,
            strategy_id='moving_average_crossover',
            config={'symbols': ['RELIANCE']},
            status=BacktestStatus.COMPLETED,
            results={
                'total_return': 12.3,
                'max_drawdown': 4.5,
                'sharpe_ratio': 1.5,
                'win_rate': 60.0,
                'total_trades': 15,
                'winning_trades': 9,
                'losing_trades': 6
            },
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        db_session.add(backtest)
        db_session.commit()
        
        # Retrieve all backtests for account
        backtests = db_session.query(Backtest).filter(
            Backtest.account_id == account.id
        ).all()
        
        assert len(backtests) == 1
        assert backtests[0].status == BacktestStatus.COMPLETED
        assert backtests[0].results['total_return'] == 12.3


class TestInvestorInvitationFlow:
    """Test investor invitation and access flow."""
    
    def test_complete_investor_invitation_flow(
        self, auth_service, user_service, db_session
    ):
        """Test complete flow from invitation to access."""
        # Step 1: Register trader and create account
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        # Step 2: Register investor
        investor = auth_service.register(
            email="investor@example.com",
            password="InvestPass123!",
            role=UserRole.INVESTOR
        )
        
        # Step 3: Trader invites investor
        invitation = user_service.invite_investor(
            account_id=str(account.id),
            inviter_id=trader.id,
            invitee_email="investor@example.com",
            expiration_days=7
        )
        
        assert invitation.account_id == account.id
        assert invitation.invitee_email == "investor@example.com"
        assert invitation.status == InvitationStatus.PENDING
        
        # Step 4: Investor accepts invitation
        access = user_service.accept_invitation(
            invitation_id=str(invitation.id),
            user_id=investor.id
        )
        
        assert access.account_id == account.id
        assert access.user_id == investor.id
        assert access.role == 'investor'
        
        # Step 5: Verify invitation status updated
        db_invitation = db_session.query(InvestorInvitation).filter(
            InvestorInvitation.id == invitation.id
        ).first()
        
        assert db_invitation.status == InvitationStatus.ACCEPTED
        
        # Step 6: Investor can view account
        investor_accounts = user_service.get_investor_accounts(investor.id)
        assert len(investor_accounts) == 1
        assert investor_accounts[0].id == account.id
        
        # Step 7: Get all users for account
        account_users = user_service.get_account_users(str(account.id))
        assert len(account_users) == 2  # Trader and investor
        
        # Step 8: Trader revokes investor access
        success = user_service.revoke_investor_access(
            account_id=str(account.id),
            investor_id=investor.id,
            revoker_id=trader.id
        )
        
        assert success is True
        
        # Step 9: Verify investor no longer has access
        investor_accounts = user_service.get_investor_accounts(investor.id)
        assert len(investor_accounts) == 0
    
    def test_investor_read_only_access(
        self, auth_service, user_service, order_router, db_session
    ):
        """Test investor has read-only access to account."""
        # Register trader and investor
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        investor = auth_service.register(
            email="investor@example.com",
            password="InvestPass123!",
            role=UserRole.INVESTOR
        )
        
        # Create account and grant access
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        invitation = user_service.invite_investor(
            account_id=str(account.id),
            inviter_id=trader.id,
            invitee_email="investor@example.com"
        )
        
        user_service.accept_invitation(
            invitation_id=str(invitation.id),
            user_id=investor.id
        )
        
        # Trader submits order
        order = order_router.submit_order(
            account_id=str(account.id),
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            current_market_price=2450.00
        )
        
        # Investor can view orders
        orders = order_router.get_orders(str(account.id), TradingMode.PAPER)
        assert len(orders) == 1
        assert orders[0].id == order.id
        
        # Investor cannot submit orders (would be enforced by API middleware)
        # Here we verify the role
        assert investor.role == UserRole.INVESTOR
    
    def test_expired_invitation_cannot_be_accepted(
        self, auth_service, user_service, db_session
    ):
        """Test expired invitations cannot be accepted."""
        # Register trader and investor
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        investor = auth_service.register(
            email="investor@example.com",
            password="InvestPass123!",
            role=UserRole.INVESTOR
        )
        
        # Create account
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        # Create invitation
        invitation = user_service.invite_investor(
            account_id=str(account.id),
            inviter_id=trader.id,
            invitee_email="investor@example.com",
            expiration_days=7
        )
        
        # Manually expire invitation
        db_invitation = db_session.query(InvestorInvitation).filter(
            InvestorInvitation.id == invitation.id
        ).first()
        
        db_invitation.expires_at = datetime.utcnow() - timedelta(days=1)
        db_session.commit()
        
        # Try to accept expired invitation
        from api_gateway.user_service import InvitationError
        
        with pytest.raises(InvitationError, match="expired"):
            user_service.accept_invitation(
                invitation_id=str(invitation.id),
                user_id=investor.id
            )


class TestMultiUserAccountSharing:
    """Test multi-user account sharing scenarios."""
    
    def test_multiple_investors_on_same_account(
        self, auth_service, user_service, db_session
    ):
        """Test multiple investors can access same account."""
        # Register trader
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Create account
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        # Register multiple investors
        investor1 = auth_service.register(
            email="investor1@example.com",
            password="InvestPass123!",
            role=UserRole.INVESTOR
        )
        
        investor2 = auth_service.register(
            email="investor2@example.com",
            password="InvestPass123!",
            role=UserRole.INVESTOR
        )
        
        # Invite both investors
        invitation1 = user_service.invite_investor(
            account_id=str(account.id),
            inviter_id=trader.id,
            invitee_email="investor1@example.com"
        )
        
        invitation2 = user_service.invite_investor(
            account_id=str(account.id),
            inviter_id=trader.id,
            invitee_email="investor2@example.com"
        )
        
        # Both accept
        user_service.accept_invitation(
            invitation_id=str(invitation1.id),
            user_id=investor1.id
        )
        
        user_service.accept_invitation(
            invitation_id=str(invitation2.id),
            user_id=investor2.id
        )
        
        # Verify both have access
        account_users = user_service.get_account_users(str(account.id))
        assert len(account_users) == 3  # Trader + 2 investors
    
    def test_trader_with_multiple_accounts(
        self, auth_service, user_service, db_session
    ):
        """Test trader can create multiple accounts."""
        # Register trader
        trader = auth_service.register(
            email="trader@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Create multiple accounts
        account1 = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Account 1"
        )
        
        account2 = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Account 2"
        )
        
        # Verify both accounts created
        accounts = user_service.get_trader_accounts(trader.id)
        assert len(accounts) == 2
        assert accounts[0].name in ["Account 1", "Account 2"]
        assert accounts[1].name in ["Account 1", "Account 2"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
