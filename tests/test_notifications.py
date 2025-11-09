"""
Unit tests for notification service.
Tests notification delivery through different channels, trigger logic, and preferences.
"""
import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models import User, UserRole, Notification
from shared.models.notification import (
    NotificationData, NotificationRequest, NotificationType,
    NotificationSeverity, NotificationChannel, NotificationChannelConfig,
    NotificationPreferences
)
from shared.services.notification_service import NotificationService
from shared.services.notification_triggers import NotificationTriggers
from shared.utils.password import hash_password


@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    # Return a mock session since we're testing service logic, not database operations
    mock_session = Mock()
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.refresh = Mock()
    mock_session.query = Mock()
    return mock_session


@pytest.fixture
def test_user():
    """Create a test user."""
    user = Mock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.password_hash = hash_password("TestPass123!")
    user.role = UserRole.TRADER
    return user


@pytest.fixture
def notification_service():
    """Create a notification service instance."""
    return NotificationService()


@pytest.fixture
def notification_triggers():
    """Create a notification triggers instance."""
    return NotificationTriggers()


class TestNotificationService:
    """Test notification service core functionality."""
    
    def test_create_notification(self, db_session, test_user, notification_service):
        """Test creating a notification."""
        request = NotificationRequest(
            user_id=str(test_user.id),
            type=NotificationType.ORDER_EXECUTED,
            title="Order Executed",
            message="Your order was executed successfully",
            severity=NotificationSeverity.INFO,
            channels=[NotificationChannel.IN_APP]
        )
        
        # Mock the notification object that would be returned from database
        mock_notification = Mock()
        mock_notification.id = uuid.uuid4()
        mock_notification.user_id = uuid.UUID(request.user_id)
        mock_notification.type = request.type
        mock_notification.title = request.title
        mock_notification.message = request.message
        mock_notification.severity = request.severity
        mock_notification.created_at = datetime.utcnow()
        mock_notification.read_at = None
        
        db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', mock_notification.id)
        
        with patch('websocket_service.notification_events.push_notification'):
            notification = notification_service.create_notification(db_session, request)
        
        assert notification is not None
        assert notification.user_id == str(test_user.id)
        assert notification.type == NotificationType.ORDER_EXECUTED
        assert notification.title == "Order Executed"
        assert notification.severity == NotificationSeverity.INFO
    
    def test_get_notification_history(self, db_session, test_user, notification_service):
        """Test retrieving notification history."""
        # Create multiple notifications
        for i in range(5):
            request = NotificationRequest(
                user_id=str(test_user.id),
                type=NotificationType.SYSTEM_ALERT,
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                severity=NotificationSeverity.INFO,
                channels=[NotificationChannel.IN_APP]
            )
            
            with patch('shared.services.notification_service.push_notification'):
                notification_service.create_notification(db_session, request)
        
        # Get history
        history = notification_service.get_notification_history(
            db=db_session,
            user_id=str(test_user.id),
            limit=10
        )
        
        assert len(history) == 5
        assert all(n.user_id == str(test_user.id) for n in history)
    
    def test_get_unread_count(self, db_session, test_user, notification_service):
        """Test getting unread notification count."""
        # Create notifications
        for i in range(3):
            request = NotificationRequest(
                user_id=str(test_user.id),
                type=NotificationType.SYSTEM_ALERT,
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                severity=NotificationSeverity.INFO,
                channels=[NotificationChannel.IN_APP]
            )
            
            with patch('shared.services.notification_service.push_notification'):
                notification_service.create_notification(db_session, request)
        
        # Get unread count
        unread_count = notification_service.get_unread_count(
            db=db_session,
            user_id=str(test_user.id)
        )
        
        assert unread_count == 3
    
    def test_mark_as_read(self, db_session, test_user, notification_service):
        """Test marking a notification as read."""
        # Create notification
        request = NotificationRequest(
            user_id=str(test_user.id),
            type=NotificationType.SYSTEM_ALERT,
            title="Test Notification",
            message="Test message",
            severity=NotificationSeverity.INFO,
            channels=[NotificationChannel.IN_APP]
        )
        
        with patch('shared.services.notification_service.push_notification'):
            notification = notification_service.create_notification(db_session, request)
        
        # Mark as read
        success = notification_service.mark_as_read(
            db=db_session,
            user_id=str(test_user.id),
            notification_id=notification.id
        )
        
        assert success is True
        
        # Verify unread count decreased
        unread_count = notification_service.get_unread_count(
            db=db_session,
            user_id=str(test_user.id)
        )
        
        assert unread_count == 0
    
    def test_mark_all_as_read(self, db_session, test_user, notification_service):
        """Test marking all notifications as read."""
        # Create multiple notifications
        for i in range(5):
            request = NotificationRequest(
                user_id=str(test_user.id),
                type=NotificationType.SYSTEM_ALERT,
                title=f"Test Notification {i}",
                message=f"Test message {i}",
                severity=NotificationSeverity.INFO,
                channels=[NotificationChannel.IN_APP]
            )
            
            with patch('shared.services.notification_service.push_notification'):
                notification_service.create_notification(db_session, request)
        
        # Mark all as read
        count = notification_service.mark_all_as_read(
            db=db_session,
            user_id=str(test_user.id)
        )
        
        assert count == 5
        
        # Verify unread count is 0
        unread_count = notification_service.get_unread_count(
            db=db_session,
            user_id=str(test_user.id)
        )
        
        assert unread_count == 0


