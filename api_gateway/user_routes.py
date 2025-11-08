"""
User management API routes.
Provides endpoints for account creation, investor invitations, and access control.
"""
import logging
from flask import Blueprint, request, jsonify

from shared.database.connection import get_db_session
from shared.models import UserRole
from api_gateway.middleware import require_auth, require_role
from api_gateway.user_service import (
    UserService,
    AccountNotFoundError,
    UnauthorizedAccessError,
    InvitationError,
    UserManagementError
)

logger = logging.getLogger(__name__)

# Create blueprint
user_bp = Blueprint('user', __name__, url_prefix='/api/users')


@user_bp.route('/accounts', methods=['POST'])
@require_auth
@require_role(['trader'])
def create_account(current_user, token):
    """
    Create a new user account for a trader.
    
    Headers:
        Authorization: Bearer <token>
    
    Request body:
        {
            "name": "My Trading Account"
        }
    
    Returns:
        201: Account created successfully
        400: Invalid input
        401: Unauthorized
        403: Forbidden
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'Account name is required'}), 400
        
        with get_db_session() as db:
            user_service = UserService(db)
            account = user_service.create_user_account(
                trader_id=current_user.id,
                account_name=data['name']
            )
        
        return jsonify({
            'message': 'Account created successfully',
            'account': {
                'id': str(account.id),
                'name': account.name,
                'trader_id': str(account.trader_id),
                'is_active': account.is_active,
                'created_at': account.created_at.isoformat()
            }
        }), 201
        
    except UserManagementError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Create account error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/accounts/<account_id>/invite', methods=['POST'])
@require_auth
def invite_investor(current_user, token, account_id):
    """
    Invite an investor to view an account.
    
    Headers:
        Authorization: Bearer <token>
    
    Request body:
        {
            "email": "investor@example.com",
            "expiration_days": 7  # Optional, defaults to 7
        }
    
    Returns:
        201: Invitation created successfully
        400: Invalid input
        401: Unauthorized
        403: Forbidden
        404: Account not found
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({'error': 'Investor email is required'}), 400
        
        expiration_days = data.get('expiration_days', 7)
        
        with get_db_session() as db:
            user_service = UserService(db)
            invitation = user_service.invite_investor(
                account_id=account_id,
                inviter_id=current_user.id,
                invitee_email=data['email'],
                expiration_days=expiration_days
            )
        
        return jsonify({
            'message': 'Invitation sent successfully',
            'invitation': {
                'id': str(invitation.id),
                'account_id': str(invitation.account_id),
                'invitee_email': invitation.invitee_email,
                'status': invitation.status.value,
                'expires_at': invitation.expires_at.isoformat()
            }
        }), 201
        
    except AccountNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except UnauthorizedAccessError as e:
        return jsonify({'error': str(e)}), 403
    except InvitationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Invite investor error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/invitations/<invitation_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(current_user, token, invitation_id):
    """
    Accept an investor invitation.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Invitation accepted successfully
        400: Invalid invitation
        401: Unauthorized
    """
    try:
        with get_db_session() as db:
            user_service = UserService(db)
            access = user_service.accept_invitation(
                invitation_id=invitation_id,
                user_id=current_user.id
            )
        
        return jsonify({
            'message': 'Invitation accepted successfully',
            'access': {
                'account_id': str(access.account_id),
                'role': access.role,
                'granted_at': access.granted_at.isoformat()
            }
        }), 200
        
    except InvitationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Accept invitation error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/accounts/<account_id>/revoke/<investor_id>', methods=['DELETE'])
