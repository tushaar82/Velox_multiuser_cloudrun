"""
Notification WebSocket Events - Handles in-app notification push and read status updates.
"""
import logging
from typing import Dict, Any, List
from flask import request
from flask_socketio import emit
from datetime import datetime

from websocket_service.websocket_server import (
    socketio, authenticated_only, subscribe_to_room, 
    unsubscribe_from_room, broadcast_to_user, publish_broadcast
)
from websocket_service.room_manager import RoomManager
from shared.models.notification import NotificationData, NotificationType, NotificationSeverity

logger = logging.getLogger(__name__)


@socketio.on('subscribe_notifications')
@authenticated_only
def handle_subscribe_notifications():
    """
    Subscribe to user-specific notifications.
    Automatically subscribes to user's notification room.
    """
    try:
        user_id = request.user_id
        
        # Subscribe to user notification room
        room_name = RoomManager.get_user_room(user_id)
        subscribe_to_room(room_name)
        
        # Load and send recent unread notifications
        unread_notifications = _load_unread_notifications(user_id)
        unread_count = len(unread_notifications)
        
        emit('notifications_subscribed', {
            'user_id': user_id,
            'unread_notifications': unread_notifications,
            'unread_count': unread_count
        })
        
        logger.info(f"User {user_id} subscribed to notifications")
        
    except Exception as e:
        logger.error(f"Error in subscribe_notifications: {e}")
        emit('error', {'message': f'Failed to subscribe to notifications: {str(e)}'})


@socketio.on('unsubscribe_notifications')
@authenticated_only
def handle_unsubscribe_notifications():
    """
    Unsubscribe from user-specific notifications.
    """
    try:
        user_id = request.user_id
        
        # Unsubscribe from user notification room
        room_name = RoomManager.get_user_room(user_id)
        unsubscribe_from_room(room_name)
        
        emit('notifications_unsubscribed', {
            'user_id': user_id
        })
        
        logger.info(f"User {user_id} unsubscribed from notifications")
        
    except Exception as e:
        logger.error(f"Error in unsubscribe_notifications: {e}")
        emit('error', {'message': f'Failed to unsubscribe from notifications: {str(e)}'})


@socketio.on('mark_notification_read')
@authenticated_only
def handle_mark_notification_read(data: Dict[str, Any]):
    """
    Mark a notification as read.
    
    Expected data format:
    {
        'notification_id': 'uuid'
    }
    """
    try:
        user_id = request.user_id
        notification_id = data.get('notification_id')
        
        if not notification_id:
            emit('error', {'message': 'Missing required field: notification_id'})
            return
        
        # Mark notification as read in database
        success = _mark_notification_read(user_id, notification_id)
        
        if success:
            emit('notification_read', {
                'notification_id': notification_id,
                'read_at': datetime.utcnow().isoformat()
            })
            
            # Update unread count
            unread_count = _get_unread_count(user_id)
            emit('unread_count_update', {
                'unread_count': unread_count
            })
            
            logger.debug(f"User {user_id} marked notification {notification_id} as read")
        else:
            emit('error', {'message': 'Failed to mark notification as read'})
        
    except Exception as e:
        logger.error(f"Error in mark_notification_read: {e}")
        emit('error', {'message': f'Failed to mark notification as read: {str(e)}'})


@socketio.on('mark_all_notifications_read')
@authenticated_only
def handle_mark_all_notifications_read():
    """
    Mark all notifications as read for the current user.
    """
    try:
        user_id = request.user_id
        
        # Mark all notifications as read in database
        count = _mark_all_notifications_read(user_id)
        
        emit('all_notifications_read', {
            'count': count,
            'read_at': datetime.utcnow().isoformat()
        })
        
        # Update unread count to 0
        emit('unread_count_update', {
            'unread_count': 0
        })
        
        logger.info(f"User {user_id} marked all {count} notifications as read")
        
    except Exception as e:
        logger.error(f"Error in mark_all_notifications_read: {e}")
        emit('error', {'message': f'Failed to mark all notifications as read: {str(e)}'})


