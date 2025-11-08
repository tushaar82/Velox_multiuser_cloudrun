"""
Authentication and authorization middleware.
Provides decorators for protecting routes and checking permissions.
"""
import logging
from functools import wraps
from typing import List, Callable
from flask import request, jsonify

from shared.database.connection import get_db_session
from api_gateway.auth_service import AuthService

logger = logging.getLogger(__name__)


def require_auth(f: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    Validates JWT token and injects current_user and token into the route function.
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route(current_user, token):
            return jsonify({'user_id': str(current_user.id)})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header is required'}), 401
        
        # Extract token from "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        token = parts[1]
        
        # Validate session
        try:
            with get_db_session() as db:
                auth_service = AuthService(db)
                user = auth_service.validate_session(token)
            
            if not user:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Inject user and token into route function
            return f(current_user=user, token=token, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return jsonify({'error': 'Authentication failed'}), 401
    
    return decorated_function


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Decorator to require specific roles for a route.
    Must be used after @require_auth decorator.
    
    Args:
        allowed_roles: List of allowed role names (e.g., ['admin', 'trader'])
    
    Usage:
        @app.route('/admin')
        @require_auth
        @require_role(['admin'])
        def admin_route(current_user, token):
            return jsonify({'message': 'Admin access granted'})
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(current_user, token, *args, **kwargs):
            # Check if user has required role
            if current_user.role.value not in allowed_roles:
                logger.warning(
                    f"Access denied: User {current_user.email} with role "
                    f"{current_user.role.value} attempted to access route requiring {allowed_roles}"
                )
                return jsonify({
                    'error': 'Forbidden',
                    'message': f'This endpoint requires one of the following roles: {", ".join(allowed_roles)}'
                }), 403
            
            return f(current_user=current_user, token=token, *args, **kwargs)
        
        return decorated_function
    
    return decorator


def optional_auth(f: Callable) -> Callable:
    """
    Decorator for routes that optionally use authentication.
    If token is provided, validates it and injects current_user.
    If no token, current_user will be None.
    
    Usage:
        @app.route('/public')
        @optional_auth
        def public_route(current_user=None, token=None):
            if current_user:
                return jsonify({'message': f'Hello {current_user.email}'})
            return jsonify({'message': 'Hello guest'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            # No auth provided, continue without user
            return f(current_user=None, token=None, *args, **kwargs)
        
        # Extract token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            # Invalid format, continue without user
            return f(current_user=None, token=None, *args, **kwargs)
        
        token = parts[1]
        
        # Try to validate session
        try:
            with get_db_session() as db:
                auth_service = AuthService(db)
                user = auth_service.validate_session(token)
            
            return f(current_user=user, token=token, *args, **kwargs)
            
        except Exception as e:
            logger.warning(f"Optional auth validation failed: {e}")
            return f(current_user=None, token=None, *args, **kwargs)
    
    return decorated_function
