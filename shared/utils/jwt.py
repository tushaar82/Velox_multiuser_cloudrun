"""
JWT token utilities for authentication.
Provides token generation, validation, and decoding.
"""
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from shared.config import get_settings

logger = logging.getLogger(__name__)


def generate_token(user_id: UUID, role: str, expiration_hours: Optional[int] = None) -> str:
    """
    Generate a JWT token for a user.
    
    Args:
        user_id: User's unique identifier
        role: User's role (admin, trader, investor)
        expiration_hours: Token expiration in hours (defaults to settings)
        
    Returns:
        JWT token as string
    """
    settings = get_settings()
    
    if expiration_hours is None:
        expiration_hours = settings.jwt_expiration_hours
    
    expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)
    
    payload = {
        'user_id': str(user_id),
        'role': role,
        'exp': expires_at,
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def verify_token(token: str) -> bool:
    """
    Verify if a token is valid.
    
    Args:
        token: JWT token to verify
        
    Returns:
        True if token is valid, False otherwise
    """
    return decode_token(token) is not None


def get_token_expiration(expiration_hours: Optional[int] = None) -> datetime:
    """
    Calculate token expiration datetime.
    
    Args:
        expiration_hours: Hours until expiration (defaults to settings)
        
    Returns:
        Expiration datetime
    """
    settings = get_settings()
    
    if expiration_hours is None:
        expiration_hours = settings.jwt_expiration_hours
    
    return datetime.utcnow() + timedelta(hours=expiration_hours)
