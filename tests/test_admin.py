"""
Unit tests for admin dashboard and monitoring functionality.
Tests admin data aggregation, access control, and user management.
"""
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from api_gateway.admin_service import (
    AdminService,
    UnauthorizedAdminAccessError,
    AdminServiceError
)
from shared.models import (
    User, UserAccount, Order, Trade, Position,
    UserRole, OrderStatus, OrderSide, OrderType, TradingMode, PositionSide
)


@pytest.fixture
def db_session():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User(
        id=uuid.uuid4(),
        email='admin@test.com',
        password_hash='hashed',
        role=UserRole.ADMIN,
        is_locked=False,
        failed_login_attempts=0
    )


@pytest.fixture
def trader_user():
    """Create a trader user."""
    return User(
        id=uuid.uuid4(),
        email='trader@test.com',
        password_hash='hashed',
        role=UserRole.TRADER,
        is_locked=False,
        failed_login_attempts=0
    )


@pytest.fixture
def investor_user():
    """Create an investor user."""
    return User(
        id=uuid.uuid4(),
        email='investor@test.com',
        password_hash='hashed',
        role=UserRole.INVESTOR,
        is_locked=False,
        failed_login_attempts=0
    )


class TestAdminService:
    """Test admin service functionality."""
    
    def test_verify_admin_success(self, db_session, admin_user):
        """Test admin verification succeeds for admin user."""
        db_session.query.return_value.filter.return_value.first.return_value = admin_user
        
        service = AdminService(db_session)
        result = service._verify_admin(str(admin_user.id))
        
        assert result == admin_user
    
    def test_verify_admin_fails_for_non_admin(self, db_session, trader_user):
        """Test admin verification fails for non-admin user."""
        db_session.query.return_value.filter.return_value.first.return_value = trader_user
        
        service = AdminService(db_session)
        
        with pytest.raises(UnauthorizedAdminAccessError):
            service._verify_admin(str(trader_user.id))
    
    def test_verify_admin_fails_for_nonexistent_user(self, db_session):
        """Test admin verification fails for nonexistent user."""
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        service = AdminService(db_session)
        
        with pytest.raises(UnauthorizedAdminAccessError):
            service._verify_admin(str(uuid.uuid4()))
    
    def test_get_active_user_count_by_role(self, db_session, admin_user):
        """Test getting user count by role."""
        # Mock admin verification
        db_session.query.return_value.filter.return_value.first.return_value = admin_user
        
        # Mock user count query
        mock_counts = [
            (UserRole.ADMIN, 2),
            (UserRole.TRADER, 10),
            (UserRole.INVESTOR, 5)
        ]
        db_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_counts
        
        service = AdminService(db_session)
        result = service.get_active_user_count_by_role(str(admin_user.id))
        
        assert result['admin'] == 2
        assert result['trader'] == 10
        assert result['investor'] == 5
        assert result['total'] == 17
    
    @patch('api_gateway.admin_service.psutil')
    def test_get_system_resource_utilization(self, mock_psutil, db_session, admin_user):
        """Test getting system resource utilization."""
        # Mock admin verification
        db_session.query.return_value.filter.return_value.first.return_value = admin_user
        
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.cpu_count.return_value = 4
        
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.used = 8 * (1024 ** 3)  # 8 GB
        mock_memory.total = 16 * (1024 ** 3)  # 16 GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_disk.used = 100 * (1024 ** 3)  # 100 GB
        mock_disk.total = 500 * (1024 ** 3)  # 500 GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        service = AdminService(db_session)
        result = service.get_system_resource_utilization(str(admin_user.id))
        
        assert result['cpu']['percent'] == 45.5
        assert result['cpu']['count'] == 4
        assert result['memory']['percent'] == 60.0
        assert result['memory']['used_gb'] == 8.0
        assert result['disk']['percent'] == 70.0
    
    def test_get_total_orders_processed(self, db_session, admin_user):
        """Test getting total orders processed."""
        # Mock admin verification
        db_session.query.return_value.filter.return_value.first.return_value = admin_user
        
        # Mock order count
        mock_query = Mock()
        mock_query.count.return_value = 100
        
        # Mock status counts
        mock_status_counts = [
            (OrderStatus.FILLED, 80),
            (OrderStatus.CANCELLED, 15),
            (OrderStatus.REJECTED, 5)
        ]
        mock_query.with_entities.return_value.group_by.return_value.all.return_value = mock_status_counts
        
        # Mock mode counts
        mock_mode_counts = [
            (TradingMode.PAPER, 60),
            (TradingMode.LIVE, 40)
        ]
        
        db_session.query.return_value.filter.return_value = mock_query
        
        # Setup different return values for different calls
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_status_counts
            else:
                return mock_mode_counts
        
        mock_query.with_entities.return_value.group_by.return_value.all.side_effect = side_effect
        
        service = AdminService(db_session)
        result = service.get_total_orders_processed(str(admin_user.id), time_period='today')
        
        assert result['total_orders'] == 100
        assert result['by_status']['filled'] == 80
        assert result['by_trading_mode']['paper'] == 60
    
    def test_get_all_user_accounts_with_activity(self, db_session, admin_user, trader_user):
        """Test getting all user accounts with activity."""
        # Mock admin verification
        db_session.query.return_value.filter.return_value.first.return_value = admin_user
        
        # Mock account
        account = UserAccount(
            id=uuid.uuid4(),
            trader_id=trader_user.id,
            name='Test Account',
            is_active=True,
            created_at=datetime.utcnow()
        )
        account.trader = trader_user
        
        # Setup query mocks
        mock_account_query = Mock()
        mock_account_query.all.return_value = [account]
        
        # Mock scalar queries for counts
        mock_scalar_query = Mock()
        mock_scalar_query.scalar.return_value = 10
        
        # Mock P&L query
        mock_pnl = Mock()
        mock_pnl.realized = 1000.0
        mock_pnl.unrealized = 500.0
        mock_pnl_query = Mock()
        mock_pnl_query.first.return_value = mock_pnl
        
        # Setup query return values
        call_count = [0]
        def query_side_effect(model):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call for admin verification
                mock = Mock()
                mock.filter.return_value.first.return_value = admin_user
                return mock
            elif call_count[0] == 2:
                # Second call for accounts
                mock = Mock()
                mock.filter.return_value = mock_account_query
                return mock
            else:
                # Subsequent calls for counts and P&L
                mock = Mock()
                if 'sum' in str(model):
                    mock.filter.return_value = mock_pnl_query
                else:
                    mock.filter.return_value = mock_scalar_query
                return mock
        
        db_session.query.side_effect = query_side_effect
        
        service = AdminService(db_session)
        result = service.get_all_user_accounts_with_activity(str(admin_user.id))
        
        assert len(result) == 1
        assert result[0]['account_name'] == 'Test Account'
        assert result[0]['trader_email'] == trader_user.email
    
    def test_admin_cannot_execute_trades(self, db_session, admin_user):
        """Test that admin users cannot execute trades (read-only access)."""
        # This is enforced by the order service, not admin service
        # Admin service only provides read-only views
        
        # Mock admin verification
        db_session.query.return_value.filter.return_value.first.return_value = admin_user
        
        service = AdminService(db_session)
        
        # Admin can view account activity
        account_id = str(uuid.uuid4())
        
        # Mock account query
        account = UserAccount(
            id=uuid.UUID(account_id),
            trader_id=uuid.uuid4(),
            name='Test Account',
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Setup complex mock for multiple queries
        def query_side_effect(model):
            mock = Mock()
            if model == UserAccount:
                mock.filter.return_value.first.return_value = account
            else:
                mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            return mock
        
        db_session.query.side_effect = query_side_effect
        
        # This should succeed - admin can view
        result = service.get_account_trading_activity(
            str(admin_user.id),
            account_id
        )
        
        assert result['account_id'] == account_id
        assert 'orders' in result
        assert 'trades' in result
        assert 'positions' in result
    
    def test_generate_daily_activity_report(self, db_session, admin_user):
        """Test generating daily activity report."""
        # Mock admin verification
        db_session.query.return_value.filter.return_value.first.return_value = admin_user
        
        # Mock scalar queries
        mock_scalar_query = Mock()
        mock_scalar_query.scalar.return_value = 50
        
        db_session.query.return_value.filter.return_value = mock_scalar_query
        
        service = AdminService(db_session)
        report_date = datetime.utcnow() - timedelta(days=1)
        result = service.generate_daily_activity_report(str(admin_user.id), report_date=report_date)
        
        assert 'report_date' in result
        assert 'user_activity' in result
        assert 'order_activity' in result
        assert 'trade_activity' in result
        assert 'pnl' in result


class TestAdminAccessControl:
    """Test admin access control."""
    
    def test_trader_cannot_access_admin_functions(self, db_session, trader_user):
        """Test that trader users cannot access admin functions."""
        db_session.query.return_value.filter.return_value.first.return_value = trader_user
        
        service = AdminService(db_session)
        
        with pytest.raises(UnauthorizedAdminAccessError):
            service.get_active_user_count_by_role(str(trader_user.id))
    
    def test_investor_cannot_access_admin_functions(self, db_session, investor_user):
        """Test that investor users cannot access admin functions."""
        db_session.query.return_value.filter.return_value.first.return_value = investor_user
        
        service = AdminService(db_session)
        
        with pytest.raises(UnauthorizedAdminAccessError):
            service.get_system_resource_utilization(str(investor_user.id))


class TestUserManagement:
    """Test admin user management functions."""
    
    def test_admin_can_disable_user(self, db_session, admin_user, trader_user):
        """Test admin can disable user accounts."""
        from api_gateway.user_service import UserService
        
        # Ensure trader is not locked initially
        trader_user.is_locked = False
        
        # Mock queries
        def query_side_effect(model):
            mock = Mock()
            if model == User:
                # First call returns admin, second returns trader
                call_count = [0]
                def filter_side_effect(*args):
                    call_count[0] += 1
                    result_mock = Mock()
                    if call_count[0] == 1:
                        result_mock.first.return_value = admin_user
                    else:
                        result_mock.first.return_value = trader_user
                    return result_mock
                mock.filter.side_effect = filter_side_effect
            return mock
        
        db_session.query.side_effect = query_side_effect
        
        service = UserService(db_session)
        result = service.disable_user(str(trader_user.id), str(admin_user.id))
        
        assert result is True
        # The service modifies the user object
        assert trader_user.is_locked is True
        assert trader_user.locked_at is not None
    
    def test_admin_can_enable_user(self, db_session, admin_user, trader_user):
        """Test admin can enable user accounts."""
        from api_gateway.user_service import UserService
        
        # Set trader as locked initially
        trader_user.is_locked = True
        trader_user.failed_login_attempts = 3
        
        # Mock queries
        def query_side_effect(model):
            mock = Mock()
            if model == User:
                call_count = [0]
                def filter_side_effect(*args):
                    call_count[0] += 1
                    result_mock = Mock()
                    if call_count[0] == 1:
                        result_mock.first.return_value = admin_user
                    else:
                        result_mock.first.return_value = trader_user
                    return result_mock
                mock.filter.side_effect = filter_side_effect
            return mock
        
        db_session.query.side_effect = query_side_effect
        
        service = UserService(db_session)
        result = service.enable_user(str(trader_user.id), str(admin_user.id))
        
        assert result is True
        # The service modifies the user object
        assert trader_user.is_locked is False
        assert trader_user.locked_at is None
        assert trader_user.failed_login_attempts == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
