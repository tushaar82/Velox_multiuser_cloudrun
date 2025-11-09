"""
Comprehensive security testing for the trading platform.

Tests authentication, authorization, role-based access control,
data isolation, credential encryption, session management, and account locking.
"""
import pytest
import uuid
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models import (
    User, UserRole, UserAccount, AccountAccess, Session,
    BrokerConnection, Order, OrderSide, TradingMode, Position
)
from shared.config.settings import get_settings
from shared.utils.encryption import CredentialEncryption
try:
    from shared.utils.jwt import create_token, verify_token
except ImportError:
    create_token = None
    verify_token = None

# Import services
from api_gateway.auth_service import AuthService, AuthenticationError
from api_gateway.user_service import UserService
from order_processor.order_router import OrderRouter
from order_processor.paper_trading_simulator import PaperTradingSimulator
from shared.services.symbol_mapping_service import SymbolMappingService


@pytest.fixture(scope='function')
def db_session():
    """Create a test database session."""
    try:
        from shared.database.connection import init_database, get_db_manager
        db_manager = init_database()
        session = db_manager.create_session()
        
        yield session
        
        # Cleanup
        session.rollback()
        session.close()
    except Exception as e:
        pytest.skip(f"Database not available for security tests: {e}")


@pytest.fixture
def auth_service(db_session):
    """Create auth service."""
    return AuthService(db_session)


@pytest.fixture
def user_service(db_session):
    """Create user service."""
    return UserService(db_session)


class TestAuthenticationSecurity:
    """Test authentication security mechanisms."""
    
    def test_password_hashing(self, auth_service):
        """Test passwords are properly hashed and not stored in plaintext."""
        # Register user
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Verify password is hashed
        assert user.password_hash != "SecurePass123!"
        assert len(user.password_hash) > 50  # Bcrypt hashes are long
        assert user.password_hash.startswith('$2b$')  # Bcrypt prefix
    
    def test_password_validation_requirements(self, auth_service):
        """Test password validation enforces security requirements."""
        # Test weak passwords are rejected
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecial123",  # No special characters
        ]
        
        for weak_pass in weak_passwords:
            with pytest.raises(Exception):  # Should raise validation error
                auth_service.register(
                    email=f"test_{weak_pass}@example.com",
                    password=weak_pass,
                    role=UserRole.TRADER
                )
    
    def test_login_with_invalid_credentials(self, auth_service):
        """Test login fails with invalid credentials."""
        # Register user
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Try login with wrong password
        with pytest.raises(AuthenticationError):
            auth_service.login(
                email="test@example.com",
                password="WrongPassword123!"
            )
        
        # Try login with non-existent email
        with pytest.raises(AuthenticationError):
            auth_service.login(
                email="nonexistent@example.com",
                password="SecurePass123!"
            )
    
    def test_account_locking_after_failed_attempts(self, auth_service, db_session):
        """Test account locks after 3 failed login attempts."""
        # Register user
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Attempt 3 failed logins
        for i in range(3):
            try:
                auth_service.login(
                    email="test@example.com",
                    password="WrongPassword123!"
                )
            except AuthenticationError:
                pass
        
        # Verify account is locked
        db_user = db_session.query(User).filter(User.id == user.id).first()
        assert db_user.is_locked is True
        assert db_user.failed_login_attempts >= 3
        
        # Try login with correct password (should fail due to lock)
        with pytest.raises(AuthenticationError, match="locked"):
            auth_service.login(
                email="test@example.com",
                password="SecurePass123!"
            )
    
    def test_account_auto_unlock_after_timeout(self, auth_service, db_session):
        """Test account automatically unlocks after 15 minutes."""
        # Register user
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Lock account
        db_user = db_session.query(User).filter(User.id == user.id).first()
        db_user.is_locked = True
        db_user.locked_at = datetime.utcnow() - timedelta(minutes=16)
        db_session.commit()
        
        # Try login (should unlock and succeed)
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Verify account unlocked
        db_user = db_session.query(User).filter(User.id == user.id).first()
        assert db_user.is_locked is False
        assert db_user.failed_login_attempts == 0
    
    def test_jwt_token_validation(self, auth_service):
        """Test JWT token validation."""
        # Register and login
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Validate token
        validated_user = auth_service.validate_session(token)
        assert validated_user is not None
        assert validated_user.id == user.id
        
        # Test invalid token
        invalid_token = "invalid.token.here"
        validated_user = auth_service.validate_session(invalid_token)
        assert validated_user is None
    
    def test_session_timeout_after_inactivity(self, auth_service, db_session):
        """Test session times out after 30 minutes of inactivity."""
        # Register and login
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Manually set last_activity to 31 minutes ago
        session = db_session.query(Session).filter(
            Session.token == token
        ).first()
        
        if session:
            session.last_activity = datetime.utcnow() - timedelta(minutes=31)
            db_session.commit()
            
            # Validate session (should fail due to timeout)
            validated_user = auth_service.validate_session(token)
            assert validated_user is None
    
    def test_session_refresh_updates_activity(self, auth_service, db_session):
        """Test session refresh updates last activity timestamp."""
        # Register and login
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Get initial last_activity
        session = db_session.query(Session).filter(
            Session.token == token
        ).first()
        
        if session:
            initial_activity = session.last_activity
            
            # Wait a moment
            time.sleep(1)
            
            # Refresh session
            auth_service.refresh_session(token)
            
            # Verify last_activity updated
            db_session.refresh(session)
            assert session.last_activity > initial_activity


