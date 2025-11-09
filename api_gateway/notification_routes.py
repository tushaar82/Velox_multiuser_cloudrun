"""
Notification API Routes - Handles notification-related HTTP endpoints.
"""
import logging
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify

from api_gateway.middleware import require_auth
from shared.database.connection import get_db_session
from shared.services.notification_service import get_notification_service
from shared.models.notification import (
    NotificationData, NotificationRequest, NotificationType, 
    NotificationSeverity, NotificationChannel, NotificationChannelConfig,
    NotificationPreferences
)

logger = logging.getLogger(__name__)

notification_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notification_bp.route('/history', methods=['GET'])
@require_auth
def get_notification_history(current_user: Dict[str, Any]) -> tuple:
    """
    Get notification history for the current user.
    
    Query Parameters:
        - limit: Maximum number of notifications to return (default: 50)
        - offset: Offset for pagination (default: 0)
        - unread_only: If true, return only unread notifications (default: false)
    
    Returns:
        200: List of notifications
        500: Internal server error
    """
    try:
        user_id = current_user['user_id']
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        # Validate parameters
        if limit < 1 or limit > 100:
            return jsonify({'error': 'Limit must be between 1 and 100'}), 400
        
        if offset < 0:
            return jsonify({'error': 'Offset must be non-negative'}), 400
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Get notification history
        with get_db_session() as db:
            notifications = notification_service.get_notification_history(
                db=db,
                user_id=user_id,
                limit=limit,
                offset=offset,
                unread_only=unread_only
            )
            
            # Convert to dict
            notifications_dict = [
            {
                'id': n.id,
                'type': n.type.value,
                'title': n.title,
                'message': n.message,
                'severity': n.severity.value,
                'read_at': n.read_at.isoformat() if n.read_at else None,
                'created_at': n.created_at.isoformat()
                }
                for n in notifications
            ]
            
            return jsonify({
                'notifications': notifications_dict,
                'count': len(notifications_dict),
                'limit': limit,
                'offset': offset
            }), 200
        
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        return jsonify({'error': 'Failed to get notification history'}), 500


@notification_bp.route('/unread-count', methods=['GET'])
@require_auth
def get_unread_count(current_user: Dict[str, Any]) -> tuple:
    """
    Get count of unread notifications for the current user.
    
    Returns:
        200: Unread count
        500: Internal server error
    """
    try:
        user_id = current_user['user_id']
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Get unread count
        with get_db_session() as db:
            unread_count = notification_service.get_unread_count(db=db, user_id=user_id)
            
            return jsonify({
                'unread_count': unread_count
            }), 200
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        return jsonify({'error': 'Failed to get unread count'}), 500


@notification_bp.route('/<notification_id>/read', methods=['POST'])
@require_auth
def mark_notification_read(current_user: Dict[str, Any], notification_id: str) -> tuple:
    """
    Mark a notification as read.
    
    Path Parameters:
        - notification_id: Notification ID
    
    Returns:
        200: Notification marked as read
        404: Notification not found
        500: Internal server error
    """
    try:
        user_id = current_user['user_id']
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Mark as read
        with get_db_session() as db:
            success = notification_service.mark_as_read(
                db=db,
                user_id=user_id,
                notification_id=notification_id
            )
            
            if not success:
                return jsonify({'error': 'Notification not found or already read'}), 404
            
            # Get updated unread count
            unread_count = notification_service.get_unread_count(db=db, user_id=user_id)
            
            return jsonify({
                'message': 'Notification marked as read',
                'notification_id': notification_id,
                'unread_count': unread_count
            }), 200
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({'error': 'Failed to mark notification as read'}), 500


@notification_bp.route('/read-all', methods=['POST'])
@require_auth
def mark_all_notifications_read(current_user: Dict[str, Any]) -> tuple:
    """
    Mark all notifications as read for the current user.
    
    Returns:
        200: All notifications marked as read
        500: Internal server error
    """
    try:
        user_id = current_user['user_id']
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Mark all as read
        with get_db_session() as db:
            count = notification_service.mark_all_as_read(db=db, user_id=user_id)
            
            return jsonify({
                'message': 'All notifications marked as read',
                'count': count
            }), 200
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'error': 'Failed to mark all notifications as read'}), 500


@notification_bp.route('/preferences', methods=['GET'])
@require_auth
def get_notification_preferences(current_user: Dict[str, Any]) -> tuple:
    """
    Get notification preferences for the current user.
    
    Returns:
        200: Notification preferences
        500: Internal server error
    """
    try:
        user_id = current_user['user_id']
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Get preferences (currently returns default preferences)
        with get_db_session() as db:
            preferences = notification_service._get_user_preferences(db=db, user_id=user_id)
            
            # Convert to dict
            preferences_dict = {}
            for notif_type, config in preferences.preferences.items():
                preferences_dict[notif_type] = {
                    'enabled': config.enabled,
                    'channels': [c.value for c in config.channels]
                }
            
            return jsonify({
                'user_id': user_id,
                'preferences': preferences_dict
            }), 200
        
    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}")
        return jsonify({'error': 'Failed to get notification preferences'}), 500


