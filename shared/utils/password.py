"""
Password hashing utilities using bcrypt.
Provides secure password hashing and verification.
"""
import bcrypt
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password as a string
        
    Raises:
        ValueError: If password is empty or invalid
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
    
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Hashed password to compare against
        
    Returns:
        True if password matches hash, False otherwise
    """
    if not password or not password_hash:
        return False
    
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def validate_password_strength(password: str, min_length: int = 8) -> tuple[bool, Optional[str]]:
    """
    Validate password strength according to requirements.
    
    Requirements:
    - Minimum length (default 8 characters)
    - At least one uppercase letter
    - At least one number
    - At least one special character
    
    Args:
        password: Password to validate
        min_length: Minimum required length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"
    
    return True, None
