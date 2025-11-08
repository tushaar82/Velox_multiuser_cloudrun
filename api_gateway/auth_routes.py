"""
Authentication API routes.
Provides endpoints for registration, login, logout, and session management.
"""
import logging
from typing import Optional
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from shared.database.connection import get_db_session
from shared.models import UserRole
from api_gateway.auth_service import (
    AuthService,
    InvalidCredentialsError,
    AccountLockedError,
    PasswordValidationError
)
from api_gateway.middleware import require_auth, require_role

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Request body:
        {
            "email": "user@example.com",
            "password": "SecurePass123!",
            "role": "trader"  # Optional, defaults to "trader"
        }
    
    Returns:
        201: User created successfully
        400: Invalid input or password validation failed
        409: Email already exists
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email')
        password = data.get('password')
        role_str = data.get('role', 'trader')
        
        # Validate required fields
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Parse role
        try:
            role = UserRole[role_str.upper()]
        except KeyError:
            return jsonify({'error': f'Invalid role: {role_str}'}), 400
        
        # Register user
        with get_db_session() as db:
            auth_service = AuthService(db)
            user = auth_service.register(email, password, role)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'role': user.role.value
            }
        }), 201
        
    except PasswordValidationError as e:
        return jsonify({'error': str(e)}), 400
    except IntegrityError:
        return jsonify({'error': 'Email already exists'}), 409
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and create session.
    
    Request body:
        {
            "email": "user@example.com",
            "password": "SecurePass123!"
        }
    
    Returns:
        200: Login successful with token
        400: Invalid input
        401: Invalid credentials
        423: Account locked
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Get client info
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        # Authenticate user
        with get_db_session() as db:
            auth_service = AuthService(db)
            user, token = auth_service.login(email, password, ip_address, user_agent)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'role': user.role.value
            }
        }), 200
        
    except InvalidCredentialsError as e:
        return jsonify({'error': str(e)}), 401
    except AccountLockedError as e:
        return jsonify({'error': str(e)}), 423
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout(current_user, token):
    """
    Logout user and invalidate session.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Logout successful
        401: Unauthorized
    """
    try:
        with get_db_session() as db:
            auth_service = AuthService(db)
            auth_service.logout(token)
        
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/session/refresh', methods=['POST'])
@require_auth
def refresh_session(current_user, token):
    """
    Refresh session activity timestamp.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Session refreshed
        401: Unauthorized
    """
    try:
        with get_db_session() as db:
            auth_service = AuthService(db)
            success = auth_service.refresh_session(token)
        
        if success:
            return jsonify({'message': 'Session refreshed'}), 200
        else:
            return jsonify({'error': 'Session not found'}), 404
        
    except Exception as e:
        logger.error(f"Session refresh error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/session/validate', methods=['GET'])
@require_auth
def validate_session(current_user, token):
    """
    Validate current session.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Session valid with user info
        401: Unauthorized
    """
    return jsonify({
        'valid': True,
        'user': {
            'id': str(current_user.id),
            'email': current_user.email,
            'role': current_user.role.value
        }
    }), 200


@auth_bp.route('/account/lock/<user_id>', methods=['POST'])
@require_auth
@require_role(['admin'])
def lock_account(current_user, token, user_id):
    """
    Lock a user account (admin only).
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Account locked
        401: Unauthorized
        403: Forbidden
        404: User not found
    """
    try:
        with get_db_session() as db:
            auth_service = AuthService(db)
            success = auth_service.lock_account(user_id)
        
        if success:
            return jsonify({'message': 'Account locked successfully'}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
        
    except Exception as e:
        logger.error(f"Lock account error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/account/unlock/<user_id>', methods=['POST'])
@require_auth
@require_role(['admin'])
def unlock_account(current_user, token, user_id):
    """
    Unlock a user account (admin only).
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Account unlocked
        401: Unauthorized
        403: Forbidden
        404: User not found
    """
    try:
        with get_db_session() as db:
            auth_service = AuthService(db)
            success = auth_service.unlock_account(user_id)
        
        if success:
            return jsonify({'message': 'Account unlocked successfully'}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
        
    except Exception as e:
        logger.error(f"Unlock account error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
