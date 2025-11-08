"""API routes for order management."""

from flask import Blueprint, request, jsonify
from shared.database.connection import get_db_session
from shared.models.order import OrderSide, TradingMode
from api_gateway.middleware import require_auth, require_role
from api_gateway.order_service import OrderService
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)

order_bp = Blueprint('orders', __name__, url_prefix='/api/orders')


@order_bp.route('/submit', methods=['POST'])
@require_auth
@require_role(['trader'])
def submit_order():
    """
    Submit a new order.
    
    Request body:
    {
        "account_id": "uuid",
        "symbol": "RELIANCE",
        "side": "buy",
        "quantity": 10,
        "order_type": "market",
        "trading_mode": "paper",
        "strategy_id": "uuid" (optional),
        "price": 2450.50 (optional, for limit orders),
        "stop_price": 2400.00 (optional, for stop orders),
        "current_market_price": 2450.00 (required for paper trading)
    }
    
    Returns:
        201: Order created successfully
        400: Invalid request
        403: Forbidden
        500: Server error
    """
    try:
        data = request.get_json()
        user_id = request.user_id
        
        # Validate required fields
        required_fields = ['account_id', 'symbol', 'side', 'quantity', 'order_type', 'trading_mode']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate trading mode
        try:
            trading_mode = TradingMode(data['trading_mode'])
        except ValueError:
            return jsonify({'error': 'Invalid trading_mode. Must be "paper" or "live"'}), 400
        
        # Validate side
        try:
            side = OrderSide(data['side'])
        except ValueError:
            return jsonify({'error': 'Invalid side. Must be "buy" or "sell"'}), 400
        
        # Paper trading requires current market price
        if trading_mode == TradingMode.PAPER and 'current_market_price' not in data:
            return jsonify({'error': 'current_market_price required for paper trading'}), 400
        
        db = get_db_session()
        order_service = OrderService(db)
        
        # Verify user has access to account
        if not order_service.verify_account_access(user_id, data['account_id']):
            return jsonify({'error': 'Access denied to account'}), 403
        
        # Submit order
        order = order_service.submit_order(
            account_id=data['account_id'],
            symbol=data['symbol'],
            side=side,
            quantity=data['quantity'],
            order_type=data['order_type'],
            trading_mode=trading_mode,
            strategy_id=data.get('strategy_id'),
            price=data.get('price'),
            stop_price=data.get('stop_price'),
            current_market_price=data.get('current_market_price')
        )
        
        logger.info(f"Order submitted by user {user_id}: {order.id}")
        
        return jsonify({
            'order_id': order.id,
            'status': order.status.value,
            'message': 'Order submitted successfully'
        }), 201
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error submitting order: {e}")
        return jsonify({'error': 'Failed to submit order'}), 500


@order_bp.route('/<order_id>/cancel', methods=['POST'])
@require_auth
@require_role(['trader'])
def cancel_order(order_id: str):
    """
    Cancel a pending order.
    
    Args:
        order_id: Order ID to cancel
        
    Returns:
        200: Order cancelled successfully
        403: Forbidden
        404: Order not found
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        order_service = OrderService(db)
        
        # Get order and verify access
        order = order_service.get_order(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        if not order_service.verify_account_access(user_id, order.account_id):
            return jsonify({'error': 'Access denied to order'}), 403
        
        # Cancel order
        success = order_service.cancel_order(order_id)
        
        if success:
            logger.info(f"Order cancelled by user {user_id}: {order_id}")
            return jsonify({'message': 'Order cancelled successfully'}), 200
        else:
            return jsonify({'error': 'Failed to cancel order'}), 400
        
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return jsonify({'error': 'Failed to cancel order'}), 500


@order_bp.route('/<order_id>', methods=['GET'])
@require_auth
@require_role(['trader', 'investor'])
def get_order_status(order_id: str):
    """
    Get order status and details.
    
    Args:
        order_id: Order ID
        
    Returns:
        200: Order details
        403: Forbidden
        404: Order not found
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        order_service = OrderService(db)
        
        # Get order and verify access
        order = order_service.get_order(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        if not order_service.verify_account_access(user_id, order.account_id):
            return jsonify({'error': 'Access denied to order'}), 403
        
        return jsonify({
            'id': order.id,
            'account_id': order.account_id,
            'strategy_id': order.strategy_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': order.quantity,
            'order_type': order.order_type,
            'price': order.price,
            'stop_price': order.stop_price,
            'trading_mode': order.trading_mode.value,
            'status': order.status.value,
            'filled_quantity': order.filled_quantity,
            'average_price': order.average_price,
            'broker_order_id': order.broker_order_id,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting order: {e}")
        return jsonify({'error': 'Failed to get order'}), 500


@order_bp.route('/account/<account_id>', methods=['GET'])
@require_auth
@require_role(['trader', 'investor'])
def get_account_orders(account_id: str):
    """
    Get all orders for an account.
    
    Args:
        account_id: Account ID
        
    Query parameters:
        trading_mode: Filter by trading mode (paper/live)
        limit: Maximum number of orders to return (default 100)
        
    Returns:
        200: List of orders
        403: Forbidden
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        order_service = OrderService(db)
        
        # Verify access
        if not order_service.verify_account_access(user_id, account_id):
            return jsonify({'error': 'Access denied to account'}), 403
        
        # Get query parameters
        trading_mode_str = request.args.get('trading_mode')
        trading_mode = TradingMode(trading_mode_str) if trading_mode_str else None
        limit = int(request.args.get('limit', 100))
        
        # Get orders
        orders = order_service.get_orders(account_id, trading_mode, limit)
        
        return jsonify({
            'orders': [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'quantity': order.quantity,
                    'order_type': order.order_type,
                    'price': order.price,
                    'trading_mode': order.trading_mode.value,
                    'status': order.status.value,
                    'filled_quantity': order.filled_quantity,
                    'average_price': order.average_price,
                    'created_at': order.created_at.isoformat()
                }
                for order in orders
            ]
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': 'Failed to get orders'}), 500


@order_bp.route('/history/<account_id>', methods=['GET'])
@require_auth
@require_role(['trader', 'investor'])
def get_order_history(account_id: str):
    """
    Get order history for an account with filtering.
    
    Args:
        account_id: Account ID
        
    Query parameters:
        trading_mode: Filter by trading mode (paper/live)
        status: Filter by status
        symbol: Filter by symbol
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        limit: Maximum number of orders (default 100)
        
    Returns:
        200: Order history
        403: Forbidden
        500: Server error
    """
    try:
        user_id = request.user_id
        
        db = get_db_session()
        order_service = OrderService(db)
        
        # Verify access
        if not order_service.verify_account_access(user_id, account_id):
            return jsonify({'error': 'Access denied to account'}), 403
        
        # Get filters from query parameters
        filters = {
            'trading_mode': request.args.get('trading_mode'),
            'status': request.args.get('status'),
            'symbol': request.args.get('symbol'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'limit': int(request.args.get('limit', 100))
        }
        
        # Get order history
        orders = order_service.get_order_history(account_id, filters)
        
        return jsonify({
            'orders': [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'quantity': order.quantity,
                    'order_type': order.order_type,
                    'price': order.price,
                    'trading_mode': order.trading_mode.value,
                    'status': order.status.value,
                    'filled_quantity': order.filled_quantity,
                    'average_price': order.average_price,
                    'created_at': order.created_at.isoformat(),
                    'updated_at': order.updated_at.isoformat()
                }
                for order in orders
            ],
            'count': len(orders)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting order history: {e}")
        return jsonify({'error': 'Failed to get order history'}), 500