@require_auth
def revoke_investor_access(current_user, token, account_id, investor_id):
    """
    Revoke an investor's access to an account.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: Access revoked successfully
        401: Unauthorized
        403: Forbidden
        404: Access not found
    """
    try:
        with get_db_session() as db:
            user_service = UserService(db)
            success = user_service.revoke_investor_access(
                account_id=account_id,
                investor_id=investor_id,
                revoker_id=current_user.id
            )
        
        if success:
            return jsonify({'message': 'Access revoked successfully'}), 200
        else:
            return jsonify({'error': 'Access not found'}), 404
        
    except UnauthorizedAccessError as e:
        return jsonify({'error': str(e)}), 403
    except UserManagementError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Revoke access error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/accounts/<account_id>/users', methods=['GET'])
@require_auth
def get_account_users(current_user, token, account_id):
    """
    Get all users with access to an account.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: List of users
        401: Unauthorized
    """
    try:
        with get_db_session() as db:
            user_service = UserService(db)
            users = user_service.get_account_users(account_id)
        
        return jsonify({
            'account_id': account_id,
            'users': users
        }), 200
        
    except Exception as e:
        logger.error(f"Get account users error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/investor/accounts', methods=['GET'])
@require_auth
@require_role(['investor'])
def get_investor_accounts(current_user, token):
    """
    Get all accounts an investor has access to.
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: List of accounts
        401: Unauthorized
        403: Forbidden
    """
    try:
        with get_db_session() as db:
            user_service = UserService(db)
            accounts = user_service.get_investor_accounts(current_user.id)
        
        return jsonify({
            'accounts': [
                {
                    'id': str(account.id),
                    'name': account.name,
                    'trader_id': str(account.trader_id),
                    'is_active': account.is_active,
                    'created_at': account.created_at.isoformat()
                }
                for account in accounts
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Get investor accounts error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/<user_id>/role', methods=['PUT'])
@require_auth
@require_role(['admin'])
def update_user_role(current_user, token, user_id):
    """
    Update a user's role (admin only).
    
    Headers:
        Authorization: Bearer <token>
    
    Request body:
        {
            "role": "trader"  # admin, trader, or investor
        }
    
    Returns:
        200: Role updated successfully
        400: Invalid input
        401: Unauthorized
        403: Forbidden
        404: User not found
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('role'):
            return jsonify({'error': 'Role is required'}), 400
        
        # Parse role
        try:
            new_role = UserRole[data['role'].upper()]
        except KeyError:
            return jsonify({'error': f'Invalid role: {data["role"]}'}), 400
        
        with get_db_session() as db:
            user_service = UserService(db)
            user = user_service.update_user_role(
                user_id=user_id,
                new_role=new_role,
                admin_id=current_user.id
            )
        
        return jsonify({
            'message': 'Role updated successfully',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'role': user.role.value
            }
        }), 200
        
    except UnauthorizedAccessError as e:
        return jsonify({'error': str(e)}), 403
    except UserManagementError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Update role error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/<user_id>/disable', methods=['POST'])
@require_auth
@require_role(['admin'])
def disable_user(current_user, token, user_id):
    """
    Disable a user account (admin only).
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: User disabled successfully
        401: Unauthorized
        403: Forbidden
        404: User not found
    """
    try:
        with get_db_session() as db:
            user_service = UserService(db)
            success = user_service.disable_user(
                user_id=user_id,
                admin_id=current_user.id
            )
        
        if success:
            return jsonify({'message': 'User disabled successfully'}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
        
    except UnauthorizedAccessError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Disable user error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/<user_id>/enable', methods=['POST'])
@require_auth
@require_role(['admin'])
def enable_user(current_user, token, user_id):
    """
    Enable a user account (admin only).
    
    Headers:
        Authorization: Bearer <token>
    
    Returns:
        200: User enabled successfully
        401: Unauthorized
        403: Forbidden
        404: User not found
    """
    try:
        with get_db_session() as db:
            user_service = UserService(db)
            success = user_service.enable_user(
                user_id=user_id,
                admin_id=current_user.id
            )
        
        if success:
            return jsonify({'message': 'User enabled successfully'}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
        
    except UnauthorizedAccessError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Enable user error: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
