"""
Unit tests for authentication service.
Tests user registration, login, session management, and account locking.
"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models import User, Session as SessionModel, UserRole
from shared.config import get_settings
from api_gateway.auth_service import (
    AuthService,
    InvalidCredentialsError,
    AccountLockedError,
    PasswordValidationError
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def auth_service(db_session):
    """Create an AuthService instance with test database."""
    return AuthService(db_session)


class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_valid_user(self, auth_service):
        """Test registering a user with valid credentials."""
        user = auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        
        assert user.email == "test@example.com"
        assert user.role == UserRole.TRADER
        assert user.is_locked is False
        assert user.failed_login_attempts == 0
        assert user.password_hash != "SecurePass123!"  # Password should be hashed
    
    def test_register_email_normalization(self, auth_service):
        """Test that email is normalized to lowercase."""
        user = auth_service.register(
            email="Test@EXAMPLE.COM",
            password="SecurePass123!"
        )
        
        assert user.email == "test@example.com"
    
    def test_register_weak_password(self, auth_service):
        """Test registration with weak password fails."""
        with pytest.raises(PasswordValidationError) as exc_info:
            auth_service.register(
                email="test@example.com",
                password="weak"
            )
        
        assert "at least 8 characters" in str(exc_info.value)
    
    def test_register_password_no_uppercase(self, auth_service):
        """Test registration fails without uppercase letter."""
        with pytest.raises(PasswordValidationError) as exc_info:
            auth_service.register(
                email="test@example.com",
                password="securepass123!"
            )
        
        assert "uppercase letter" in str(exc_info.value)
    
    def test_register_password_no_number(self, auth_service):
        """Test registration fails without number."""
        with pytest.raises(PasswordValidationError) as exc_info:
            auth_service.register(
                email="test@example.com",
                password="SecurePass!"
            )
        
        assert "number" in str(exc_info.value)
    
    def test_register_password_no_special_char(self, auth_service):
        """Test registration fails without special character."""
        with pytest.raises(PasswordValidationError) as exc_info:
            auth_service.register(
                email="test@example.com",
                password="SecurePass123"
            )
        
        assert "special character" in str(exc_info.value)
    
    def test_register_duplicate_email(self, auth_service):
        """Test registration with duplicate email fails."""
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        with pytest.raises(Exception):  # IntegrityError
            auth_service.register(
                email="test@example.com",
                password="AnotherPass123!"
            )


class TestUserLogin:
    """Test user login functionality."""
    
    def test_login_valid_credentials(self, auth_service):
        """Test login with correct credentials."""
        # Register user
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Login
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!",
            ip_address="127.0.0.1",
            user_agent="Test Agent"
        )
        
        assert user.email == "test@example.com"
        assert token is not None
        assert len(token) > 0
    
    def test_login_invalid_email(self, auth_service):
        """Test login with non-existent email."""
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email="nonexistent@example.com",
                password="SecurePass123!"
            )
    
    def test_login_invalid_password(self, auth_service):
        """Test login with incorrect password."""
        # Register user
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Try login with wrong password
        with pytest.raises(InvalidCredentialsError):
            auth_service.login(
                email="test@example.com",
                password="WrongPass123!"
            )
    
    def test_login_case_insensitive_email(self, auth_service):
        """Test login with different email case."""
        # Register user
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Login with uppercase email
        user, token = auth_service.login(
            email="TEST@EXAMPLE.COM",
            password="SecurePass123!"
        )
        
        assert user.email == "test@example.com"


class TestAccountLocking:
    """Test account locking functionality."""
    
    def test_account_locks_after_max_attempts(self, auth_service, db_session):
        """Test account locks after maximum failed login attempts."""
        settings = get_settings()
        
        # Register user
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Make failed login attempts
        for i in range(settings.max_login_attempts):
            try:
                auth_service.login(
                    email="test@example.com",
                    password="WrongPass123!"
                )
            except InvalidCredentialsError:
                pass
        
        # Verify account is locked
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        assert user.is_locked is True
        assert user.locked_at is not None
        
        # Next login attempt should raise AccountLockedError
        with pytest.raises(AccountLockedError):
            auth_service.login(
                email="test@example.com",
                password="SecurePass123!"
            )
    
    def test_failed_attempts_reset_on_success(self, auth_service, db_session):
        """Test failed attempts counter resets on successful login."""
        # Register user
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Make some failed attempts
        for i in range(2):
            try:
                auth_service.login(
                    email="test@example.com",
                    password="WrongPass123!"
                )
            except InvalidCredentialsError:
                pass
        
        # Successful login
        auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Verify failed attempts reset
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        assert user.failed_login_attempts == 0
    
    def test_account_auto_unlocks_after_duration(self, auth_service, db_session):
        """Test account automatically unlocks after lock duration."""
        settings = get_settings()
        
        # Register user
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Lock account manually
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        user.is_locked = True
        user.locked_at = datetime.utcnow() - timedelta(minutes=settings.account_lock_duration_minutes + 1)
        db_session.commit()
        
        # Login should succeed (auto-unlock)
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        assert user.is_locked is False
        assert user.locked_at is None


class TestSessionManagement:
    """Test session validation and management."""
    
    def test_validate_valid_session(self, auth_service, db_session):
        """Test validating a valid session."""
        # Register and login
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Validate session
        validated_user = auth_service.validate_session(token)
        
        assert validated_user is not None
        assert validated_user.id == user.id
    
    def test_validate_invalid_token(self, auth_service):
        """Test validating an invalid token."""
        validated_user = auth_service.validate_session("invalid_token")
        
        assert validated_user is None
    
    def test_session_timeout_after_inactivity(self, auth_service, db_session):
        """Test session times out after inactivity period."""
        settings = get_settings()
        
        # Register and login
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Manually set last_activity to past timeout
        session = db_session.query(SessionModel).filter(SessionModel.token == token).first()
        session.last_activity = datetime.utcnow() - timedelta(minutes=settings.session_timeout_minutes + 1)
        db_session.commit()
        
        # Validate session should fail
        validated_user = auth_service.validate_session(token)
        
        assert validated_user is None
    
    def test_refresh_session(self, auth_service, db_session):
        """Test refreshing session updates last_activity."""
        # Register and login
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Get initial last_activity
        session = db_session.query(SessionModel).filter(SessionModel.token == token).first()
        initial_activity = session.last_activity
        
        # Wait a moment and refresh
        import time
        time.sleep(0.1)
        
        success = auth_service.refresh_session(token)
        
        assert success is True
        
        # Verify last_activity updated
        db_session.refresh(session)
        assert session.last_activity > initial_activity
    
    def test_logout_invalidates_session(self, auth_service, db_session):
        """Test logout removes session from database."""
        # Register and login
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Logout
        success = auth_service.logout(token)
        
        assert success is True
        
        # Verify session removed
        session = db_session.query(SessionModel).filter(SessionModel.token == token).first()
        assert session is None
        
        # Validate session should fail
        validated_user = auth_service.validate_session(token)
        assert validated_user is None


class TestJWTTokenValidation:
    """Test JWT token generation and validation."""
    
    def test_token_contains_user_info(self, auth_service):
        """Test JWT token contains user ID and role."""
        from shared.utils.jwt import decode_token
        
        # Register and login
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!",
            role=UserRole.TRADER
        )
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Decode token
        payload = decode_token(token)
        
        assert payload is not None
        assert payload['user_id'] == str(user.id)
        assert payload['role'] == UserRole.TRADER.value
    
    def test_token_expiration(self, auth_service, db_session):
        """Test token expires after expiration time."""
        # Register and login
        auth_service.register(
            email="test@example.com",
            password="SecurePass123!"
        )
        user, token = auth_service.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Manually set session expiration to past
        session = db_session.query(SessionModel).filter(SessionModel.token == token).first()
        session.expires_at = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()
        
        # Validate session should fail
        validated_user = auth_service.validate_session(token)
        
        assert validated_user is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