def push_notification(user_id: str, notification: NotificationData):
    """
    Push a notification to a specific user via WebSocket.
    Called by notification service when a new notification is created.
    
    Args:
        user_id: User ID to send notification to
        notification: Notification data
    """
    # Convert notification to dict
    notification_dict = {
        'id': notification.id,
        'type': notification.type.value,
        'title': notification.title,
        'message': notification.message,
        'severity': notification.severity.value,
        'created_at': notification.created_at.isoformat(),
        'read_at': notification.read_at.isoformat() if notification.read_at else None
    }
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='new_notification',
        payload={
            'notification': notification_dict,
            'timestamp': datetime.utcnow().isoformat()
        },
        user_id=user_id
    )
    
    logger.info(f"Pushed notification to user {user_id}: {notification.type.value}")


def push_notification_dict(user_id: str, notification_dict: Dict[str, Any]):
    """
    Push a notification dictionary to a specific user via WebSocket.
    Alternative method that accepts a dictionary instead of NotificationData.
    
    Args:
        user_id: User ID to send notification to
        notification_dict: Notification data as dictionary
    """
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='new_notification',
        payload={
            'notification': notification_dict,
            'timestamp': datetime.utcnow().isoformat()
        },
        user_id=user_id
    )
    
    logger.info(f"Pushed notification to user {user_id}")


def broadcast_unread_count_update(user_id: str, unread_count: int):
    """
    Broadcast unread notification count update to user.
    
    Args:
        user_id: User ID
        unread_count: Number of unread notifications
    """
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='unread_count_update',
        payload={
            'unread_count': unread_count,
            'timestamp': datetime.utcnow().isoformat()
        },
        user_id=user_id
    )
    
    logger.debug(f"Broadcasted unread count update to user {user_id}: {unread_count}")


def _load_unread_notifications(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Load unread notifications for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of notifications to load
        
    Returns:
        List of notification dictionaries
    """
    from sqlalchemy.orm import Session
    from shared.database.connection import get_db_session
    from shared.models import Notification
    
    try:
        with get_db_session() as db:
            notifications = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None)
            ).order_by(Notification.created_at.desc()).limit(limit).all()
            
            return [
                {
                    'id': str(n.id),
                    'type': n.type.value,
                    'title': n.title,
                    'message': n.message,
                    'severity': n.severity.value,
                    'created_at': n.created_at.isoformat(),
                    'read_at': None
                }
                for n in notifications
            ]
        
    except Exception as e:
        logger.error(f"Error loading unread notifications: {e}")
        return []


def _mark_notification_read(user_id: str, notification_id: str) -> bool:
    """
    Mark a notification as read.
    
    Args:
        user_id: User ID
        notification_id: Notification ID
        
    Returns:
        True if successful, False otherwise
    """
    from sqlalchemy.orm import Session
    from shared.database.connection import get_db_session
    from shared.models import Notification
    
    try:
        with get_db_session() as db:
            notification = db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.user_id == user_id
            ).first()
            
            if notification and not notification.read_at:
                notification.read_at = datetime.utcnow()
                db.commit()
                return True
            
            return False
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return False


def _mark_all_notifications_read(user_id: str) -> int:
    """
    Mark all notifications as read for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Number of notifications marked as read
    """
    from sqlalchemy.orm import Session
    from shared.database.connection import get_db_session
    from shared.models import Notification
    
    try:
        with get_db_session() as db:
            count = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.read_at.is_(None)
            ).update({
                'read_at': datetime.utcnow()
            })
            
            db.commit()
            return count
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return 0


def _get_unread_count(user_id: str) -> int:
    """
    Get count of unread notifications for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Number of unread notifications
    """
    from sqlalchemy.orm import Session
    from shared.database.connection import get_db_session
    from shared.models import Notification
    
    try:
        with get_db_session() as db:
            count = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.read_at.is_(None)
            ).count()
            
            return count
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return 0