class TestNotificationDelivery:
    """Test notification delivery through different channels."""
    
    @patch('shared.services.notification_service.push_notification')
    def test_in_app_delivery(self, mock_push, db_session, test_user, notification_service):
        """Test in-app notification delivery via WebSocket."""
        request = NotificationRequest(
            user_id=str(test_user.id),
            type=NotificationType.ORDER_EXECUTED,
            title="Order Executed",
            message="Your order was executed",
            severity=NotificationSeverity.INFO,
            channels=[NotificationChannel.IN_APP]
        )
        
        notification = notification_service.create_notification(db_session, request)
        
        # Verify WebSocket push was called
        mock_push.assert_called_once()
        assert notification is not None
    
    @patch('smtplib.SMTP')
    def test_email_delivery(self, mock_smtp, db_session, test_user, notification_service):
        """Test email notification delivery."""
        # Configure SMTP settings
        notification_service._smtp_user = "test@example.com"
        notification_service._smtp_password = "password"
        
        request = NotificationRequest(
            user_id=str(test_user.id),
            type=NotificationType.STRATEGY_ERROR,
            title="Strategy Error",
            message="Your strategy encountered an error",
            severity=NotificationSeverity.ERROR,
            channels=[NotificationChannel.EMAIL]
        )
        
        with patch('shared.services.notification_service.push_notification'):
            notification = notification_service.create_notification(db_session, request)
        
        assert notification is not None
    
    def test_notification_batching(self, db_session, test_user, notification_service):
        """Test notification batching to prevent spam."""
        # Create multiple low-priority notifications
        for i in range(5):
            request = NotificationRequest(
                user_id=str(test_user.id),
                type=NotificationType.SYSTEM_ALERT,
                title=f"Info {i}",
                message=f"Info message {i}",
                severity=NotificationSeverity.INFO,
                channels=[NotificationChannel.EMAIL]
            )
            
            with patch('shared.services.notification_service.push_notification'):
                notification_service.create_notification(db_session, request)
        
        # Verify notifications were added to batch
        assert len(notification_service._notification_batch) > 0
    
    def test_immediate_delivery_for_critical(self, db_session, test_user, notification_service):
        """Test that critical notifications are delivered immediately without batching."""
        request = NotificationRequest(
            user_id=str(test_user.id),
            type=NotificationType.LOSS_LIMIT_BREACHED,
            title="Loss Limit Breached",
            message="Your loss limit has been breached",
            severity=NotificationSeverity.CRITICAL,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
        )
        
        with patch('shared.services.notification_service.push_notification'):
            with patch.object(notification_service, '_deliver_email') as mock_email:
                notification = notification_service.create_notification(db_session, request)
                
                # Verify email was sent immediately (not batched)
                mock_email.assert_called_once()


