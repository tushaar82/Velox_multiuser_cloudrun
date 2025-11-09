"""
Trading Activity WebSocket Events - Handles position, order, P&L, and strategy updates.
"""
import logging
from typing import Dict, Any, List
from flask import request
from flask_socketio import emit
from datetime import datetime

from websocket_service.websocket_server import (
    socketio, authenticated_only, subscribe_to_room, 
    unsubscribe_from_room, publish_broadcast
)
from websocket_service.room_manager import RoomManager
from shared.models.position import PositionData
from shared.models.order import OrderData
from shared.models.order import TradingMode

logger = logging.getLogger(__name__)


@socketio.on('subscribe_account')
@authenticated_only
def handle_subscribe_account(data: Dict[str, Any]):
    """
    Subscribe to account-specific trading updates.
    
    Expected data format:
    {
        'account_id': 'uuid',
        'trading_mode': 'paper' or 'live'
    }
    """
    try:
        account_id = data.get('account_id')
        trading_mode = data.get('trading_mode', 'paper')
        
        if not account_id:
            emit('error', {'message': 'Missing required field: account_id'})
            return
        
        # Verify user has access to this account
        if not _verify_account_access(request.user_id, account_id):
            emit('error', {'message': 'Access denied to this account'})
            return
        
        # Subscribe to account room
        room_name = RoomManager.get_account_room(account_id, trading_mode)
        subscribe_to_room(room_name)
        
        # Subscribe to position and order rooms
        position_room = RoomManager.get_position_room(account_id, trading_mode)
        order_room = RoomManager.get_order_room(account_id, trading_mode)
        subscribe_to_room(position_room)
        subscribe_to_room(order_room)
        
        # Load and send current state
        positions = _load_positions(account_id, trading_mode)
        orders = _load_orders(account_id, trading_mode)
        pnl_summary = _calculate_pnl_summary(positions)
        
        emit('account_subscribed', {
            'account_id': account_id,
            'trading_mode': trading_mode,
            'positions': positions,
            'orders': orders,
            'pnl_summary': pnl_summary
        })
        
        logger.info(f"User {request.user_id} subscribed to account {account_id}:{trading_mode}")
        
    except Exception as e:
        logger.error(f"Error in subscribe_account: {e}")
        emit('error', {'message': f'Failed to subscribe to account: {str(e)}'})


@socketio.on('unsubscribe_account')
@authenticated_only
def handle_unsubscribe_account(data: Dict[str, Any]):
    """
    Unsubscribe from account-specific trading updates.
    
    Expected data format:
    {
        'account_id': 'uuid',
        'trading_mode': 'paper' or 'live'
    }
    """
    try:
        account_id = data.get('account_id')
        trading_mode = data.get('trading_mode', 'paper')
        
        if not account_id:
            emit('error', {'message': 'Missing required field: account_id'})
            return
        
        # Unsubscribe from all account-related rooms
        room_name = RoomManager.get_account_room(account_id, trading_mode)
        position_room = RoomManager.get_position_room(account_id, trading_mode)
        order_room = RoomManager.get_order_room(account_id, trading_mode)
        
        unsubscribe_from_room(room_name)
        unsubscribe_from_room(position_room)
        unsubscribe_from_room(order_room)
        
        emit('account_unsubscribed', {
            'account_id': account_id,
            'trading_mode': trading_mode
        })
        
        logger.info(f"User {request.user_id} unsubscribed from account {account_id}:{trading_mode}")
        
    except Exception as e:
        logger.error(f"Error in unsubscribe_account: {e}")
        emit('error', {'message': f'Failed to unsubscribe from account: {str(e)}'})


def broadcast_position_update(position: PositionData):
    """
    Broadcast position update to all subscribed clients.
    Called when position is opened, updated, or closed.
    
    Args:
        position: Position data
    """
    room_name = RoomManager.get_position_room(
        position.account_id, 
        position.trading_mode.value
    )
    
    # Convert position to dict
    position_dict = {
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
        'opened_at': position.opened_at.isoformat(),
        'closed_at': position.closed_at.isoformat() if position.closed_at else None
    }
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='position_update',
        payload={
            'position': position_dict,
            'timestamp': datetime.utcnow().isoformat()
        },
        room=room_name
    )
    
    logger.debug(f"Broadcasted position update for {position.symbol} in account {position.account_id}")


def broadcast_order_update(order: OrderData):
    """
    Broadcast order status update to all subscribed clients.
    Called when order status changes.
    
    Args:
        order: Order data
    """
    room_name = RoomManager.get_order_room(
        order.account_id,
        order.trading_mode.value
    )
    
    # Convert order to dict
    order_dict = {
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
    }
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='order_update',
        payload={
            'order': order_dict,
            'timestamp': datetime.utcnow().isoformat()
        },
        room=room_name
    )
    
    logger.debug(f"Broadcasted order update for {order.symbol} in account {order.account_id}")


