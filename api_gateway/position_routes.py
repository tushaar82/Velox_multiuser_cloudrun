"""API routes for position management."""

from flask import Blueprint, request, jsonify
from shared.database.connection import get_db_session
from shared.models.order import TradingMode
from api_gateway.middleware import require_auth, require_role
from api_gateway.position_service import PositionService
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)

position_bp = Blueprint('positions', __name__, url_prefix='/api/positions')


@position_bp.route('/account/<account_id>', methods=['GET'])
@require_auth
@require_role(['trader', 'investor'])
def get_account_positions(account_id: str):
    """
    Get all positions for an account.
    
    Args:
        account_id: Account ID
        
    Query parameters:
        trading_mode: Filter by trading mode (paper/live)
        include_closed: Include closed positions (default false)
        
    Returns:
        200: List of positions
        403: Forbidden
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        position_service = PositionService(db)
        
        # Verify access
        if not position_service.verify_account_access(user_id, account_id):
            return jsonify({'error': 'Access denied to account'}), 403
        
        # Get query parameters
        trading_mode_str = request.args.get('trading_mode')
        trading_mode = TradingMode(trading_mode_str) if trading_mode_str else None
        include_closed = request.args.get('include_closed', 'false').lower() == 'true'
        
        # Get positions
        if trading_mode:
            positions = position_service.get_positions(account_id, trading_mode, include_closed)
        else:
            # Get both paper and live positions
            paper_positions = position_service.get_positions(account_id, TradingMode.PAPER, include_closed)
            live_positions = position_service.get_positions(account_id, TradingMode.LIVE, include_closed)
            positions = paper_positions + live_positions
        
        return jsonify({
            'positions': [
                {
                    'id': pos.id,
                    'symbol': pos.symbol,
                    'side': pos.side.value,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'realized_pnl': pos.realized_pnl,
                    'trading_mode': pos.trading_mode.value,
                    'stop_loss': pos.stop_loss,
                    'take_profit': pos.take_profit,
                    'trailing_stop_loss': {
                        'enabled': pos.trailing_stop_loss.enabled,
                        'percentage': pos.trailing_stop_loss.percentage,
                        'current_stop_price': pos.trailing_stop_loss.current_stop_price
                    } if pos.trailing_stop_loss else None,
                    'opened_at': pos.opened_at.isoformat(),
                    'closed_at': pos.closed_at.isoformat() if pos.closed_at else None
                }
                for pos in positions
            ]
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': 'Failed to get positions'}), 500


@position_bp.route('/<position_id>', methods=['GET'])
@require_auth
@require_role(['trader', 'investor'])
def get_position(position_id: str):
    """
    Get single position details.
    
    Args:
        position_id: Position ID
        
    Returns:
        200: Position details
        403: Forbidden
        404: Position not found
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        position_service = PositionService(db)
        
        # Get position
        position = position_service.get_position(position_id)
        if not position:
            return jsonify({'error': 'Position not found'}), 404
        
        # Verify access
        if not position_service.verify_account_access(user_id, position.account_id):
            return jsonify({'error': 'Access denied to position'}), 403
        
        return jsonify({
            'id': position.id,
            'account_id': position.account_id,
            'strategy_id': position.strategy_id,
            'symbol': position.symbol,
            'side': position.side.value,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'current_price': position.current_price,
            'unrealized_pnl': position.unrealized_pnl,
            'realized_pnl': position.realized_pnl,
            'trading_mode': position.trading_mode.value,
            'stop_loss': position.stop_loss,
            'take_profit': position.take_profit,
            'trailing_stop_loss': {
                'enabled': position.trailing_stop_loss.enabled,
                'percentage': position.trailing_stop_loss.percentage,
                'current_stop_price': position.trailing_stop_loss.current_stop_price,
                'highest_price': position.trailing_stop_loss.highest_price,
                'lowest_price': position.trailing_stop_loss.lowest_price
            } if position.trailing_stop_loss else None,
            'opened_at': position.opened_at.isoformat(),
            'closed_at': position.closed_at.isoformat() if position.closed_at else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        return jsonify({'error': 'Failed to get position'}), 500


@position_bp.route('/<position_id>/close', methods=['POST'])
@require_auth
@require_role(['trader'])
def close_position(position_id: str):
    """
    Manually close a position.
    
    Args:
        position_id: Position ID
        
    Request body:
    {
        "closing_price": 2450.50,
        "commission": 10.50 (optional)
    }
    
    Returns:
        200: Position closed successfully
        400: Invalid request
        403: Forbidden
        404: Position not found
        500: Server error
    """
    try:
        user_id = request.user_id
        data = request.get_json()
        
        if 'closing_price' not in data:
            return jsonify({'error': 'Missing required field: closing_price'}), 400
        
        db = get_db_session()
        position_service = PositionService(db)
        
        # Get position and verify access
        position = position_service.get_position(position_id)
        if not position:
            return jsonify({'error': 'Position not found'}), 404
        
        if not position_service.verify_account_access(user_id, position.account_id):
            return jsonify({'error': 'Access denied to position'}), 403
        
        # Close position
        closed_position = position_service.close_position(
            position_id,
            data['closing_price'],
            data.get('commission', 0.0)
        )
        
        logger.info(f"Position closed by user {user_id}: {position_id}")
        
        return jsonify({
            'message': 'Position closed successfully',
            'position_id': closed_position.id,
            'realized_pnl': closed_position.realized_pnl
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return jsonify({'error': 'Failed to close position'}), 500


@position_bp.route('/<position_id>/trailing-stop', methods=['PUT'])
@require_auth
@require_role(['trader'])
def update_trailing_stop(position_id: str):
    """
    Update trailing stop-loss configuration for a position.
    
    Args:
        position_id: Position ID
        
    Request body:
    {
        "percentage": 0.02,  # 2%
        "current_price": 2450.50
    }
    
    Returns:
        200: Trailing stop updated successfully
        400: Invalid request
        403: Forbidden
        404: Position not found
        500: Server error
    """
    try:
        user_id = request.user_id
        data = request.get_json()
        
        required_fields = ['percentage', 'current_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        db = get_db_session()
        position_service = PositionService(db)
        
        # Get position and verify access
        position = position_service.get_position(position_id)
        if not position:
            return jsonify({'error': 'Position not found'}), 404
        
        if not position_service.verify_account_access(user_id, position.account_id):
            return jsonify({'error': 'Access denied to position'}), 403
        
        # Update trailing stop
        updated_position = position_service.configure_trailing_stop(
            position_id,
            data['percentage'],
            data['current_price']
        )
        
        logger.info(f"Trailing stop updated by user {user_id}: {position_id}")
        
        return jsonify({
            'message': 'Trailing stop updated successfully',
            'trailing_stop': {
                'enabled': updated_position.trailing_stop_loss.enabled,
                'percentage': updated_position.trailing_stop_loss.percentage,
                'current_stop_price': updated_position.trailing_stop_loss.current_stop_price
            } if updated_position.trailing_stop_loss else None
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating trailing stop: {e}")
        return jsonify({'error': 'Failed to update trailing stop'}), 500


@position_bp.route('/risk-metrics/<account_id>', methods=['GET'])
@require_auth
@require_role(['trader', 'investor'])
def get_risk_metrics(account_id: str):
    """
    Get real-time risk metrics for an account.
    
    Args:
        account_id: Account ID
        
    Query parameters:
        trading_mode: Filter by trading mode (paper/live)
        
    Returns:
        200: Risk metrics
        403: Forbidden
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        position_service = PositionService(db)
        
        # Verify access
        if not position_service.verify_account_access(user_id, account_id):
            return jsonify({'error': 'Access denied to account'}), 403
        
        # Get trading mode filter
        trading_mode_str = request.args.get('trading_mode')
        trading_mode = TradingMode(trading_mode_str) if trading_mode_str else None
        
        # Calculate risk metrics
        metrics = position_service.calculate_risk_metrics(account_id, trading_mode)
        
        return jsonify(metrics), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}")
        return jsonify({'error': 'Failed to calculate risk metrics'}), 500


@position_bp.route('/history/<account_id>', methods=['GET'])
@require_auth
@require_role(['trader', 'investor'])
def get_position_history(account_id: str):
    """
    Get position history for an account.
    
    Args:
        account_id: Account ID
        
    Query parameters:
        trading_mode: Filter by trading mode (paper/live)
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        symbol: Filter by symbol
        limit: Maximum number of positions (default 100)
        
    Returns:
        200: Position history
        403: Forbidden
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        position_service = PositionService(db)
        
        # Verify access
        if not position_service.verify_account_access(user_id, account_id):
            return jsonify({'error': 'Access denied to account'}), 403
        
        # Get filters
        filters = {
            'trading_mode': request.args.get('trading_mode'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'symbol': request.args.get('symbol'),
            'limit': int(request.args.get('limit', 100))
        }
        
        # Get position history
        positions = position_service.get_position_history(account_id, filters)
        
        return jsonify({
            'positions': [
                {
                    'id': pos.id,
                    'symbol': pos.symbol,
                    'side': pos.side.value,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'realized_pnl': pos.realized_pnl,
                    'trading_mode': pos.trading_mode.value,
                    'opened_at': pos.opened_at.isoformat(),
                    'closed_at': pos.closed_at.isoformat() if pos.closed_at else None
                }
                for pos in positions
            ],
            'count': len(positions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting position history: {e}")
        return jsonify({'error': 'Failed to get position history'}), 500