class TestNotificationTriggers:
    """Test notification trigger logic for various events."""
    
    def test_trigger_order_executed(self, db_session, test_user, notification_triggers):
        """Test order executed notification trigger."""
        with patch('shared.services.notification_service.push_notification'):
            notification_triggers.trigger_order_executed(
                db=db_session,
                user_id=str(test_user.id),
                order_id=str(uuid.uuid4()),
                symbol="RELIANCE",
                side="buy",
                quantity=10,
                price=2500.50,
                trading_mode="paper"
            )
        
        # Verify notification was created
        notifications = db_session.query(Notification).filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.ORDER_EXECUTED
        ).all()
        
        assert len(notifications) == 1
        assert "RELIANCE" in notifications[0].message
        assert "Paper" in notifications[0].title
    
    def test_trigger_strategy_error(self, db_session, test_user, notification_triggers):
        """Test strategy error notification trigger."""
        with patch('shared.services.notification_service.push_notification'):
            notification_triggers.trigger_strategy_error(
                db=db_session,
                user_id=str(test_user.id),
                strategy_id=str(uuid.uuid4()),
                strategy_name="MA Crossover",
                error_message="Division by zero",
                error_details="Error in indicator calculation"
            )
        
        # Verify notification was created
        notifications = db_session.query(Notification).filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.STRATEGY_ERROR
        ).all()
        
        assert len(notifications) == 1
        assert notifications[0].severity == NotificationSeverity.ERROR
        assert "MA Crossover" in notifications[0].message
    
    def test_trigger_threshold_alert(self, db_session, test_user, notification_triggers):
        """Test threshold alert notification trigger."""
        with patch('shared.services.notification_service.push_notification'):
            notification_triggers.trigger_threshold_alert(
                db=db_session,
                user_id=str(test_user.id),
                alert_type="loss",
                symbol="TCS",
                current_value=-5000.0,
                threshold_value=-5000.0,
                trading_mode="live"
            )
        
        # Verify notification was created
        notifications = db_session.query(Notification).filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.THRESHOLD_ALERT
        ).all()
        
        assert len(notifications) == 1
        assert "Loss Threshold" in notifications[0].title
        assert "TCS" in notifications[0].message
    
    def test_trigger_connection_lost(self, db_session, test_user, notification_triggers):
        """Test connection lost notification trigger."""
        with patch('shared.services.notification_service.push_notification'):
            notification_triggers.trigger_connection_lost(
                db=db_session,
                user_id=str(test_user.id),
                connection_type="broker",
                connection_name="Angel One",
                error_message="Connection timeout"
            )
        
        # Verify notification was created
        notifications = db_session.query(Notification).filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.CONNECTION_LOST
        ).all()
        
        assert len(notifications) == 1
        assert "Angel One" in notifications[0].message
    
    def test_trigger_trailing_stop_triggered(self, db_session, test_user, notification_triggers):
        """Test trailing stop triggered notification."""
        with patch('shared.services.notification_service.push_notification'):
            notification_triggers.trigger_trailing_stop_triggered(
                db=db_session,
                user_id=str(test_user.id),
                position_id=str(uuid.uuid4()),
                symbol="INFY",
                side="long",
                stop_price=1450.0,
                current_price=1445.0,
                trading_mode="live"
            )
        
        # Verify notification was created
        notifications = db_session.query(Notification).filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.TRAILING_STOP_TRIGGERED
        ).all()
        
        assert len(notifications) == 1
        assert "INFY" in notifications[0].message
        assert notifications[0].severity == NotificationSeverity.WARNING
    
    def test_trigger_loss_limit_breached(self, db_session, test_user, notification_triggers):
        """Test loss limit breached notification trigger."""
        with patch('shared.services.notification_service.push_notification'):
            notification_triggers.trigger_loss_limit_breached(
                db=db_session,
                user_id=str(test_user.id),
                account_id=str(uuid.uuid4()),
                trading_mode="live",
                current_loss=-10500.0,
                loss_limit=-10000.0
            )
        
        # Verify notification was created
        notifications = db_session.query(Notification).filter(
            Notification.user_id == test_user.id,
            Notification.type == NotificationType.LOSS_LIMIT_BREACHED
        ).all()
        
        assert len(notifications) == 1
        assert notifications[0].severity == NotificationSeverity.CRITICAL
        assert "10500" in notifications[0].message


class TestNotificationPreferences:
    """Test notification preferences functionality."""
    
    def test_get_user_preferences(self, db_session, test_user, notification_service):
        """Test getting user notification preferences."""
        preferences = notification_service._get_user_preferences(
            db=db_session,
            user_id=str(test_user.id)
        )
        
        assert preferences is not None
        assert preferences.user_id == str(test_user.id)
        assert len(preferences.preferences) > 0
    
    def test_get_channels_for_type(self, db_session, test_user, notification_service):
        """Test getting enabled channels for a notification type."""
        preferences = notification_service._get_user_preferences(
            db=db_session,
            user_id=str(test_user.id)
        )
        
        # Get channels for strategy error (should include SMS)
        channels = preferences.get_channels_for_type(NotificationType.STRATEGY_ERROR)
        
        assert NotificationChannel.IN_APP in channels
        assert NotificationChannel.EMAIL in channels
        assert NotificationChannel.SMS in channels
    
    def test_disabled_notification_type(self):
        """Test that disabled notification types return no channels."""
        preferences = NotificationPreferences(
            user_id=str(uuid.uuid4()),
            preferences={
                NotificationType.SYSTEM_ALERT.value: NotificationChannelConfig(
                    enabled=False,
                    channels=[NotificationChannel.IN_APP]
                )
            }
        )
        
        channels = preferences.get_channels_for_type(NotificationType.SYSTEM_ALERT)
        
        assert len(channels) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