def broadcast_pnl_update(account_id: str, trading_mode: str, pnl_data: Dict[str, Any]):
    """
    Broadcast P&L update to all subscribed clients.
    Called periodically (every 1 second) with updated P&L calculations.
    
    Args:
        account_id: Account ID
        trading_mode: Trading mode ('paper' or 'live')
        pnl_data: P&L summary data
    """
    room_name = RoomManager.get_account_room(account_id, trading_mode)
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='pnl_update',
        payload={
            'account_id': account_id,
            'trading_mode': trading_mode,
            'pnl': pnl_data,
            'timestamp': datetime.utcnow().isoformat()
        },
        room=room_name
    )
    
    logger.debug(f"Broadcasted P&L update for account {account_id}:{trading_mode}")


def broadcast_strategy_status(strategy_id: str, status: str, message: str = None):
    """
    Broadcast strategy status update to all subscribed clients.
    Called when strategy starts, stops, pauses, or encounters an error.
    
    Args:
        strategy_id: Strategy ID
        status: Strategy status ('running', 'paused', 'stopped', 'error')
        message: Optional status message
    """
    room_name = RoomManager.get_strategy_room(strategy_id)
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='strategy_status',
        payload={
            'strategy_id': strategy_id,
            'status': status,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        },
        room=room_name
    )
    
    logger.info(f"Broadcasted strategy status update: {strategy_id} -> {status}")


def _verify_account_access(user_id: str, account_id: str) -> bool:
    """
    Verify that user has access to the specified account.
    
    Args:
        user_id: User ID
        account_id: Account ID
        
    Returns:
        True if user has access, False otherwise
    """
    # TODO: Implement actual access verification
    # This should check the AccountAccess table
    from sqlalchemy.orm import Session
    from shared.database.connection import get_db
    from shared.models import AccountAccess, User, UserRole
    
    try:
        db: Session = next(get_db())
        
        # Check if user is admin (has access to all accounts)
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.role == UserRole.ADMIN:
            return True
        
        # Check if user has explicit access to this account
        access = db.query(AccountAccess).filter(
            AccountAccess.user_id == user_id,
            AccountAccess.account_id == account_id
        ).first()
        
        return access is not None
        
    except Exception as e:
        logger.error(f"Error verifying account access: {e}")
        return False


def _load_positions(account_id: str, trading_mode: str) -> List[Dict[str, Any]]:
    """
    Load current positions for an account.
    
    Args:
        account_id: Account ID
        trading_mode: Trading mode
        
    Returns:
        List of position dictionaries
    """
    # TODO: Integrate with position manager
    from sqlalchemy.orm import Session
    from shared.database.connection import get_db
    from shared.models import Position
    from shared.models.position import PositionData
    
    try:
        db: Session = next(get_db())
        
        positions = db.query(Position).filter(
            Position.account_id == account_id,
            Position.trading_mode == trading_mode,
            Position.closed_at.is_(None)
        ).all()
        
        return [
            {
                'id': str(p.id),
                'symbol': p.symbol,
                'side': p.side.value,
                'quantity': p.quantity,
                'entry_price': float(p.entry_price),
                'current_price': float(p.current_price),
                'unrealized_pnl': float(p.unrealized_pnl),
                'realized_pnl': float(p.realized_pnl),
                'opened_at': p.opened_at.isoformat()
            }
            for p in positions
        ]
        
    except Exception as e:
        logger.error(f"Error loading positions: {e}")
        return []


def _load_orders(account_id: str, trading_mode: str) -> List[Dict[str, Any]]:
    """
    Load recent orders for an account.
    
    Args:
        account_id: Account ID
        trading_mode: Trading mode
        
    Returns:
        List of order dictionaries
    """
    # TODO: Integrate with order manager
    from sqlalchemy.orm import Session
    from shared.database.connection import get_db
    from shared.models import Order
    
    try:
        db: Session = next(get_db())
        
        orders = db.query(Order).filter(
            Order.account_id == account_id,
            Order.trading_mode == trading_mode
        ).order_by(Order.created_at.desc()).limit(50).all()
        
        return [
            {
                'id': str(o.id),
                'symbol': o.symbol,
                'side': o.side.value,
                'quantity': o.quantity,
                'order_type': o.order_type,
                'status': o.status.value,
                'filled_quantity': o.filled_quantity,
                'average_price': float(o.average_price) if o.average_price else None,
                'created_at': o.created_at.isoformat()
            }
            for o in orders
        ]
        
    except Exception as e:
        logger.error(f"Error loading orders: {e}")
        return []


def _calculate_pnl_summary(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate P&L summary from positions.
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        P&L summary dictionary
    """
    total_unrealized = sum(p.get('unrealized_pnl', 0) for p in positions)
    total_realized = sum(p.get('realized_pnl', 0) for p in positions)
    
    return {
        'total_unrealized_pnl': total_unrealized,
        'total_realized_pnl': total_realized,
        'total_pnl': total_unrealized + total_realized,
        'open_positions_count': len(positions)
    }