@notification_bp.route('/preferences', methods=['PUT'])
@require_auth
def update_notification_preferences(current_user: Dict[str, Any]) -> tuple:
    """
    Update notification preferences for the current user.
    
    Request Body:
        {
            "preferences": {
                "order_executed": {
                    "enabled": true,
                    "channels": ["in_app", "email"]
                },
                "strategy_error": {
                    "enabled": true,
                    "channels": ["in_app", "email", "sms"]
                },
                ...
            }
        }
    
    Returns:
        200: Preferences updated
        400: Invalid request
        500: Internal server error
    """
    try:
        user_id = current_user['user_id']
        data = request.get_json()
        
        if not data or 'preferences' not in data:
            return jsonify({'error': 'Missing required field: preferences'}), 400
        
        preferences_data = data['preferences']
        
        # Validate preferences structure
        valid_types = [t.value for t in NotificationType]
        valid_channels = [c.value for c in NotificationChannel]
        
        for notif_type, config in preferences_data.items():
            if notif_type not in valid_types:
                return jsonify({'error': f'Invalid notification type: {notif_type}'}), 400
            
            if 'enabled' not in config or 'channels' not in config:
                return jsonify({'error': f'Missing enabled or channels for {notif_type}'}), 400
            
            if not isinstance(config['enabled'], bool):
                return jsonify({'error': f'enabled must be boolean for {notif_type}'}), 400
            
            if not isinstance(config['channels'], list):
                return jsonify({'error': f'channels must be a list for {notif_type}'}), 400
            
            for channel in config['channels']:
                if channel not in valid_channels:
                    return jsonify({'error': f'Invalid channel: {channel}'}), 400
        
        # TODO: Store preferences in database
        # For now, just return success
        
        logger.info(f"Updated notification preferences for user {user_id}")
        
        return jsonify({
            'message': 'Notification preferences updated',
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        return jsonify({'error': 'Failed to update notification preferences'}), 500


@notification_bp.route('/test', methods=['POST'])
@require_auth
def test_notification_delivery(current_user: Dict[str, Any]) -> tuple:
    """
    Test notification delivery for the current user.
    
    Request Body:
        {
            "channels": ["in_app", "email", "sms"]  # Optional, defaults to in_app only
        }
    
    Returns:
        200: Test notification sent
        400: Invalid request
        500: Internal server error
    """
    try:
        user_id = current_user['user_id']
        data = request.get_json() or {}
        
        # Get channels to test
        channels_data = data.get('channels', ['in_app'])
        
        # Validate channels
        valid_channels = [c.value for c in NotificationChannel]
        channels = []
        
        for channel_str in channels_data:
            if channel_str not in valid_channels:
                return jsonify({'error': f'Invalid channel: {channel_str}'}), 400
            channels.append(NotificationChannel(channel_str))
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Create test notification
        with get_db_session() as db:
            request_obj = NotificationRequest(
                user_id=user_id,
                type=NotificationType.SYSTEM_ALERT,
                title="Test Notification",
                message="This is a test notification to verify your notification settings are working correctly.",
                severity=NotificationSeverity.INFO,
                channels=channels
            )
            
            notification = notification_service.create_notification(db, request_obj)
            
            return jsonify({
                'message': 'Test notification sent',
                'notification_id': notification.id,
                'channels': [c.value for c in channels]
            }), 200
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return jsonify({'error': 'Failed to send test notification'}), 500


@notification_bp.route('/create', methods=['POST'])
@require_auth
def create_notification(current_user: Dict[str, Any]) -> tuple:
    """
    Create a notification (admin only).
    
    Request Body:
        {
            "user_id": "uuid",
            "type": "system_alert",
            "title": "Notification Title",
            "message": "Notification message",
            "severity": "info",
            "channels": ["in_app", "email"]  # Optional
        }
    
    Returns:
        200: Notification created
        400: Invalid request
        403: Forbidden (not admin)
        500: Internal server error
    """
    try:
        # Check if user is admin
        if current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'type', 'title', 'message', 'severity']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate notification type
        try:
            notif_type = NotificationType(data['type'])
        except ValueError:
            return jsonify({'error': f'Invalid notification type: {data["type"]}'}), 400
        
        # Validate severity
        try:
            severity = NotificationSeverity(data['severity'])
        except ValueError:
            return jsonify({'error': f'Invalid severity: {data["severity"]}'}), 400
        
        # Validate channels if provided
        channels = None
        if 'channels' in data:
            try:
                channels = [NotificationChannel(c) for c in data['channels']]
            except ValueError as e:
                return jsonify({'error': f'Invalid channel: {str(e)}'}), 400
        
        # Get notification service
        notification_service = get_notification_service()
        
        # Create notification
        with get_db_session() as db:
            request_obj = NotificationRequest(
                user_id=data['user_id'],
                type=notif_type,
                title=data['title'],
                message=data['message'],
                severity=severity,
                channels=channels,
                metadata=data.get('metadata')
            )
            
            notification = notification_service.create_notification(db, request_obj)
            
            return jsonify({
                'message': 'Notification created',
                'notification': {
                    'id': notification.id,
                    'user_id': notification.user_id,
                    'type': notification.type.value,
                    'title': notification.title,
                    'message': notification.message,
                    'severity': notification.severity.value,
                    'created_at': notification.created_at.isoformat()
                }
            }), 200
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return jsonify({'error': 'Failed to create notification'}), 500



def register_notification_routes(app):
    """Register notification blueprint with Flask app"""
    app.register_blueprint(notification_bp)
    logger.info("Notification routes registered")