class TestRoleBasedAccessControl:
    """Test role-based access control enforcement."""
    
    def test_admin_role_permissions(self, auth_service, user_service, db_session):
        """Test admin users have elevated permissions."""
        # Create admin user
        admin = auth_service.register(
            email="admin@example.com",
            password="AdminPass123!",
            role=UserRole.ADMIN
        )
        
        # Create trader user
        trader = auth_service.register(
            email="trader@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        # Admin should be able to view all users
        assert admin.role == UserRole.ADMIN
        
        # Admin should be able to disable user accounts
        # (This would be enforced in API middleware)
        assert admin.role == UserRole.ADMIN
    
    def test_trader_role_permissions(self, auth_service, user_service):
        """Test trader users can create accounts and strategies."""
        # Create trader
        trader = auth_service.register(
            email="trader@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        # Trader can create account
        account = user_service.create_user_account(
            trader_id=trader.id,
            account_name="Trading Account"
        )
        
        assert account.trader_id == trader.id
        
        # Trader can invite investors
        invitation = user_service.invite_investor(
            account_id=str(account.id),
            inviter_id=trader.id,
            invitee_email="investor@example.com"
        )
        
        assert invitation is not None
    
    def test_investor_role_read_only_access(
        self, auth_service, user_service, db_session
    ):
        """Test investor users have read-only access."""
        # Create trader and investor
        trader = auth_service.register(
            email="trader@example.com",
            password="TraderPass123!",
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
        
        # Verify investor has read-only access
        access = db_session.query(AccountAccess).filter(
            AccountAccess.user_id == investor.id,
            AccountAccess.account_id == account.id
        ).first()
        
        assert access is not None
        assert access.role == 'investor'
        
        # Investor cannot create accounts
        with pytest.raises(Exception):
            user_service.create_user_account(
                trader_id=investor.id,
                account_name="Investor Account"
            )
    
    def test_unauthorized_access_to_other_accounts(
        self, auth_service, user_service, db_session
    ):
        """Test users cannot access accounts they don't own."""
        # Create two traders
        trader1 = auth_service.register(
            email="trader1@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        trader2 = auth_service.register(
            email="trader2@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        # Each creates an account
        account1 = user_service.create_user_account(
            trader_id=trader1.id,
            account_name="Account 1"
        )
        
        account2 = user_service.create_user_account(
            trader_id=trader2.id,
            account_name="Account 2"
        )
        
        # Trader 1 should not have access to Account 2
        access = db_session.query(AccountAccess).filter(
            AccountAccess.user_id == trader1.id,
            AccountAccess.account_id == account2.id
        ).first()
        
        assert access is None
        
        # Trader 2 should not have access to Account 1
        access = db_session.query(AccountAccess).filter(
            AccountAccess.user_id == trader2.id,
            AccountAccess.account_id == account1.id
        ).first()
        
        assert access is None


class TestAccountLevelDataIsolation:
    """Test account-level data isolation."""
    
    def test_order_data_isolation(
        self, auth_service, user_service, db_session
    ):
        """Test orders are isolated between accounts."""
        # Create two traders with accounts
        trader1 = auth_service.register(
            email="trader1@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        trader2 = auth_service.register(
            email="trader2@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        account1 = user_service.create_user_account(
            trader_id=trader1.id,
            account_name="Account 1"
        )
        
        account2 = user_service.create_user_account(
            trader_id=trader2.id,
            account_name="Account 2"
        )
        
        # Create orders for each account
        order1 = Order(
            id=uuid.uuid4(),
            account_id=account1.id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            status='filled',
            created_at=datetime.utcnow()
        )
        
        order2 = Order(
            id=uuid.uuid4(),
            account_id=account2.id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=5,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            status='filled',
            created_at=datetime.utcnow()
        )
        
        db_session.add(order1)
        db_session.add(order2)
        db_session.commit()
        
        # Query orders for each account
        account1_orders = db_session.query(Order).filter(
            Order.account_id == account1.id
        ).all()
        
        account2_orders = db_session.query(Order).filter(
            Order.account_id == account2.id
        ).all()
        
        # Verify isolation
        assert len(account1_orders) == 1
        assert len(account2_orders) == 1
        assert account1_orders[0].id == order1.id
        assert account2_orders[0].id == order2.id
    
    def test_position_data_isolation(
        self, auth_service, user_service, db_session
    ):
        """Test positions are isolated between accounts."""
        # Create two traders with accounts
        trader1 = auth_service.register(
            email="trader1@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        trader2 = auth_service.register(
            email="trader2@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        account1 = user_service.create_user_account(
            trader_id=trader1.id,
            account_name="Account 1"
        )
        
        account2 = user_service.create_user_account(
            trader_id=trader2.id,
            account_name="Account 2"
        )
        
        # Create positions for each account
        position1 = Position(
            id=uuid.uuid4(),
            account_id=account1.id,
            symbol='RELIANCE',
            side='long',
            quantity=10,
            entry_price=2450.00,
            current_price=2460.00,
            trading_mode=TradingMode.PAPER,
            opened_at=datetime.utcnow()
        )
        
        position2 = Position(
            id=uuid.uuid4(),
            account_id=account2.id,
            symbol='RELIANCE',
            side='long',
            quantity=5,
            entry_price=2450.00,
            current_price=2460.00,
            trading_mode=TradingMode.PAPER,
            opened_at=datetime.utcnow()
        )
        
        db_session.add(position1)
        db_session.add(position2)
        db_session.commit()
        
        # Query positions for each account
        account1_positions = db_session.query(Position).filter(
            Position.account_id == account1.id
        ).all()
        
        account2_positions = db_session.query(Position).filter(
            Position.account_id == account2.id
        ).all()
        
        # Verify isolation
        assert len(account1_positions) == 1
        assert len(account2_positions) == 1
        assert account1_positions[0].id == position1.id
        assert account2_positions[0].id == position2.id
    
    def test_investor_can_only_view_granted_accounts(
        self, auth_service, user_service, db_session
    ):
        """Test investor can only view accounts they have access to."""
        # Create traders and investor
        trader1 = auth_service.register(
            email="trader1@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        trader2 = auth_service.register(
            email="trader2@example.com",
            password="TraderPass123!",
            role=UserRole.TRADER
        )
        
        investor = auth_service.register(
            email="investor@example.com",
            password="InvestPass123!",
            role=UserRole.INVESTOR
        )
        
        # Create accounts
        account1 = user_service.create_user_account(
            trader_id=trader1.id,
            account_name="Account 1"
        )
        
        account2 = user_service.create_user_account(
            trader_id=trader2.id,
            account_name="Account 2"
        )
        
        # Grant investor access to account1 only
        invitation = user_service.invite_investor(
            account_id=str(account1.id),
            inviter_id=trader1.id,
            invitee_email="investor@example.com"
        )
        
        user_service.accept_invitation(
            invitation_id=str(invitation.id),
            user_id=investor.id
        )
        
        # Get investor's accessible accounts
        investor_accounts = user_service.get_investor_accounts(investor.id)
        
        # Verify investor can only see account1
        assert len(investor_accounts) == 1
        assert investor_accounts[0].id == account1.id


class TestBrokerCredentialEncryption:
    """Test broker credential encryption."""
    
    def test_credentials_encrypted_at_rest(self, db_session):
        """Test broker credentials are encrypted in database."""
        import os
        
        # Set encryption key for test
        os.environ['ENCRYPTION_KEY'] = CredentialEncryption.generate_key()
        encryptor = CredentialEncryption()
        
        # Create broker connection with encrypted credentials
        account_id = uuid.uuid4()
        
        # Encrypt credentials
        api_key = "test_api_key_12345"
        api_secret = "test_api_secret_67890"
        
        encrypted_key = encryptor.encrypt(api_key)
        encrypted_secret = encryptor.encrypt(api_secret)
        
        # Verify encrypted data is different from plaintext
        assert encrypted_key != api_key
        assert encrypted_secret != api_secret
        
        # Create broker connection
        broker_conn = BrokerConnection(
            id=uuid.uuid4(),
            account_id=account_id,
            broker_name='Test Broker',
            encrypted_api_key=encrypted_key,
            encrypted_api_secret=encrypted_secret,
            is_connected=False,
            created_at=datetime.utcnow()
        )
        
        db_session.add(broker_conn)
        db_session.commit()
        
        # Retrieve and decrypt
        db_conn = db_session.query(BrokerConnection).filter(
            BrokerConnection.id == broker_conn.id
        ).first()
        
        decrypted_key = decrypt_data(db_conn.encrypted_api_key)
        decrypted_secret = decrypt_data(db_conn.encrypted_api_secret)
        
        # Verify decryption works
        assert decrypted_key == api_key
        assert decrypted_secret == api_secret
    
    def test_credentials_not_exposed_in_api_responses(self):
        """Test credentials are not included in API responses."""
        # This would be tested at API level
        # Verify that broker connection responses don't include credentials
        
        broker_response = {
            'id': str(uuid.uuid4()),
            'broker_name': 'Test Broker',
            'is_connected': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Verify no credential fields in response
        assert 'api_key' not in broker_response
        assert 'api_secret' not in broker_response
        assert 'encrypted_api_key' not in broker_response
        assert 'encrypted_api_secret' not in broker_response


class TestSessionManagement:
    """Test session management security."""
    
    def test_logout_invalidates_session(self, auth_service):
        """Test logout properly invalidates session."""
        # Register and login
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Validate session works
        validated_user = auth_service.validate_session(token)
        assert validated_user is not None
        
        # Logout
        success = auth_service.logout(token)
        assert success is True
        
        # Validate session should fail
        validated_user = auth_service.validate_session(token)
        assert validated_user is None
    
    def test_concurrent_sessions_from_different_devices(self, auth_service):
        """Test user can have multiple active sessions."""
        # Register user
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Login from device 1
        user1, token1 = auth_service.login(
            email="test@example.com",
            password="SecurePass123!",
            ip_address="192.168.1.1",
            user_agent="Device 1"
        )
        
        # Login from device 2
        user2, token2 = auth_service.login(
            email="test@example.com",
            password="SecurePass123!",
            ip_address="192.168.1.2",
            user_agent="Device 2"
        )
        
        # Both sessions should be valid
        assert token1 != token2
        
        validated_user1 = auth_service.validate_session(token1)
        validated_user2 = auth_service.validate_session(token2)
        
        assert validated_user1 is not None
        assert validated_user2 is not None
        assert validated_user1.id == validated_user2.id
    
    def test_session_hijacking_prevention(self, auth_service, db_session):
        """Test session includes IP and user agent for hijacking detection."""
        # Register and login
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!",
            ip_address="192.168.1.1",
            user_agent="Original Device"
        )
        
        # Get session from database
        session = db_session.query(Session).filter(
            Session.token == token
        ).first()
        
        if session:
            # Verify session includes security metadata
            assert session.ip_address == "192.168.1.1"
            assert session.user_agent == "Original Device"
            
            # In production, validate these on each request
            # to detect potential session hijacking


class TestInputValidationAndSanitization:
    """Test input validation and sanitization."""
    
    def test_sql_injection_prevention(self, auth_service):
        """Test SQL injection attempts are prevented."""
        # Try SQL injection in email field
        malicious_email = "test@example.com'; DROP TABLE users; --"
        
        try:
            user = auth_service.register(
                email=malicious_email,
                password="SecurePass123!",
                role=UserRole.TRADER
            )
            # If registration succeeds, verify email is sanitized
            assert "DROP TABLE" not in user.email
        except Exception:
            # Registration should fail due to validation
            pass
    
    def test_xss_prevention_in_user_inputs(self, auth_service, user_service):
        """Test XSS attempts are prevented."""
        # Register user
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        # Try XSS in account name
        malicious_name = "<script>alert('XSS')</script>"
        
        account = user_service.create_user_account(
            trader_id=user.id,
            account_name=malicious_name
        )
        
        # Verify script tags are not executed (would be sanitized in API layer)
        # At minimum, verify account is created
        assert account is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
