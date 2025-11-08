"""
Authentication service for user registration, login, and session management.
Implements JWT-based authentication with session tracking and account locking.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from shared.config import get_settings
from shared.models import User, Session as SessionModel, UserRole
from shared.utils.password import hash_password, verify_password, validate_password_strength
from shared.utils.jwt import generate_token, decode_token, get_token_expiration

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""
    pass


class AccountLockedError(AuthenticationError):
    """Raised when account is locked."""
    pass


class PasswordValidationError(AuthenticationError):
    """Raised when password doesn't meet requirements."""
    pass


class AuthService:
    """Service for handling user authentication and session management."""
    
    def __init__(self, db_session: Session):
        """
        Initialize authentication service.
        
        Args:
            db_session: Database session for queries
        """
        self.db = db_session
        self.settings = get_settings()
    
    def register(
        self,
        email: str,
        password: str,
        role: UserRole = UserRole.TRADER
    ) -> User:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: Plain text password
            role: User role (default: TRADER)
            
        Returns:
            Created user object
            
        Raises:
            PasswordValidationError: If password doesn't meet requirements
            IntegrityError: If email already exists
        """
        # Validate password strength
        is_valid, error_msg = validate_password_strength(
            password,
            self.settings.password_min_length
        )
        if not is_valid:
            raise PasswordValidationError(error_msg)
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user
        user = User(
            id=uuid.uuid4(),
            email=email.lower().strip(),
            password_hash=password_hash,
            role=role,
            is_locked=False,
            failed_login_attempts=0
        )
        
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"User registered: {user.email} with role {role.value}")
            return user
        except IntegrityError:
            self.db.rollback()
            logger.warning(f"Registration failed: Email already exists - {email}")
            raise
    
    def login(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str]:
        """
        Authenticate user and create session.
        
        Args:
            email: User's email address
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent string
            
        Returns:
            Tuple of (user, token)
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AccountLockedError: If account is locked
        """
        # Find user by email
        user = self.db.query(User).filter(User.email == email.lower().strip()).first()
        
        if not user:
            logger.warning(f"Login failed: User not found - {email}")
            raise InvalidCredentialsError("Invalid email or password")
        
        # Check if account is locked
        if user.is_locked:
            # Check if lock duration has passed
            if user.locked_at:
                lock_duration = timedelta(minutes=self.settings.account_lock_duration_minutes)
                if datetime.utcnow() - user.locked_at < lock_duration:
                    logger.warning(f"Login failed: Account locked - {email}")
                    raise AccountLockedError(
                        f"Account is locked. Try again after {self.settings.account_lock_duration_minutes} minutes."
                    )
                else:
                    # Auto-unlock account
                    self._unlock_account(user)
        
        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if max attempts reached
            if user.failed_login_attempts >= self.settings.max_login_attempts:
                user.is_locked = True
                user.locked_at = datetime.utcnow()
                logger.warning(f"Account locked after {user.failed_login_attempts} failed attempts - {email}")
            
            self.db.commit()
            logger.warning(f"Login failed: Invalid password - {email}")
            raise InvalidCredentialsError("Invalid email or password")
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        self.db.commit()
        
        # Generate JWT token
        token = generate_token(user.id, user.role.value)
        
        # Create session
        session = SessionModel(
            token=token,
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=get_token_expiration(),
            last_activity=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(session)
        self.db.commit()
        
        logger.info(f"User logged in: {user.email}")
        return user, token
    
    def validate_session(self, token: str) -> Optional[User]:
        """
        Validate session token and check inactivity timeout.
        
        Args:
            token: JWT token to validate
            
        Returns:
            User object if session is valid, None otherwise
        """
        # Decode token
        payload = decode_token(token)
        if not payload:
            return None
        
        # Find session in database
        session = self.db.query(SessionModel).filter(SessionModel.token == token).first()
        if not session:
            logger.warning("Session not found in database")
            return None
        
        # Check if session has expired
        if datetime.utcnow() > session.expires_at:
            logger.info("Session expired")
            self.db.delete(session)
            self.db.commit()
            return None
        
        # Check inactivity timeout
        inactivity_timeout = timedelta(minutes=self.settings.session_timeout_minutes)
        if datetime.utcnow() - session.last_activity > inactivity_timeout:
            logger.info("Session timed out due to inactivity")
            self.db.delete(session)
            self.db.commit()
            return None
        
        # Get user
        user = self.db.query(User).filter(User.id == session.user_id).first()
        if not user:
            logger.warning("User not found for session")
            self.db.delete(session)
            self.db.commit()
            return None
        
        # Check if account is locked
        if user.is_locked:
            logger.warning(f"Account is locked: {user.email}")
            return None
        
        return user
    
    def refresh_session(self, token: str) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            token: JWT token
            
        Returns:
            True if session was refreshed, False otherwise
        """
        session = self.db.query(SessionModel).filter(SessionModel.token == token).first()
        if not session:
            return False
        
        session.last_activity = datetime.utcnow()
        self.db.commit()
        return True
    
    def logout(self, token: str) -> bool:
        """
        Invalidate session token.
        
        Args:
            token: JWT token to invalidate
            
        Returns:
            True if session was invalidated, False if not found
        """
        session = self.db.query(SessionModel).filter(SessionModel.token == token).first()
        if not session:
            return False
        
        user_email = session.user.email if session.user else "unknown"
        self.db.delete(session)
        self.db.commit()
        
        logger.info(f"User logged out: {user_email}")
        return True
    
    def lock_account(self, user_id: uuid.UUID) -> bool:
        """
        Lock a user account.
        
        Args:
            user_id: User ID to lock
            
        Returns:
            True if account was locked, False if user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_locked = True
        user.locked_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Account locked: {user.email}")
        return True
    
    def unlock_account(self, user_id: uuid.UUID) -> bool:
        """
        Unlock a user account (admin only).
        
        Args:
            user_id: User ID to unlock
            
        Returns:
            True if account was unlocked, False if user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        self._unlock_account(user)
        logger.info(f"Account unlocked: {user.email}")
        return True
    
    def _unlock_account(self, user: User) -> None:
        """
        Internal method to unlock account and reset failed attempts.
        
        Args:
            user: User object to unlock
        """
        user.is_locked = False
        user.locked_at = None
        user.failed_login_attempts = 0
        self.db.commit()
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from database.
        Should be run periodically as a background task.
        
        Returns:
            Number of sessions deleted
        """
        expired_sessions = self.db.query(SessionModel).filter(
            SessionModel.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_sessions)
        for session in expired_sessions:
            self.db.delete(session)
        
        self.db.commit()
        logger.info(f"Cleaned up {count} expired sessions")
        return count
