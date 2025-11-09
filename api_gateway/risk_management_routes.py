"""
Risk Management API Routes

Endpoints for managing risk limits and loss tracking.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from flask import Blueprint, request, jsonify
from pydantic import BaseModel, Field

from shared.database.connection import get_db_session
from api_gateway.risk_management_service import RiskManagementService
from api_gateway.middleware import require_auth
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)

risk_management_bp = Blueprint('risk_management', __name__, url_prefix='/api/risk-management')


# Request/Response Models
class SetMaxLossLimitRequest(BaseModel):
    """Request model for setting max loss limit."""
    account_id: str
    trading_mode: str = Field(..., pattern='^(paper|live)$')
    max_loss_limit: float = Field(..., gt=0)


class AcknowledgeLimitBreachRequest(BaseModel):
    """Request model for acknowledging limit breach."""
    account_id: str
    trading_mode: str = Field(..., pattern='^(paper|live)$')
    new_limit: Optional[float] = Field(None, gt=0)


@risk_management_bp.route('/loss-limit', methods=['POST'])
@require_auth
def set_max_loss_limit():
    """
    Set or update maximum loss limit for an account.
    
    Request Body:
        {
            "account_id": "uuid",
            "trading_mode": "paper" or "live",
            "max_loss_limit": 50000.00
        }
    
    Returns:
        200: Risk limits data
        400: Invalid request
        500: Server error
    """
    try:
        # Parse and validate request
        data = SetMaxLossLimitRequest(**request.json)
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Set loss limit
        risk_limits = service.set_max_loss_limit(
            account_id=UUID(data.account_id),
            trading_mode=data.trading_mode,
            max_loss_limit=Decimal(str(data.max_loss_limit))
        )
        
        return jsonify({
            'success': True,
            'data': risk_limits.to_dict()
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in set_max_loss_limit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in set_max_loss_limit: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@risk_management_bp.route('/loss-limit/<account_id>/<trading_mode>', methods=['GET'])
@require_auth
def get_risk_limits(account_id: str, trading_mode: str):
    """
    Get risk limits for an account and trading mode.
    
    Path Parameters:
        account_id: Account UUID
        trading_mode: 'paper' or 'live'
    
    Returns:
        200: Risk limits data
        404: Risk limits not found
        500: Server error
    """
    try:
        # Validate trading mode
        if trading_mode not in ['paper', 'live']:
            return jsonify({
                'success': False,
                'error': 'Invalid trading_mode. Must be "paper" or "live"'
            }), 400
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Get risk limits
        risk_limits = service.get_risk_limits(
            account_id=UUID(account_id),
            trading_mode=trading_mode
        )
        
        if not risk_limits:
            return jsonify({
                'success': False,
                'error': 'Risk limits not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': risk_limits.to_dict()
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in get_risk_limits: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in get_risk_limits: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@risk_management_bp.route('/current-loss/<account_id>/<trading_mode>', methods=['GET'])
@require_auth
def get_current_loss(account_id: str, trading_mode: str):
    """
    Calculate and return current loss for an account.
    
    Path Parameters:
        account_id: Account UUID
        trading_mode: 'paper' or 'live'
    
    Returns:
        200: Loss calculation data
        400: Invalid request
        500: Server error
    """
    try:
        # Validate trading mode
        if trading_mode not in ['paper', 'live']:
            return jsonify({
                'success': False,
                'error': 'Invalid trading_mode. Must be "paper" or "live"'
            }), 400
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Calculate current loss
        loss_calc = service.calculate_current_loss(
            account_id=UUID(account_id),
            trading_mode=trading_mode
        )
        
        return jsonify({
            'success': True,
            'data': loss_calc.to_dict()
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in get_current_loss: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in get_current_loss: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@risk_management_bp.route('/check-limit/<account_id>/<trading_mode>', methods=['POST'])
@require_auth
def check_loss_limit(account_id: str, trading_mode: str):
    """
    Check if loss limit has been breached.
    
    Path Parameters:
        account_id: Account UUID
        trading_mode: 'paper' or 'live'
    
    Returns:
        200: Breach status
        400: Invalid request
        500: Server error
    """
    try:
        # Validate trading mode
        if trading_mode not in ['paper', 'live']:
            return jsonify({
                'success': False,
                'error': 'Invalid trading_mode. Must be "paper" or "live"'
            }), 400
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Check loss limit
        is_breached = service.check_loss_limit(
            account_id=UUID(account_id),
            trading_mode=trading_mode
        )
        
        return jsonify({
            'success': True,
            'data': {
                'is_breached': is_breached
            }
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in check_loss_limit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in check_loss_limit: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@risk_management_bp.route('/acknowledge-breach', methods=['POST'])
@require_auth
def acknowledge_limit_breach():
    """
    Acknowledge a loss limit breach and optionally update the limit.
    
    Request Body:
        {
            "account_id": "uuid",
            "trading_mode": "paper" or "live",
            "new_limit": 75000.00  // Optional
        }
    
    Returns:
        200: Updated risk limits data
        400: Invalid request
        500: Server error
    """
    try:
        # Parse and validate request
        data = AcknowledgeLimitBreachRequest(**request.json)
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Acknowledge breach
        risk_limits = service.acknowledge_limit_breach(
            account_id=UUID(data.account_id),
            trading_mode=data.trading_mode,
            new_limit=Decimal(str(data.new_limit)) if data.new_limit else None
        )
        
        return jsonify({
            'success': True,
            'data': risk_limits.to_dict()
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in acknowledge_limit_breach: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in acknowledge_limit_breach: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500



# Strategy Limit Management Routes

class SetStrategyLimitRequest(BaseModel):
    """Request model for setting strategy limit."""
    trading_mode: str = Field(..., pattern='^(paper|live)$')
    max_concurrent_strategies: int = Field(..., gt=0)


@risk_management_bp.route('/strategy-limit', methods=['POST'])
@require_auth
def set_strategy_limit():
    """
    Set global concurrent strategy limit (admin only).
    
    Request Body:
        {
            "trading_mode": "paper" or "live",
            "max_concurrent_strategies": 10
        }
    
    Returns:
        200: Updated strategy limits
        400: Invalid request
        403: Forbidden (not admin)
        500: Server error
    """
    try:
        # TODO: Check if user is admin when auth middleware is fully implemented
        # For now, we'll allow any authenticated user
        
        # Parse and validate request
        data = SetStrategyLimitRequest(**request.json)
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # TODO: Get actual user ID from auth middleware
        # For now, use a placeholder UUID
        from uuid import uuid4
        admin_user_id = uuid4()
        
        # Set strategy limit
        strategy_limits = service.set_global_strategy_limit(
            trading_mode=data.trading_mode,
            max_concurrent_strategies=data.max_concurrent_strategies,
            updated_by=admin_user_id
        )
        
        return jsonify({
            'success': True,
            'data': strategy_limits
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in set_strategy_limit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in set_strategy_limit: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@risk_management_bp.route('/strategy-limit/<trading_mode>', methods=['GET'])
@require_auth
def get_strategy_limit(trading_mode: str):
    """
    Get global strategy limit for a trading mode.
    
    Path Parameters:
        trading_mode: 'paper' or 'live'
    
    Returns:
        200: Strategy limits data
        404: Strategy limits not found
        500: Server error
    """
    try:
        # Validate trading mode
        if trading_mode not in ['paper', 'live']:
            return jsonify({
                'success': False,
                'error': 'Invalid trading_mode. Must be "paper" or "live"'
            }), 400
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Get strategy limit
        strategy_limits = service.get_strategy_limit(trading_mode)
        
        if not strategy_limits:
            return jsonify({
                'success': False,
                'error': 'Strategy limits not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': strategy_limits
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_strategy_limit: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@risk_management_bp.route('/active-strategy-count/<account_id>/<trading_mode>', methods=['GET'])
@require_auth
def get_active_strategy_count(account_id: str, trading_mode: str):
    """
    Get count of active strategies for an account.
    
    Path Parameters:
        account_id: Account UUID
        trading_mode: 'paper' or 'live'
    
    Returns:
        200: Active strategy count
        400: Invalid request
        500: Server error
    """
    try:
        # Validate trading mode
        if trading_mode not in ['paper', 'live']:
            return jsonify({
                'success': False,
                'error': 'Invalid trading_mode. Must be "paper" or "live"'
            }), 400
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Get active count
        active_count = service.get_active_strategy_count(
            account_id=UUID(account_id),
            trading_mode=trading_mode
        )
        
        # Get limit
        strategy_limits = service.get_strategy_limit(trading_mode)
        max_limit = strategy_limits['max_concurrent_strategies'] if strategy_limits else None
        
        return jsonify({
            'success': True,
            'data': {
                'active_count': active_count,
                'max_limit': max_limit,
                'can_activate_more': active_count < max_limit if max_limit else True
            }
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in get_active_strategy_count: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in get_active_strategy_count: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@risk_management_bp.route('/can-activate-strategy/<account_id>/<trading_mode>', methods=['GET'])
@require_auth
def can_activate_strategy(account_id: str, trading_mode: str):
    """
    Check if a strategy can be activated based on concurrent strategy limits.
    
    Path Parameters:
        account_id: Account UUID
        trading_mode: 'paper' or 'live'
    
    Returns:
        200: Activation status
        400: Invalid request
        500: Server error
    """
    try:
        # Validate trading mode
        if trading_mode not in ['paper', 'live']:
            return jsonify({
                'success': False,
                'error': 'Invalid trading_mode. Must be "paper" or "live"'
            }), 400
        
        # Get database session
        db = next(get_db())
        service = RiskManagementService(db)
        
        # Check if can activate
        can_activate, error_msg = service.can_activate_strategy(
            account_id=UUID(account_id),
            trading_mode=trading_mode
        )
        
        return jsonify({
            'success': True,
            'data': {
                'can_activate': can_activate,
                'error_message': error_msg
            }
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error in can_activate_strategy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in can_activate_strategy: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
